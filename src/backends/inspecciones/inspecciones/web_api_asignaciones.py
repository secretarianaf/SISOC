"""Web API (G1 v1) of the Asignaciones tab (IN02): day list, form and removal.

``GET /api/web/inspecciones/asignaciones/`` runs ``AsignacionesView`` itself
(day, filters, ordering, 25 per page, invalid page 404) and projects its
context; the day totals come from the native service, which ignores the state
filters, so the client never derives them from the page rows. The form route
runs ``AsignacionCrearView``: GET returns the form as data, POST runs the
native ``post()``. As in ``panel.js`` the modal sends
``X-Requested-With: XMLHttpRequest``: success answers the native
``{"ok", "mensaje", "otra"}`` and the page mode answers the native redirect as
``{"ok": true, "redirect": ...}``; an invalid form answers the form data with
its errors (400) instead of HTML. ``asignaciones/<pk>/quitar/`` runs
``AsignacionQuitarView.post`` (POST only) and answers its redirect. Access:
``WebGatePermission`` and then the native ``puede_gestionar``.
"""

import json

from django.http import Http404, JsonResponse
from django.urls import reverse
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from inspecciones.views import es_parcial
from inspecciones.views_ajax import EscuelasAjaxView, VerificarAsignacionAjaxView
from inspecciones.views_asignaciones import (
    AsignacionCrearView,
    AsignacionesView,
    AsignacionQuitarView,
)
from inspecciones.web_api import _layout, _pagina, _pestanas, _WebView
from inspecciones.web_api_acta import pending_messages
from inspecciones.web_api_escuelas import _native, _provincias, _raw


def _choices(campo):
    return [
        {"value": valor, "label": str(etiqueta)} for valor, etiqueta in campo.choices
    ]


def _opcion(opcion):
    return {"id": opcion["id"], "text": opcion["text"]} if opcion else None


def _fila(fila):
    asignacion = fila["asignacion"]
    escuela = fila["escuela"]
    inspector = fila["inspector"]
    return {
        "id": asignacion.pk,
        "iniciales": fila["iniciales"],
        "inspector": {
            "nombre": inspector.get_full_name() or inspector.username,
            "usuario": inspector.username,
        },
        "escuela": {
            "nombre": escuela.nombre,
            "cueanexo": str(escuela.cueanexo),
            "localidad": str(escuela.localidad) if escuela.localidad else "—",
            "provincia": escuela.provincia.nombre if escuela.provincia_id else "",
        },
        "estado": fila["estado"],
        "estado_display": fila["estado_display"],
        "actas": [
            {
                "numero": acta.numero,
                "url": reverse("inspecciones_acta_detalle", args=[acta.numero]),
                "anulada": acta.estado == "anulada",
                "prueba": bool(acta.es_prueba),
            }
            for acta in fila["actas"]
        ],
        "se_puede_quitar": fila["se_puede_quitar"],
        "quitar_url": reverse(
            "inspecciones_web_asignacion_quitar", args=[asignacion.pk]
        ),
    }


class AsignacionesWebView(_WebView):
    """``GET /api/web/inspecciones/asignaciones/``: the Asignaciones tab."""

    http_method_names = ["get", "head"]

    def get(self, request):
        django_request = request._request  # pylint: disable=protected-access
        vista = _native(django_request, AsignacionesView)
        try:
            context = vista.get_context_data()
        except Http404 as exc:
            raise NotFound() from exc
        context["request"] = request
        filtro = context["filtro"]
        totales = context["totales"]
        fecha = context["fecha"].isoformat()
        return Response(
            {
                "layout": _layout(context),
                "tabs": _pestanas(),
                "filters": {
                    "fecha": fecha,
                    "inspector": _opcion(context["inspector_filtro"]),
                    "escuela": _opcion(context["escuela_filtro"]),
                    "provincia": _raw(filtro["provincia"].value()),
                    "estado": _raw(filtro["estado"].value()),
                    "estado_acta": _raw(filtro["estado_acta"].value()),
                },
                "day": {
                    "es_hoy": context["es_hoy"],
                    "anterior": context["url_anterior"],
                    "siguiente": context["url_siguiente"],
                    "hoy": context["url_hoy"],
                },
                "options": {
                    "provincias": _provincias(filtro.fields["provincia"].queryset),
                    "estados": _choices(filtro.fields["estado"]),
                    "estados_acta": _choices(filtro.fields["estado_acta"]),
                    "inspectores_url": reverse("inspecciones_web_inspectores")
                    + "?alcance=programa",
                    "escuelas_url": reverse("inspecciones_web_escuelas_buscar"),
                },
                "totales": {
                    clave: totales[clave]
                    for clave in (
                        "total",
                        "pendiente",
                        "en_curso",
                        "finalizada",
                        "inspectores",
                    )
                },
                "results": [_fila(fila) for fila in context["filas"]],
                "page": _pagina(context),
                "urls": {
                    "nueva": f"{reverse('inspecciones_web_asignacion_nueva')}"
                    f"?fecha={fecha}",
                    "importar": reverse("inspecciones_importar_asignaciones"),
                },
                "messages": pending_messages(request),
            }
        )


def _valor(campo):
    valor = campo.value()
    return valor.isoformat() if hasattr(valor, "isoformat") else _raw(valor)


def _campo(form, nombre):
    campo = form[nombre]
    return {"value": _valor(campo), "errors": [str(e) for e in campo.errors]}


def _form_payload(context, request, *, mensajes):
    form = context["form"]
    return {
        "layout": _layout(context),
        "tabs": _pestanas(),
        "non_field_errors": [str(e) for e in form.non_field_errors()],
        "fields": {
            nombre: _campo(form, nombre) for nombre in ("fecha", "inspector", "escuela")
        },
        "inspector_inicial": _opcion(context.get("inspector_inicial")),
        "escuela_inicial": _opcion(context.get("escuela_inicial")),
        "options": {
            "inspectores_url": reverse("inspecciones_web_inspectores"),
            "escuelas_url": reverse("inspecciones_web_escuelas_buscar"),
            "verificar_url": reverse("inspecciones_web_asignacion_verificar"),
        },
        "messages": pending_messages(request) if mensajes else [],
    }


class AsignacionNuevaWebView(_WebView):
    """``/api/web/inspecciones/asignaciones/nueva/`` (``AsignacionCrearView``)."""

    http_method_names = ["get", "post"]

    def get(self, request):
        django_request = request._request  # pylint: disable=protected-access
        vista = _native(django_request, AsignacionCrearView)
        context = vista.get_context_data()
        context["request"] = request
        # The modal fragment does not render messages; the page does.
        return Response(
            _form_payload(context, request, mensajes=not es_parcial(request))
        )

    def post(self, request):
        django_request = request._request  # pylint: disable=protected-access
        vista = _native(django_request, AsignacionCrearView)
        respuesta = vista.post(django_request)
        if isinstance(respuesta, JsonResponse):
            return Response(json.loads(respuesta.content))
        if respuesta.status_code == 302:
            return Response({"ok": True, "redirect": respuesta["Location"]})
        context = respuesta.context_data
        context["request"] = request
        return Response(
            _form_payload(context, request, mensajes=not es_parcial(request)),
            status=400,
        )


class AsignacionQuitarWebView(_WebView):
    """``POST /api/web/inspecciones/asignaciones/<pk>/quitar/``."""

    http_method_names = ["post"]

    def post(self, request, pk):
        django_request = request._request  # pylint: disable=protected-access
        vista = _native(django_request, AsignacionQuitarView, pk=pk)
        try:
            respuesta = vista.post(django_request, pk=pk)
        except Http404 as exc:
            raise NotFound() from exc
        return Response({"ok": True, "redirect": respuesta["Location"]})


class VerificarAsignacionWebView(_WebView):
    """``GET /api/web/inspecciones/asignaciones/verificar/``: «otra visita» notice.

    Same form and service as ``views_ajax.VerificarAsignacionAjaxView``.
    """

    http_method_names = ["get"]

    def get(self, request):
        django_request = request._request  # pylint: disable=protected-access
        respuesta = VerificarAsignacionAjaxView().get(django_request)
        return Response(json.loads(respuesta.content))


class EscuelasBuscarWebView(_WebView):
    """``GET /api/web/inspecciones/escuelas/buscar/``: the J2 school search.

    Same service, threshold and 20-result limit as
    ``views_ajax.EscuelasAjaxView``; the response is ``{"results": [...]}``.
    """

    http_method_names = ["get"]

    def get(self, request):
        django_request = request._request  # pylint: disable=protected-access
        return Response({"results": EscuelasAjaxView().resultados(django_request)})
