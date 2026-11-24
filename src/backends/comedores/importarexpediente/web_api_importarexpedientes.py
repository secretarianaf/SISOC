"""Web API (G1 v1) of the payment-file imports (EX02.02 and EX02.01).

``/api/web/comedores/`` is published by the Comedores backend (``url_prefixes``
in ``src/backends/config/backends.json``). In a split deploy the core checks the
session and the web prerequisites and signs each request; the runtime only
serves requests its ``WebGateMiddleware`` verified. In the monolith
``WebGatePermission`` evaluates the same policy locally. After that the native
rules apply unchanged (kept on purpose, see
``docs/registro/decisiones/2026-11-10-2785-brechas-acceso-conservadas.md``):

- list and detail: the ``importarexpediente.view_archivosimportados`` code, no
  scope (every user with it sees every batch);
- upload, import and delete of the imported data: a session only;
- accreditation dates: ``permissions_any_required`` with the two change codes.

Every endpoint runs the native view of ``importarexpediente.views`` itself: the
queryset and the combinable filters, the paginator and its 404, the completion
of the missing periods (a write on GET, kept), the form validation, the import
and its states, the physical delete and the accreditation update. Nothing is
reimplemented here: the native messages are read back from the request, in the
same order, so the screens show the same texts and levels. A native 302 to the
batch list keeps its messages queued in the session (the next GET of the list
consumes them, like the native page); a native redirect that stays on the form
(upload) or re-renders it (accreditation) returns its messages in the body.

Nothing runs as a job: the import, the states update and the delete are the
native synchronous code. A repeated import is answered 409 and has no effect
(native ``select_for_update`` plus ``importacion_completada``).
"""

from html import unescape

from django.contrib import messages
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.template import Context, Template
from django.urls import reverse
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound
from rest_framework.permissions import BasePermission
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

# The exact predicates of the native route decorators.
from core.decorators import _has_all_permissions, _has_any_permissions
from core.pagination import build_compact_page_range
from core.templatetags.custom_filters import has_any_perm
from core.web_gate import WebGatePermission
from importarexpediente.forms import AcreditacionUploadForm, CSVUploadForm
from importarexpediente.models import ArchivosImportados
from importarexpediente.views import (
    BorrarDatosImportadosView,
    ImportarExpedienteDetalleListView,
    ImportarExpedienteListView,
    ImportarFechasAcreditacionView,
    ImportDatosView,
    ImportExpedientesView,
)

VIEW_CODE = "importarexpediente.view_archivosimportados"
# ``importarexpediente/urls.py`` and ``importarexpediente_detail.html``.
ACREDITACION_CODES = [
    "importarexpediente.change_archivosimportados",
    "expedientespagos.change_expedientepago",
]
MESSAGE_LEVELS = {
    messages.DEBUG: "info",
    messages.INFO: "info",
    messages.SUCCESS: "success",
    messages.WARNING: "warning",
    messages.ERROR: "error",
}
UPLOAD_TYPES = ("multipart/form-data",)
# Native message texts the status code of the transport is derived from.
DUPLICADO = (
    "No se puede adjuntar el archivo ya que el expediente de pago se encuentra "
    "cargado anteriormente"
)
YA_IMPORTADO = "Este archivo ya fue importado."
NO_LEGIBLE = "No se pudo leer el archivo"
IMPORTACION_FALLIDA = "No se pudo completar la importación"

# ``importarexpediente_list_rows.html``, cell by cell.
_ROW = {
    key: Template("{% load custom_filters %}" + source)
    for key, source in {
        "numero_expediente_pago": '{{ e.numero_expediente_pago|default_if_none:"Sin informacion" }}',
        "archivo": "{{ e.archivo }}",
        "periodo_pago": '{{ e.periodo_pago|default_if_none:"Sin informacion" }}',
        "periodo_orden": "{{ e.periodo_pago|default:'' }}",
        "usuario": '{{ e.usuario.username|default_if_none:"Sin informacion" }}',
        "fecha_subida": '{{ e.fecha_subida|default_if_none:"Sin informacion" }}',
        "count_exitos": '{{ e.count_exitos|default_if_none:"Sin informacion" }}',
        "count_errores": '{{ e.count_errores|default_if_none:"Sin informacion" }}',
        "importacion_completada": '{{ e.importacion_completada|yesno:"Si,No,Sin informacion" }}',
    }.items()
}
# ``importarexpediente_detail_rows.html``.
_ERROR_ROW = {
    key: Template(source)
    for key, source in {
        "fila": '{{ e.fila|default_if_none:"Sin información" }}',
        "mensaje": '{{ e.mensaje|default_if_none:"Sin información" }}',
        "archivo": "{{ e.archivo_importado }}",
    }.items()
}
_QUOTE = Template("{{ v|urlencode }}")


def _render(template, objeto):
    return unescape(template.render(Context({"e": objeto})).strip())


def _plain(valor):
    return _QUOTE.render(Context({"v": valor})).strip()


def pending_messages(request):
    """Consume the queued Django messages exactly as the native page would."""
    return [
        {"message": str(m), "level": MESSAGE_LEVELS.get(m.level, "info")}
        for m in messages.get_messages(request)
    ]


def _peek_and_requeue(request):
    """Read the native messages for the transport status and queue them again.

    The destination page (the batch list) consumes them, like after the native
    302.
    """
    leidos = list(messages.get_messages(request))
    for mensaje in leidos:
        messages.add_message(
            request, mensaje.level, mensaje.message, extra_tags=mensaje.extra_tags
        )
    return [str(m) for m in leidos]


class VerLotes(BasePermission):
    """``permission_code_required`` of list and detail (``permissions_all_required``)."""

    def has_permission(self, request, view):
        return _has_all_permissions(request.user, [VIEW_CODE])


class CambiarFechas(BasePermission):
    """``permissions_any_required`` of the accreditation dates."""

    def has_permission(self, request, view):
        return _has_any_permissions(request.user, ACREDITACION_CODES)


class _WebView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission]
    renderer_classes = [JSONRenderer]
    http_method_names = ["get", "head"]

    @staticmethod
    def native(view_class, request, **kwargs):
        vista = view_class()
        vista.setup(request._request, **kwargs)  # pylint: disable=protected-access
        return vista


def _query_prefix(request, excluidos):
    """Link prefix of ``components/pagination.html`` (page and the query dropped)."""
    return "".join(
        f"{clave}={_plain(valor)}&"
        for clave, valor in request.GET.items()
        if clave not in excluidos
    )


def _pagina(page, context, request, excluidos):
    return {
        "is_paginated": context["is_paginated"],
        "number": page.number,
        "num_pages": page.paginator.num_pages,
        "count": page.paginator.count,
        "previous": page.previous_page_number() if page.has_previous() else None,
        "next": page.next_page_number() if page.has_next() else None,
        "range": [
            "…" if numero in ("...", "…") else numero
            for numero in build_compact_page_range(page)
        ],
        "query_without_page": _query_prefix(request, excluidos),
    }


class LotesListWebView(_WebView):
    """``GET .../importarexpedientes/``: ``importarexpediente_list.html`` (EX02.02)."""

    permission_classes = [WebGatePermission, VerLotes]

    def get(self, request):
        vista = self.native(ImportarExpedienteListView, request)
        vista.object_list = vista.get_queryset()
        try:
            # Also completes (and saves) the missing periods of the visible page.
            context = vista.get_context_data()
        except Http404 as exc:
            raise NotFound() from exc
        page = context["page_obj"]
        return Response(
            {
                "filters_config": context["filters_config"],
                "favorites": {
                    "section": "",
                    "url": reverse("filtros_favoritos"),
                    "detail_url_template": reverse(
                        "detalle_filtro_favorito", kwargs={"pk": 0}
                    ),
                },
                "urls": {
                    "list": context["filters_action"],
                    "upload": reverse("upload"),
                },
                "results": [
                    {
                        "id": lote.pk,
                        **{
                            clave: _render(plantilla, lote)
                            for clave, plantilla in _ROW.items()
                        },
                        "detail_url": reverse(
                            "importarexpediente_detail", args=[lote.pk]
                        ),
                        "download_url": reverse(
                            "descargar_archivo_importado", args=[lote.pk]
                        ),
                    }
                    for lote in context["archivos_importados"]
                ],
                "page": _pagina(page, context, request, ("page", "busqueda")),
                "messages": pending_messages(request),
            }
        )


def _detalle_vista(request, pk):
    """The two lookups of ``ImportarExpedienteDetalleListView.dispatch``."""
    vista = _WebView.native(ImportarExpedienteDetalleListView, request, id_archivo=pk)
    vista.batch_id = pk
    try:
        vista.batch = get_object_or_404(ArchivosImportados, pk=pk)
    except Http404 as exc:
        raise NotFound() from exc
    return vista


class LoteDetailWebView(_WebView):
    """``GET .../importarexpedientes/<pk>/``: ``importarexpediente_detail.html``."""

    permission_classes = [WebGatePermission, VerLotes]

    def get(self, request, pk):
        vista = _detalle_vista(request, pk)
        vista.object_list = vista.get_queryset()
        try:
            context = vista.get_context_data()
        except Http404 as exc:
            raise NotFound() from exc
        batch = context["batch"]
        page = context["page_obj"]
        return Response(
            {
                "batch": {
                    "id": batch.pk,
                    "label": str(batch),
                    "importacion_completada": batch.importacion_completada,
                },
                "counts": {
                    "validos": context["exito_count"],
                    "errores": context["error_count"],
                    "con_acreditacion": context["expedientes_con_acreditacion_count"],
                },
                "can_update_acreditacion": bool(
                    batch.importacion_completada
                    and has_any_perm(request.user, ",".join(ACREDITACION_CODES))
                ),
                "urls": {
                    "list": context["volver_url"],
                    "ajax": reverse("importarexpediente_detail_ajax", args=[pk]),
                },
                "query": context["query"],
                "results": [
                    {
                        "id": error.pk,
                        "batch_id": error.archivo_importado_id,
                        **{
                            clave: _render(plantilla, error)
                            for clave, plantilla in _ERROR_ROW.items()
                        },
                        "detail_url": reverse(
                            "importarexpediente_detail",
                            args=[error.archivo_importado_id],
                        ),
                    }
                    for error in context["registros_del_archivo"]
                ],
                "page": _pagina(page, context, request, ("page", "busqueda")),
                "messages": pending_messages(request),
            }
        )


def _campo(form, nombre, tipo):
    campo = form.fields[nombre]
    bound = form[nombre]
    datos = {
        "name": nombre,
        "label": str(campo.label),
        "type": tipo,
        "required": campo.required,
        "help_text": str(campo.help_text or ""),
        "accept": campo.widget.attrs.get("accept", ""),
    }
    if tipo == "select":
        datos["choices"] = [
            {"value": valor, "label": str(etiqueta)}
            for valor, etiqueta in campo.choices
        ]
        datos["value"] = str(bound.value() if bound.value() is not None else "")
    elif tipo == "checkbox":
        datos["value"] = bool(bound.value())
    return datos


def formulario_subida():
    """The fields ``upload.html`` renders through ``form|crispy``."""
    form = CSVUploadForm()
    return [
        _campo(form, "file", "file"),
        _campo(form, "delimiter", "select"),
        _campo(form, "has_header", "checkbox"),
    ]


def formulario_fechas():
    """The field of ``importarexpediente_acreditacion_upload.html``."""
    return [_campo(AcreditacionUploadForm(), "file", "file")]


def _no_multipart(request):
    # ``Request.content_type`` keeps the multipart boundary; Django strips it.
    # pylint: disable-next=protected-access
    return request._request.content_type not in UPLOAD_TYPES


class SubirWebView(_WebView):
    """``/api/web/comedores/importarexpedientes/subir/``: ``ImportExpedientesView``.

    The native view only asks for a session. A native redirect back to the form
    (invalid form, unreadable file, repeated expediente number, save error) is
    answered 400, or 409 for the repeated number, with its messages in the body
    and without storing anything the native view does not store.
    """

    http_method_names = ["get", "post"]

    def get(self, request):
        return Response(
            {
                "fields": formulario_subida(),
                "list_url": reverse("importarexpedientes_list"),
                "messages": pending_messages(request),
            }
        )

    def post(self, request):
        if _no_multipart(request):
            return Response({"detail": "Formato de solicitud no admitido."}, status=415)
        vista = self.native(ImportExpedientesView, request)
        # pylint: disable-next=protected-access
        respuesta = vista.post(request._request)
        if respuesta["Location"] == str(vista.error_url):
            textos = pending_messages(request)
            estado = 409 if any(t["message"] == DUPLICADO for t in textos) else 400
            return Response({"ok": False, "messages": textos}, status=estado)
        return Response({"ok": True, "redirect": respuesta["Location"]})


class _AccionLoteWebView(_WebView):
    """Import and delete: the native ``post()`` of a batch, always back to the list."""

    http_method_names = ["post"]
    view_class = None

    def estado(self, textos):
        raise NotImplementedError

    def post(self, request, pk):
        vista = self.native(self.view_class, request, id_archivo=pk)
        vista.batch_id = pk
        try:
            # pylint: disable-next=protected-access
            respuesta = vista.post(request._request)
        except Http404 as exc:
            raise NotFound() from exc
        estado = self.estado(_peek_and_requeue(request))
        return Response(
            {"ok": estado == 200, "redirect": respuesta["Location"]}, status=estado
        )


class ImportarWebView(_AccionLoteWebView):
    """``POST .../importarexpedientes/<pk>/importar/``: ``ImportDatosView``."""

    view_class = ImportDatosView

    def estado(self, textos):
        if any(t.startswith(YA_IMPORTADO) for t in textos):
            return 409
        if any(t.startswith(IMPORTACION_FALLIDA) for t in textos):
            return 500
        if any(
            t.startswith(NO_LEGIBLE) or t.startswith(("El archivo est", "Archivo sin"))
            for t in textos
        ):
            return 400
        return 200


class BorrarDatosWebView(_AccionLoteWebView):
    """``POST .../importarexpedientes/<pk>/borrar-datos/``: ``BorrarDatosImportadosView``."""

    view_class = BorrarDatosImportadosView

    def estado(self, textos):
        return 200


class FechasAcreditacionWebView(_WebView):
    """``.../importarexpedientes/<pk>/fechas-acreditacion/``: ``ImportarFechasAcreditacionView``."""

    permission_classes = [WebGatePermission, CambiarFechas]
    http_method_names = ["get", "post"]

    def _vista(self, request, pk):
        vista = self.native(ImportarFechasAcreditacionView, request, id_archivo=pk)
        vista.batch_id = pk
        try:
            vista.batch = get_object_or_404(ArchivosImportados, pk=pk)
        except Http404 as exc:
            raise NotFound() from exc
        return vista

    def get(self, request, pk):
        vista = self._vista(request, pk)
        return Response(
            {
                "batch": {"id": vista.batch.pk, "label": str(vista.batch)},
                "fields": formulario_fechas(),
                "list_url": reverse("importarexpedientes_list"),
                "messages": pending_messages(request),
            }
        )

    def post(self, request, pk):
        if _no_multipart(request):
            return Response({"detail": "Formato de solicitud no admitido."}, status=415)
        vista = self._vista(request, pk)
        # pylint: disable-next=protected-access
        respuesta = vista.post(request._request)
        if respuesta.status_code == 302:
            return Response({"ok": True, "redirect": respuesta["Location"]})
        # The native view re-renders the form (200) with its messages.
        return Response(
            {"ok": False, "messages": pending_messages(request)}, status=400
        )
