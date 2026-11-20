"""Web API (G1 v1) of the global app-mobile course catalog served by React (CO04.01).

``/api/web/comedores/cursos-app-mobile/`` is published by the Comedores backend. After
G1 (``WebGatePermission``) each endpoint keeps the permission of its native URL
(``auth.role_admin``) and runs the native view's own ``dispatch``
(``comedores.views.cursos_app_mobile``): the list (20 per page, global), the form
(``CursoAppMobileForm``, image upload included), the actor stamps in a transaction
and the soft delete with its two native messages stay the native ones. A native
redirect becomes ``{"ok": true, "redirect": ...}``; a rejected request returns 400
with the bound form and writes nothing. This module only projects the native
context to JSON; the image is stored by the native form and never read here.
"""

from django.contrib import messages
from django.urls import reverse
from rest_framework.response import Response

from comedores.views.cursos_app_mobile import (
    CursoAppMobileCreateView,
    CursoAppMobileDeleteView,
    CursoAppMobileListView,
    CursoAppMobileUpdateView,
)
from comedores.web_api_montos import _pagina, _valor_de_campo
from core.web_gate import WebGatePermission
from intervenciones.web_api import NativeWebView, requires_any

FORMATOS = ("multipart/form-data", "application/x-www-form-urlencoded")
PERMISOS = ["auth.role_admin"]
# ``form.as_p`` renders each field in this order with the native widget.
CAMPOS = (
    "nombre",
    "link",
    "imagen",
    "descripcion",
    "programa_objetivo",
    "es_recomendado",
    "orden",
    "activo",
)


def _mensajes(request):
    return [
        {"message": str(mensaje), "tags": mensaje.tags}
        for mensaje in messages.get_messages(request)
    ]


def _campo(form, nombre, errores):
    campo = form[nombre]
    widget = campo.field.widget
    minimo = widget.attrs.get("min")
    entrada = {
        "name": nombre,
        "label": str(campo.label),
        "type": getattr(widget, "input_type", "select"),
        "html_required": bool(
            campo.field.required
            and form.use_required_attribute
            and widget.use_required_attribute(campo.initial)
        ),
        "errors": [error["message"] for error in errores.get(nombre, [])],
        "max_length": getattr(campo.field, "max_length", None),
        "min": None if minimo is None else str(minimo),
        "accept": widget.attrs.get("accept"),
    }
    if entrada["type"] == "checkbox":
        entrada["value"] = bool(campo.value())
    elif entrada["type"] == "file":
        entrada["value"] = ""
    else:
        entrada["value"] = _valor_de_campo(campo)
    if entrada["type"] == "select":
        entrada["choices"] = [
            {"value": str(valor), "label": str(etiqueta)}
            for valor, etiqueta in campo.field.choices
        ]
    return entrada


def _formulario(contexto, request):
    form = contexto["form"]
    errores = form.errors.get_json_data() if form.is_bound else {}
    return {
        "edit_mode": contexto.get("object") is not None,
        "fields": [_campo(form, nombre, errores) for nombre in CAMPOS],
        "non_field_errors": [error["message"] for error in errores.get("__all__", [])],
        "messages": _mensajes(request),
        "urls": {"list": reverse("cursos_app_mobile_list")},
    }


def _fila(curso):
    return {
        "id": curso.pk,
        "nombre": curso.nombre,
        "programa": curso.get_programa_objetivo_display(),
        "link": curso.link,
        "orden": curso.orden,
        "es_recomendado": bool(curso.es_recomendado),
        "activo": bool(curso.activo),
        "tiene_imagen": bool(curso.imagen),
        "urls": {
            "editar": reverse("cursos_app_mobile_editar", args=[curso.pk]),
            "eliminar": reverse("cursos_app_mobile_eliminar", args=[curso.pk]),
        },
    }


class _CursoWebView(NativeWebView):
    http_method_names = ["get", "post", "head"]
    permission_classes = [WebGatePermission, requires_any(PERMISOS)]
    native_class = None

    def dispatch_nativo(self, request, **kwargs):
        vista = self.native(self.native_class, request, **kwargs)
        # The native dispatch: login, list paging (404 out of range) or object lookup.
        # pylint: disable-next=protected-access
        return vista.dispatch(request._request, **kwargs)


class CursosListWebView(_CursoWebView):
    """``GET /api/web/comedores/cursos-app-mobile/``: the native list, 20 per page."""

    http_method_names = ["get", "head"]
    native_class = CursoAppMobileListView

    def get(self, request):
        contexto = self.dispatch_nativo(request).context_data
        django_request = request._request  # pylint: disable=protected-access
        return Response(
            {
                "results": [_fila(curso) for curso in contexto["cursos"]],
                "page": _pagina(contexto, django_request),
                "messages": _mensajes(request),
                "urls": {"crear": reverse("cursos_app_mobile_crear")},
            }
        )


class _FormularioWebView(_CursoWebView):
    def get(self, request, **kwargs):
        return Response(
            _formulario(self.dispatch_nativo(request, **kwargs).context_data, request)
        )

    def post(self, request, **kwargs):
        # ``Request.content_type`` keeps the multipart boundary; Django strips it.
        # pylint: disable-next=protected-access
        if request._request.content_type not in FORMATOS:
            return Response({"detail": "Formato de solicitud no admitido."}, status=415)
        respuesta = self.dispatch_nativo(request, **kwargs)
        if respuesta.status_code == 302:
            return Response({"ok": True, "redirect": respuesta["Location"]})
        return Response(_formulario(respuesta.context_data, request), status=400)


class CursoCrearWebView(_FormularioWebView):
    """``/api/web/comedores/cursos-app-mobile/crear/``."""

    native_class = CursoAppMobileCreateView


class CursoEditarWebView(_FormularioWebView):
    """``/api/web/comedores/cursos-app-mobile/<pk>/editar/``."""

    native_class = CursoAppMobileUpdateView


class CursoBajaWebView(_CursoWebView):
    """``/api/web/comedores/cursos-app-mobile/<pk>/eliminar/``: native soft-delete confirm.

    The POST is the native logical delete (never ``activo=False``): the curso keeps
    its row and the native view's two messages are queued for the list.
    """

    native_class = CursoAppMobileDeleteView

    def get(self, request, pk):
        contexto = self.dispatch_nativo(request, pk=pk).context_data
        return Response(
            {
                "nombre": contexto["object"].nombre,
                "cancel_url": contexto["cancel_url"],
                "messages": _mensajes(request),
            }
        )

    def post(self, request, pk):
        respuesta = self.dispatch_nativo(request, pk=pk)
        return Response({"ok": True, "redirect": respuesta["Location"]})
