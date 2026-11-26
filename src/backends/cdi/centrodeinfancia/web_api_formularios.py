"""Shared transport of the CDI form screens (G1 v1) for the React pages.

Session transport over native views: each API view inherits the native view,
so forms, scope, messages and the CDI-A3 auditor veto stay the native ones.
Order of checks:

1. G1 (``WebGatePermission``): 401/403 JSON, or the signed attestation.
2. The same permission code(s) as the URL decorator in ``centrodeinfancia/urls.py``.
3. The native dispatch.

A native redirect becomes ``{"ok": true, "redirect": <Location>}``; an invalid
form returns 400 with its errors. Responses are ``private, no-store``.

This module also projects a Django form field to JSON (``campo_web``) and the
RENAPER block of a form (``bloque_renaper_web``) and serves the RENAPER lookup
of ``centrodeinfancia_renaper_bloque`` behind the same guards.
"""

from django.core.exceptions import PermissionDenied
from django.http import Http404, JsonResponse
from django.urls import reverse
from django.utils.cache import patch_cache_control, patch_vary_headers
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.exceptions import APIException

from centrodeinfancia.services_renaper_bloques import (
    TIPOS_DOCUMENTO_CON_DNI,
    TIPO_DOCUMENTO_POR_BLOQUE,
)
from centrodeinfancia.views import consultar_renaper_bloque
from core.decorators import permissions_any_required
from core.web_gate import WebGatePermission

SIN_PERMISO = "No tiene permisos para esta acción."
NO_ENCONTRADO = "No encontrado."
PERMISOS_RENAPER = (
    "centrodeinfancia.add_centrodeinfancia",
    "centrodeinfancia.change_centrodeinfancia",
    "centrodeinfancia.add_nominacentroinfancia",
    "centrodeinfancia.change_nominacentroinfancia",
)


def privada(response):
    patch_cache_control(response, private=True, no_store=True)
    patch_vary_headers(response, ("Cookie",))
    return response


def json_privado(body, status=200):
    return privada(JsonResponse(body, status=status))


def puerta_g1(request):
    """``WebGatePermission`` for a Django view: the same 401/403 bodies as DRF."""
    try:
        WebGatePermission().has_permission(request, None)
    except APIException as exc:
        detail = exc.detail if isinstance(exc.detail, dict) else {"detail": exc.detail}
        response = json_privado(
            {key: str(value) for key, value in detail.items()}, exc.status_code
        )
        if exc.status_code == 401:
            response["WWW-Authenticate"] = "Session"
        return response
    return None


class TransporteFormularioMixin:
    """G1, the URL permission and the native dispatch, as JSON."""

    permission_codes = ()
    http_method_names = ["get", "head", "post"]

    def dispatch(self, request, *args, **kwargs):
        response = puerta_g1(request)
        if response is not None:
            return response
        guardada = permissions_any_required(list(self.permission_codes))(
            lambda req: self._nativa(req, *args, **kwargs)
        )
        try:
            response = guardada(request)
        except PermissionDenied as exc:
            return json_privado({"detail": str(exc) or SIN_PERMISO}, 403)
        except Http404:
            return json_privado({"detail": NO_ENCONTRADO}, 404)
        if response.status_code == 302:
            convertida = JsonResponse({"ok": True, "redirect": response["Location"]})
            convertida.cookies = response.cookies
            response = convertida
        return privada(response)

    def _nativa(self, request, *args, **kwargs):
        if request.method.lower() not in self.http_method_names:
            return self.http_method_not_allowed(request, *args, **kwargs)
        if (
            request.method == "POST"
            and request.body
            and request.content_type != "application/x-www-form-urlencoded"
        ):
            return JsonResponse(
                {"detail": "Formato de solicitud no admitido."}, status=415
            )
        return super().dispatch(request, *args, **kwargs)


def _atributos(campo):
    widget = campo.widget
    atributos = {**campo.widget_attrs(widget), **widget.attrs}
    for clave in ("class", "data-renaper"):
        atributos.pop(clave, None)
    return {
        clave: str(valor)
        for clave, valor in atributos.items()
        if valor not in (None, False)
    }


def campo_web(form, nombre):
    """One field as the crispy template renders it (label, widget, help, value)."""
    bound = form[nombre]
    campo = bound.field
    valor = bound.value()
    return {
        "name": nombre,
        "label": str(bound.label or ""),
        "required": bool(campo.required),
        "disabled": bool(campo.disabled),
        "widget": getattr(campo.widget, "input_type", "text"),
        "help_text": str(campo.help_text or ""),
        "value": "" if valor is None else str(valor),
        "attrs": _atributos(campo),
        "renaper": bool(campo.widget.attrs.get("data-renaper")),
        "errors": (
            [
                {"message": error["message"], "code": error["code"]}
                for error in bound.errors.get_json_data()
            ]
            if form.is_bound
            else []
        ),
        "choices": (
            [
                {"value": str(opcion), "label": str(etiqueta)}
                for opcion, etiqueta in getattr(campo, "choices", [])
            ]
            if hasattr(campo, "choices")
            else None
        ),
    }


def bloque_renaper_web(form, bloque, token, *, permite_cambiar, opcional=False):
    """Data attributes of ``partials/renaper_bloque.html`` for one block."""
    return {
        "bloque": bloque,
        "url": reverse("centrodeinfancia_renaper_bloque", args=[bloque]),
        "modo": form.modos_renaper[bloque],
        "campos": form.campos_bloque_renaper[bloque].split(","),
        "tipo_field": TIPO_DOCUMENTO_POR_BLOQUE.get(bloque, ""),
        "tipos_con_dni": list(TIPOS_DOCUMENTO_CON_DNI),
        "verificado": bool(form.bloques_verificados_renaper[bloque]),
        "permite_cambiar": permite_cambiar,
        "opcional": opcional,
        "token": token or "",
    }


@ensure_csrf_cookie
def renaper_bloque_web(request, bloque):
    """``GET /api/web/cdi/renaper/<bloque>/?dni=``: the native RENAPER lookup."""
    if request.method not in ("GET", "HEAD"):
        respuesta = json_privado({"detail": "Método no permitido."}, 405)
        respuesta["Allow"] = "GET, HEAD"
        return respuesta
    bloqueo = puerta_g1(request)
    if bloqueo is not None:
        return bloqueo
    guardada = permissions_any_required(list(PERMISOS_RENAPER))(
        lambda req: consultar_renaper_bloque(req, bloque)
    )
    try:
        return privada(guardada(request))
    except PermissionDenied as exc:
        return json_privado({"detail": str(exc) or SIN_PERMISO}, 403)
    except Http404:
        return json_privado({"detail": NO_ENCONTRADO}, 404)
