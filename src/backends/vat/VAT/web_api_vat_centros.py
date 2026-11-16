"""Web API (G1 v1) de la lista y la baja de centros de VAT (V06.01, V06.02).

``/api/web/vat/centros-lista/`` corre la vista nativa ``CentroListView`` (alcance por usuario, búsqueda, filtros avanzados y
páginas sin conteo) y proyecta su contexto; ``/api/web/vat/centros-lista/<pk>/eliminar/`` corre ``CentroDeleteView`` con su
``dispatch`` (el mismo 403 y 404 que la ruta nativa) y devuelve la vista previa de la baja lógica en cascada (GET) o da de
baja el centro con el mensaje nativo (POST). Acceso: ``VAT.view_centro``, como cada ruta.
``vat_centros_ajax`` y los endpoints ``vat_ajax_*`` siguen siendo los nativos: ninguna pantalla React los llama.
"""

from urllib.parse import quote

from django.http import Http404
from django.urls import reverse
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from core.pagination import build_compact_page_range
from VAT.views.centro import CentroDeleteView, CentroListView
from VAT.web_api_common import VatNativeReadView, mensajes_pendientes, texto
from VAT.web_api_vat_centros_base import redireccion

_VER = ["VAT.view_centro"]
_LISTA = "vat_centro_list"
_TEXTO = "{{ v }}"


def _prefijo_paginacion(request):
    """Prefix of every ``components/pagination.html`` link (``page`` is appended)."""
    busqueda = request.GET.get("busqueda", "")
    prefijo = f"busqueda={quote(busqueda, safe='/')}&" if busqueda else ""
    return prefijo + "".join(
        f"{clave}={quote(valor, safe='/')}&"
        for clave, valor in request.GET.items()
        if clave not in ("page", "busqueda")
    )


def _config_filtros(config):
    """The filters config as the page script reads it: option values are the strings ``String(value)`` gives."""
    campos = []
    for campo in config["fields"]:
        opciones = [
            {
                **opcion,
                "value": (
                    str(opcion["value"]).lower()
                    if isinstance(opcion["value"], bool)
                    else str(opcion["value"])
                ),
            }
            for opcion in campo.get("options", [])
        ]
        campos.append({**campo, **({"options": opciones} if opciones else {})})
    return {**config, "fields": campos}


def _fila(centro):
    """One row of ``centro_list.html``; the values print as ``{{ centro.x }}`` does."""
    return {
        "id": centro.pk,
        "nombre": centro.nombre,
        "calle": texto(_TEXTO, v=centro.calle),
        "telefono": texto(_TEXTO, v=centro.telefono),
        "celular": texto(_TEXTO, v=centro.celular),
        "activo": bool(centro.activo),
        "detail_url": reverse("vat_centro_detail", args=[centro.pk]),
        "update_url": reverse("vat_centro_update", args=[centro.pk]),
        "delete_url": reverse("vat_centro_delete", args=[centro.pk]),
    }


class CentroListWebView(VatNativeReadView):
    """``GET .../centros-lista/``: ``centro_list.html`` (filters mode, pages without a count)."""

    native_class = CentroListView
    codigos = _VER

    def get(self, request):
        django_request = request._request  # pylint: disable=protected-access
        vista = self.native()
        vista.object_list = vista.get_queryset()
        try:
            context = vista.get_context_data()
        except Http404 as exc:
            raise NotFound("Página no válida.") from exc
        page = context["page_obj"]
        return Response(
            {
                "filters_config": _config_filtros(context["filters_config"]),
                "favorites": {
                    "section": str(context["seccion_filtros_favoritos"]),
                    "url": reverse("filtros_favoritos"),
                    "detail_url_template": reverse(
                        "detalle_filtro_favorito", kwargs={"pk": 0}
                    ),
                },
                "results": [_fila(centro) for centro in context["centros"]],
                "page": {
                    "is_paginated": bool(context["is_paginated"]),
                    "number": page.number,
                    "previous": (
                        page.previous_page_number() if page.has_previous() else None
                    ),
                    "next": page.next_page_number() if page.has_next() else None,
                    "range": [
                        "…" if numero in ("...", "…") else numero
                        for numero in (
                            context.get("page_range") or build_compact_page_range(page)
                        )
                    ],
                    "query_prefix": _prefijo_paginacion(django_request),
                },
                "can_add": bool(context["can_add"]),
                "permisos": {
                    "eliminar": request.user.has_perm("VAT.delete_centro"),
                },
                "urls": {
                    "list": reverse(_LISTA),
                    "create": reverse("vat_centro_create"),
                },
                "messages": mensajes_pendientes(django_request),
            }
        )


class _CentroBaja(CentroDeleteView):
    """The native delete view: its GET only resolves the object once ``dispatch`` has guarded it."""

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()


class CentroDeleteWebView(VatNativeReadView):
    """``GET|POST .../centros-lista/<pk>/eliminar/``: cascade preview and native soft delete."""

    native_class = _CentroBaja
    codigos = _VER
    http_method_names = ["get", "head", "post"]

    def _despachar(self, pk):
        vista = self.native(pk=pk)
        try:
            respuesta = vista.dispatch(
                self.request._request, pk=pk  # pylint: disable=protected-access
            )
        except Http404 as exc:
            raise NotFound() from exc
        return vista, respuesta

    def get(self, request, pk):
        vista, _respuesta = self._despachar(pk)
        context = vista.get_context_data()
        centro = vista.object
        return Response(
            {
                "id": centro.pk,
                "nombre": centro.nombre,
                "preview": context.get("cascade_preview"),
                "confirm_text": context["confirm_text"],
                "cancel_text": context["cancel_text"],
                "urls": {"detail": reverse("vat_centro_detail", args=[centro.pk])},
                "messages": mensajes_pendientes(
                    request._request  # pylint: disable=protected-access
                ),
            }
        )

    def post(self, request, pk):
        _vista, respuesta = self._despachar(pk)
        return redireccion(respuesta)
