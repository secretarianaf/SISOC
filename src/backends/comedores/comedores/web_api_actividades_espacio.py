"""Web API (G1 v1) of the comedor activity screens served by React (CO03.02).

``/api/web/comedores/actividades-espacio/`` is published by the Comedores backend.
After G1 (``WebGatePermission``) each endpoint keeps the permission codes of its
native URL (``auth.role_admin`` or ``pwa.manage_colaboradores_pwa``) and runs the
native view's own ``dispatch`` (``comedores.views.actividad_espacio_pwa``): the
scoped comedor, the "only PNUD comedores" 404, ``ActividadEspacioPWAWebForm`` (the
schedule rows, their overlaps and the catalog) and the shared PWA service (actor,
audit and the messages that tell one activity from several schedules) stay the
native ones. One schedule is one stored activity row: nothing here turns the
schedules into an array. A native redirect becomes ``{"ok": true, "redirect":
...}``; a rejected request returns 400 with the bound form and writes nothing
(creation and edition are atomic).
"""

from django.contrib import messages
from django.urls import reverse
from rest_framework.response import Response

from comedores.views.actividad_espacio_pwa import (
    ActividadEspacioPWACreateView,
    ActividadEspacioPWAUpdateView,
)
from comedores.web_api_montos import _valor_de_campo
from core.web_gate import WebGatePermission
from intervenciones.web_api import NativeWebView, comedor_ref, requires_any

FORMATOS = ("multipart/form-data", "application/x-www-form-urlencoded")
PERMISOS = ["auth.role_admin", "pwa.manage_colaboradores_pwa"]


def _campo(form, nombre, errores):
    campo = form[nombre]
    return {
        "label": str(campo.label),
        "required": campo.field.required,
        "value": _valor_de_campo(campo),
        "errors": [error["message"] for error in errores.get(nombre, [])],
    }


def _mensajes(request):
    """The flash messages of the native alert block (``alert-{{ message.tags }}``)."""
    return [
        {"message": str(mensaje), "tags": mensaje.tags}
        for mensaje in messages.get_messages(request)
    ]


def _filas_individuales(filas):
    """Proyecta los días agrupados del formulario al contrato Web API v1."""
    for fila in filas:
        valores = fila["values"]
        errores = dict(fila["errors"])
        dias = valores["dias"]
        if "dias" in errores:
            error_dias = errores.pop("dias")
            errores["dia_actividad"] = (
                error_dias if dias else "Este campo es obligatorio."
            )
        for dia in dias or ("",):
            yield {
                "values": {
                    "dia_actividad": str(dia),
                    "hora_inicio": str(valores["hora_inicio"]),
                    "hora_fin": str(valores["hora_fin"]),
                },
                "errors": {campo: str(error) for campo, error in errores.items()},
            }


def _pagina(contexto, request):
    form = contexto["form"]
    comedor = contexto["comedor"]
    errores = form.errors.get_json_data() if form.is_bound else {}
    categoria = _campo(form, "categoria", errores)
    categoria["options"] = [
        {"value": str(valor), "label": str(etiqueta)}
        for valor, etiqueta in form.fields["categoria"].choices
    ]
    vigencia = _campo(form, "vigencia_actividad_meses", errores)
    minimo = form.fields["vigencia_actividad_meses"].widget.attrs.get("min")
    # ``min`` is an int once the model validator overrides the widget's own "1".
    vigencia["min"] = None if minimo is None else str(minimo)
    responsable = _campo(form, "responsable_actividad", errores)
    responsable["max_length"] = form.fields["responsable_actividad"].max_length
    return {
        "comedor": comedor_ref(comedor),
        "edit_mode": bool(contexto["edit_mode"]),
        "fields": {
            "categoria": categoria,
            "catalogo_actividad": _campo(form, "catalogo_actividad", errores),
            "vigencia_actividad_meses": vigencia,
            "responsable_actividad": responsable,
        },
        "non_field_errors": [
            (
                "Completa todos los dias y horarios con formato HH:MM."
                if error["code"] == "schedule_invalid"
                else error["message"]
            )
            for error in errores.get("__all__", [])
        ],
        "activity_options": [
            {
                "id": int(opcion["id"]),
                "categoria": opcion["categoria"],
                "actividad": opcion["actividad"],
            }
            for opcion in form.activity_options
        ],
        "days": [{"id": dia.id, "nombre": dia.nombre} for dia in form.day_options],
        "rows": list(_filas_individuales(form.schedule_form_rows)),
        "messages": _mensajes(request),
        "urls": {
            "comedor": reverse("comedor_detalle", args=[comedor.id]),
            "volver": f"{reverse('comedor_detalle', args=[comedor.id])}"
            "#legajo-actividades-pnud",
        },
    }


class _ActividadWebView(NativeWebView):
    http_method_names = ["get", "post", "head"]
    permission_classes = [WebGatePermission, requires_any(PERMISOS)]
    native_class = None

    def get(self, request, **kwargs):
        vista = self.native(self.native_class, request, **kwargs)
        # The native dispatch: scope, PNUD-only 404, object lookup and context.
        # pylint: disable-next=protected-access
        respuesta = vista.dispatch(request._request, **kwargs)
        return Response(_pagina(respuesta.context_data, request))

    def post(self, request, **kwargs):
        # ``Request.content_type`` keeps the multipart boundary; Django strips it.
        # pylint: disable-next=protected-access
        if request._request.content_type not in FORMATOS:
            return Response({"detail": "Formato de solicitud no admitido."}, status=415)
        vista = self.native(self.native_class, request, **kwargs)
        # pylint: disable-next=protected-access
        respuesta = vista.dispatch(request._request, **kwargs)
        if respuesta.status_code == 302:
            return Response({"ok": True, "redirect": respuesta["Location"]})
        return Response(_pagina(respuesta.context_data, request), status=400)


class ActividadCrearWebView(_ActividadWebView):
    """``/api/web/comedores/actividades-espacio/comedor/<pk>/crear/``."""

    native_class = ActividadEspacioPWACreateView


class ActividadEditarWebView(_ActividadWebView):
    """``/api/web/comedores/actividades-espacio/comedor/<pk>/<pk2>/editar/``."""

    native_class = ActividadEspacioPWAUpdateView
