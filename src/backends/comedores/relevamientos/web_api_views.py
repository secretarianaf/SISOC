"""Web API (G1 v1) of the relevamiento pages served by React (R01.01).

``/api/web/comedores/`` is published by the Comedores backend (``url_prefixes``
in ``src/backends/config/backends.json``). In a split deploy the core checks the
session and the web prerequisites and signs each request; the runtime only
serves requests its ``WebGateMiddleware`` verified. In the monolith
``WebGatePermission`` evaluates the same policy locally. After that the native
rule applies unchanged: superuser or ``relevamientos.view_relevamiento`` (the
predicate of ``permissions_any_required``), with no object scope and the detail
looked up by ``pk`` alone (kept on purpose, see
``docs/registro/decisiones/2026-11-10-2785-brechas-acceso-conservadas.md``).

Each endpoint runs the native view itself (queryset, context, 404s); this
module only projects that context to JSON. The native POSTs stay native.
"""

from django.http import Http404
from django.urls import reverse
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound
from rest_framework.permissions import BasePermission
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

# The exact predicate of ``permissions_any_required``, the native URL guard.
from core.decorators import _has_any_permissions
from core.web_gate import WebGatePermission
from relevamientos.views.backoffice_views import (
    ActaComplementariaDetailView,
    SeguimientoPnudDetailView,
)
from relevamientos.views.web_views import (
    PrimerSeguimientoDetailView,
    RelevamientoDetailView,
    RelevamientoListView,
)
from relevamientos.web_api_serializers import (
    acta_resumen,
    bloques_seguimiento,
    instancias_ciclo,
    mostrar,
    pdf_seguimiento,
    pnud_resumen,
    prestaciones_acta,
    prestaciones_seguimiento,
    receta_items,
    secciones_pnud,
    seguimiento_resumen,
    actas_listado,
    adjuntos_detalle,
    cabecera,
    comedor_encabezado,
    pdf_detalle,
    pending_messages,
    relevamientos_listado,
    secciones,
    seguimientos_detalle,
    seguimientos_pnud_listado,
    timeline,
)

VIEW_PERMISSIONS = ["relevamientos.view_relevamiento"]


class RelevamientoAccess(BasePermission):
    """Same rule as the native ``permissions_any_required(["relevamientos.view_relevamiento"])``."""

    def has_permission(self, request, view):
        return _has_any_permissions(request.user, VIEW_PERMISSIONS)


class _NativeReadView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, RelevamientoAccess]
    renderer_classes = [JSONRenderer]
    http_method_names = ["get", "head"]

    @staticmethod
    def native(view_class, request, **kwargs):
        vista = view_class()
        vista.setup(request._request, **kwargs)  # pylint: disable=protected-access
        return vista


def _perms(user, *codes):
    return {codigo: user.has_perm(f"relevamientos.{codigo}") for codigo in codes}


class RelevamientosListadoWebView(_NativeReadView):
    """``GET .../relevamientos/<comedor_pk>/``: ``relevamiento_list.html``."""

    def get(self, request, comedor_pk):
        vista = self.native(RelevamientoListView, request, comedor_pk=comedor_pk)
        vista.object_list = vista.get_queryset()
        try:
            context = vista.get_context_data()
        except Http404 as exc:
            raise NotFound() from exc
        comedor = context["comedor"]
        comedor_id = comedor["id"]
        return Response(
            {
                "comedor": {"id": comedor_id, "nombre": comedor["nombre"]},
                "encabezado": comedor_encabezado(comedor),
                "relevamientos": relevamientos_listado(
                    context["relevamientos_items"], comedor_id
                ),
                "actas": actas_listado(context["actas_complementarias"], comedor_id),
                "seguimientos_pnud": seguimientos_pnud_listado(
                    context["seguimientos_pnud"], comedor_id
                ),
                "opciones_alta": [
                    {"value": valor, "label": str(etiqueta)}
                    for valor, etiqueta in context["opciones_alta"]
                ],
                "opciones_seguimiento": [
                    {"value": valor, "label": str(etiqueta)}
                    for valor, etiqueta in context["opciones_seguimiento"]
                ],
                "capabilities": _perms(
                    request.user,
                    "add_relevamiento",
                    "change_relevamiento",
                    "add_actacomplementaria",
                    "change_actacomplementaria",
                ),
                "urls": {
                    "listado": reverse("relevamientos", args=[comedor_id]),
                    "alta": reverse("relevamiento_create_edit_ajax", args=[comedor_id]),
                    "acta_crear": reverse(
                        "acta_complementaria_crear", args=[comedor_id]
                    ),
                    "territoriales": reverse(
                        "api_obtener_territoriales", args=[comedor_id]
                    ),
                    "territoriales_sincronizar": reverse(
                        "api_sincronizar_territoriales", args=[comedor_id]
                    ),
                },
                "messages": pending_messages(request),
            }
        )


class RelevamientoDetalleWebView(_NativeReadView):
    """``GET .../relevamientos/<comedor_pk>/relevamiento/<pk>/``: ``relevamiento_detail.html``.

    ``comedor_pk`` is ignored, as in the native view (it looks up ``pk`` only).
    """

    def get(self, request, comedor_pk, pk):
        vista = self.native(
            RelevamientoDetailView, request, comedor_pk=comedor_pk, pk=pk
        )
        try:
            vista.object = vista.get_object()
        except Http404 as exc:
            raise NotFound() from exc
        context = vista.get_context_data(object=vista.object)
        relevamiento = vista.object
        comedor_id = relevamiento.comedor.id
        arbol, titulos = secciones(context)
        return Response(
            {
                "relevamiento": cabecera(relevamiento, context["estado_visible"]),
                "timeline": timeline(context["relevamientos_timeline"]),
                "secciones": arbol,
                "titulos": titulos,
                "seguimientos": seguimientos_detalle(
                    context["seguimientos"], comedor_id, relevamiento.id
                ),
                "adjuntos": adjuntos_detalle(context["adjuntos"]),
                "pdf": pdf_detalle(relevamiento, context["pdf_oficial"]),
                "capabilities": {
                    **_perms(
                        request.user,
                        "change_relevamiento",
                        "review_relevamiento",
                        "change_primerseguimiento",
                        "delete_primerseguimiento",
                    ),
                    "view_logentry": request.user.has_perm("auditlog.view_logentry"),
                },
                "urls": {
                    "listado": reverse("relevamientos", args=[comedor_id]),
                    "comedores": reverse("comedores"),
                    "comedor": reverse("comedor_detalle", args=[comedor_id]),
                    "alta": reverse("relevamiento_create_edit_ajax", args=[comedor_id]),
                    "eliminar": reverse(
                        "relevamiento_eliminar", args=[comedor_id, relevamiento.id]
                    ),
                    "revision": reverse(
                        "relevamiento_revision_coordinador",
                        args=[comedor_id, relevamiento.id],
                    ),
                    "historial": reverse(
                        "audittrail:log_instance",
                        args=["relevamientos", "relevamiento", relevamiento.pk],
                    ),
                    "territoriales": reverse(
                        "api_obtener_territoriales", args=[comedor_id]
                    ),
                    "territoriales_sincronizar": reverse(
                        "api_sincronizar_territoriales", args=[comedor_id]
                    ),
                },
                "messages": pending_messages(request),
            }
        )


class SeguimientoDetalleWebView(_NativeReadView):
    """``GET .../relevamiento/<relevamiento_pk>/seguimientos/<pk>/`` (or ``primero/``): ``primer_seguimiento_detail.html``."""

    def get(self, request, comedor_pk, relevamiento_pk, pk=None):
        kwargs = {"comedor_pk": comedor_pk, "relevamiento_pk": relevamiento_pk}
        if pk is not None:
            kwargs["pk"] = pk
        vista = self.native(PrimerSeguimientoDetailView, request, **kwargs)
        try:
            vista.object = vista.get_object()
        except Http404 as exc:
            raise NotFound(str(exc) if exc.args else None) from exc
        context = vista.get_context_data(object=vista.object)
        seguimiento = vista.object
        relevamiento = context["relevamiento"]
        comedor = context["comedor"]
        args = [comedor.id, relevamiento.id, seguimiento.id]
        return Response(
            {
                "seguimiento": seguimiento_resumen(seguimiento),
                "relevamiento": {
                    "id": relevamiento.id,
                    "fecha_visita": mostrar(
                        relevamiento.fecha_visita, "Sin información"
                    ),
                },
                "comedor": {"id": comedor.id, "nombre": comedor.nombre},
                "instancias": instancias_ciclo(
                    context["instancias"], comedor.id, relevamiento.id
                ),
                "bloques": bloques_seguimiento(context["bloques"]),
                "es_primer": context["es_primer"],
                "prestaciones": prestaciones_seguimiento(
                    context["prestaciones"], context["es_primer"]
                ),
                "receta_items": receta_items(context["receta_items"]),
                "adjuntos": adjuntos_detalle(context["adjuntos"]),
                "pdf": pdf_seguimiento(
                    seguimiento, context["pdf_oficial"], comedor.id, relevamiento.id
                ),
                "capabilities": _perms(
                    request.user,
                    "change_primerseguimiento",
                    "review_relevamiento",
                    "delete_primerseguimiento",
                ),
                "urls": {
                    "comedores": reverse("comedores"),
                    "comedor": reverse("comedor_detalle", args=[comedor.id]),
                    "relevamiento": reverse(
                        "relevamiento_detalle", args=[comedor.id, relevamiento.id]
                    ),
                    "editar": reverse("seguimiento_editar", args=args),
                    "revision": reverse("seguimiento_revision_coordinador", args=args),
                },
                "messages": pending_messages(request),
            }
        )


class SeguimientoPnudDetalleWebView(_NativeReadView):
    """``GET .../pnud/<pk>/``: ``seguimiento_pnud_detail.html``."""

    def get(self, request, comedor_pk, pk):
        vista = self.native(
            SeguimientoPnudDetailView, request, comedor_pk=comedor_pk, pk=pk
        )
        try:
            vista.object = vista.get_object()
        except Http404 as exc:
            raise NotFound() from exc
        context = vista.get_context_data(object=vista.object)
        seguimiento = vista.object
        comedor = context["comedor"]
        encabezado = context["encabezado_formulario"] or {}
        return Response(
            {
                "seguimiento": pnud_resumen(seguimiento),
                "comedor": {"id": comedor.id, "nombre": comedor.nombre},
                "encabezado_formulario": {
                    "linea": encabezado.get("linea") or "",
                    "titulo": encabezado.get("titulo") or "",
                },
                "secciones": secciones_pnud(context["secciones"]),
                "adjuntos": adjuntos_detalle(context["adjuntos"]),
                "pdf_url": (
                    reverse(
                        "seguimiento_pnud_pdf",
                        kwargs={"comedor_pk": comedor.pk, "pk": seguimiento.pk},
                    )
                    if seguimiento.formulario == "siph"
                    else None
                ),
                "capabilities": _perms(request.user, "review_relevamiento"),
                "urls": {
                    "comedores": reverse("comedores"),
                    "comedor": reverse("comedor_detalle", args=[comedor.id]),
                    "listado": reverse("relevamientos", args=[comedor.id]),
                    "revision": reverse(
                        "seguimiento_pnud_revision_coordinador",
                        args=[comedor.id, seguimiento.id],
                    ),
                },
                "messages": pending_messages(request),
            }
        )


class ActaDetalleWebView(_NativeReadView):
    """``GET .../actas/<pk>/``: ``acta_complementaria_detail.html``."""

    def get(self, request, comedor_pk, pk):
        vista = self.native(
            ActaComplementariaDetailView, request, comedor_pk=comedor_pk, pk=pk
        )
        try:
            vista.object = vista.get_object()
        except Http404 as exc:
            raise NotFound() from exc
        context = vista.get_context_data(object=vista.object)
        acta = vista.object
        comedor = context["comedor"]
        args = [comedor.id, acta.id]
        return Response(
            {
                "acta": acta_resumen(acta),
                "prestaciones": prestaciones_acta(context["prestaciones"]),
                "adjuntos": adjuntos_detalle(context["adjuntos"]),
                "capabilities": _perms(
                    request.user,
                    "change_actacomplementaria",
                    "review_relevamiento",
                    "delete_actacomplementaria",
                ),
                "urls": {
                    "comedores": reverse("comedores"),
                    "comedor": reverse("comedor_detalle", args=[comedor.id]),
                    "listado": reverse("relevamientos", args=[comedor.id]),
                    "editar": reverse("acta_complementaria_editar", args=args),
                    "revision": reverse(
                        "acta_complementaria_revision_coordinador", args=args
                    ),
                    "eliminar": reverse("acta_complementaria_eliminar", args=args),
                },
                "messages": pending_messages(request),
            }
        )
