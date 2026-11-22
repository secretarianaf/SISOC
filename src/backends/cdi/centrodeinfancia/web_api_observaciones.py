"""Web API (G1 v1) of the CDI observation screens (CDI07) for the React pages.

Session transport over the native observation views: each API view inherits
the native create/detail/edit/delete view, so the form, the scope, the
server-side centre/author/date, ``safe_redirect`` with ``next``, the soft
delete and its message stay the native ones. Order of checks:

1. G1 (``WebGatePermission``): 401/403 JSON, or the signed attestation in the
   runtime.
2. The same permission code as the URL decorator in ``centrodeinfancia/urls.py``
   (Add/ViewCentro/Change/DeleteIntervención; no new Observacion permissions).
3. The native dispatch, including the CDI-A3 read-only veto for SIMEPI
   auditors on every non-GET (``_AuditoriaSoloLecturaMixin``).

A native redirect becomes ``{"ok": true, "redirect": <Location>}``; an invalid
form returns 400 with its errors. Responses are ``private, no-store``.
"""

from django.core.exceptions import PermissionDenied
from django.http import Http404, JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.cache import patch_cache_control, patch_vary_headers
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework.exceptions import APIException

from centrodeinfancia.views import (
    ObservacionCentroInfanciaCreateView,
    ObservacionCentroInfanciaDeleteView,
    ObservacionCentroInfanciaDetailView,
    ObservacionCentroInfanciaUpdateView,
)
from centrodeinfancia.web_api import pending_messages
from core.decorators import permissions_any_required
from core.web_gate import WebGatePermission

PERMISO_VER = "centrodeinfancia.view_centrodeinfancia"
PERMISO_ALTA = "centrodeinfancia.add_intervencioncentroinfancia"
PERMISO_EDICION = "centrodeinfancia.change_intervencioncentroinfancia"
PERMISO_BAJA = "centrodeinfancia.delete_intervencioncentroinfancia"
SIN_PERMISO = "No tiene permisos para esta acción."
NO_ENCONTRADA = "No encontrado."


def _privada(response):
    patch_cache_control(response, private=True, no_store=True)
    patch_vary_headers(response, ("Cookie",))
    return response


def _json(body, status=200):
    return _privada(JsonResponse(body, status=status))


def _gate(request):
    """``WebGatePermission`` for a Django view: the same 401/403 bodies as DRF."""
    try:
        WebGatePermission().has_permission(request, None)
    except APIException as exc:
        detail = exc.detail if isinstance(exc.detail, dict) else {"detail": exc.detail}
        response = _json(
            {key: str(value) for key, value in detail.items()}, exc.status_code
        )
        if exc.status_code == 401:
            response["WWW-Authenticate"] = "Session"
        return response
    return None


def _centro(centro_id, nombre):
    return {
        "id": centro_id,
        "nombre": nombre,
        "url": reverse("centrodeinfancia_detalle", args=[centro_id]),
    }


class _ObservacionTransportMixin:
    """G1, the URL permission and the native dispatch, as JSON."""

    permission_code = ""
    http_method_names = ["get", "head", "post"]

    def dispatch(self, request, *args, **kwargs):
        response = _gate(request)
        if response is not None:
            return response
        # Same decorator as the native URL (superusers keep their bypass); it
        # wraps the native dispatch, so it runs before the view, as in urls.py.
        guarded = permissions_any_required([self.permission_code])(
            lambda req: self._native(req, *args, **kwargs)
        )
        try:
            response = guarded(request)
        except PermissionDenied as exc:
            return _json({"detail": str(exc) or SIN_PERMISO}, 403)
        except Http404:
            return _json({"detail": NO_ENCONTRADA}, 404)
        if response.status_code == 302:
            converted = JsonResponse({"ok": True, "redirect": response["Location"]})
            converted.cookies = response.cookies
            response = converted
        return _privada(response)

    def _native(self, request, *args, **kwargs):
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


class _FormTransportMixin(_ObservacionTransportMixin):
    def form_invalid(self, form):
        return self.render_to_response(self.get_context_data(form=form), status=400)

    def render_to_response(self, context, **response_kwargs):
        form = context["form"]
        campo = form.fields["observacion"]
        attrs = campo.widget.attrs
        return JsonResponse(
            {
                # The native context carries the scoped centre as id/nombre.
                "centro": _centro(context["centro"]["id"], context["centro"]["nombre"]),
                "field": {
                    "name": "observacion",
                    "label": str(campo.label),
                    "required": campo.required,
                    "rows": int(attrs.get("rows", 4)),
                    "placeholder": str(attrs.get("placeholder", "")),
                },
                "value": form["observacion"].value() or "",
                "errors": form.errors.get_json_data() if form.is_bound else {},
                "messages": pending_messages(self.request),
            },
            status=response_kwargs.get("status", 200),
        )


@method_decorator(ensure_csrf_cookie, name="dispatch")
@method_decorator(csrf_protect, name="dispatch")
class ObservacionCrearWebView(_FormTransportMixin, ObservacionCentroInfanciaCreateView):
    """``/api/web/cdi/centros/<pk>/observaciones/crear/``: native create."""

    permission_code = PERMISO_ALTA


@method_decorator(ensure_csrf_cookie, name="dispatch")
@method_decorator(csrf_protect, name="dispatch")
class ObservacionEditarWebView(
    _FormTransportMixin, ObservacionCentroInfanciaUpdateView
):
    """``/api/web/cdi/observaciones/<pk>/editar/``: native edit."""

    permission_code = PERMISO_EDICION


class ObservacionDetalleWebView(
    _ObservacionTransportMixin, ObservacionCentroInfanciaDetailView
):
    """``GET /api/web/cdi/observaciones/<pk>/``: the native detail card."""

    permission_code = PERMISO_VER
    http_method_names = ["get", "head"]

    def render_to_response(self, context, **response_kwargs):
        observacion = context["observacion"]
        fecha = observacion.fecha_visita
        return JsonResponse(
            {
                "id": observacion.id,
                "centro": _centro(observacion.centro.id, observacion.centro.nombre),
                "observador": observacion.observador or "-",
                "fecha": (
                    timezone.localtime(fecha).strftime("%d/%m/%Y %H:%M")
                    if fecha
                    else ""
                ),
                "observacion": observacion.observacion,
                "urls": {
                    "editar": reverse(
                        "centrodeinfancia_observacion_editar", args=[observacion.id]
                    ),
                    "eliminar": reverse(
                        "centrodeinfancia_observacion_eliminar", args=[observacion.id]
                    ),
                },
                "messages": pending_messages(self.request),
            }
        )


@method_decorator(ensure_csrf_cookie, name="dispatch")
@method_decorator(csrf_protect, name="dispatch")
class ObservacionEliminarWebView(
    _ObservacionTransportMixin, ObservacionCentroInfanciaDeleteView
):
    """``/api/web/cdi/observaciones/<pk>/eliminar/``: native soft-delete confirm."""

    permission_code = PERMISO_BAJA

    def render_to_response(self, context, **response_kwargs):
        observacion = context["observacion"]
        preview = context.get("cascade_preview")
        return JsonResponse(
            {
                "id": observacion.id,
                "centro": _centro(observacion.centro.id, observacion.centro.nombre),
                "object_name": str(observacion).upper(),
                "cascade_preview": _preview(preview) if preview else None,
                "confirm_text": str(context["confirm_text"]),
                "cancel_text": str(context["cancel_text"]),
                "cancel_url": reverse(
                    "centrodeinfancia_observacion_detalle", args=[observacion.id]
                ),
                "messages": pending_messages(self.request),
            },
            status=response_kwargs.get("status", 200),
        )


def _preview(preview):
    return {
        "total_afectados": preview.get("total_afectados", 0),
        "total_baja_logica": preview.get("total_baja_logica", 0),
        "total_borrado_fisico": preview.get("total_borrado_fisico", 0),
        "desglose_por_modelo": [
            {
                "modelo": str(item.get("modelo", "")),
                "cantidad": item.get("cantidad", 0),
                "modo": item.get("modo", ""),
                "ejemplos": [str(ejemplo) for ejemplo in item.get("ejemplos") or []],
            }
            for item in preview.get("desglose_por_modelo", [])
        ],
    }
