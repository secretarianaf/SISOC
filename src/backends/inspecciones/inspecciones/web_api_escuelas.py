"""Web API (G1 v1) of the Escuelas tab (IN05): panel, school form and localities.

``GET /api/web/inspecciones/escuelas/`` runs ``EscuelasView`` itself (filters,
order, 25 per page, invalid page 404, totals, "A revisar" chip) and projects
its context. The form routes run ``EscuelaCrearView`` / ``EscuelaEditarView``:
GET returns the form as data (values, errors, initial locality, review
notice); POST runs the native ``post()``. As in ``panel.js`` the modal sends
``X-Requested-With: XMLHttpRequest``: success answers the native
``{"ok", "mensaje", "otra"}`` and the page mode answers the native redirect as
``{"ok": true, "redirect": ...}``; an invalid form answers the same form data
with its errors (400) instead of HTML. Import stays the native multipart form.
Access: ``WebGatePermission`` and then the native ``puede_gestionar``.
"""

import json

from django.http import Http404, JsonResponse
from django.template.defaultfilters import date as formato_fecha
from django.urls import reverse
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from inspecciones.views import es_parcial
from inspecciones.views_ajax import LocalidadesAjaxView
from inspecciones.views_escuelas import (
    EscuelaCrearView,
    EscuelaEditarView,
    EscuelasView,
)
from inspecciones.web_api import _layout, _pagina, _pestanas, _WebView
from inspecciones.web_api_acta import pending_messages

SIN_DATO = "—"
CAMPOS = (
    "provincia",
    "localidad",
    "cueanexo",
    "cp",
    "nombre",
    "domicilio",
    "telefono",
    "mail",
)


def _o(valor):
    """``|default:"—"``."""
    return str(valor) if valor else SIN_DATO


def _raw(valor):
    """``|default:''`` of a bound value."""
    return str(valor) if valor else ""


def _native(django_request, view_class, **kwargs):
    vista = view_class()
    vista.setup(django_request, **kwargs)
    return vista


def _localidad(escuela):
    if escuela.localidad_vinculada_id:
        distrito = escuela.distrito
        return {
            "vinculada": True,
            "texto": str(escuela.localidad),
            "distrito": (
                distrito if distrito and distrito != escuela.localidad else ""
            ),
            "aviso": "",
        }
    motivos = escuela.motivos_revision or []
    aviso = ""
    if "localidad_repetida" in motivos:
        aviso = "localidad repetida"
    elif "localidad_inexistente" in motivos:
        aviso = "localidad a revisar"
    return {
        "vinculada": False,
        "texto": _o(escuela.localidad_original or escuela.localidad),
        "distrito": "",
        "aviso": aviso,
    }


def _fila(escuela):
    mail_invalido = "mail_invalido" in (escuela.motivos_revision or [])
    return {
        "id": escuela.pk,
        "cueanexo": str(escuela.cueanexo),
        "nombre": escuela.nombre,
        "provincia": _o(escuela.provincia.nombre if escuela.provincia_id else ""),
        "localidad": _localidad(escuela),
        "domicilio": _o(escuela.domicilio),
        "cp": _o(escuela.cp),
        "telefono": _o(escuela.telefono),
        "mail": escuela.mail if mail_invalido else _o(escuela.mail),
        "mail_invalido": mail_invalido,
        "form_url": reverse("inspecciones_web_escuela_editar", args=[escuela.pk]),
    }


def _totales(totales):
    """``totales_panel`` of ``PanelMixin`` (only the Escuelas tab shows it)."""
    return {
        "escuelas": totales["escuelas"],
        "escuelas_a_revisar": totales["escuelas_a_revisar"],
        "jornada": formato_fecha(totales["jornada"], "d/m"),
        "asignaciones_hoy": totales["asignaciones_hoy"],
        "actas_hoy": totales["actas_hoy"],
    }


def _provincias(queryset):
    return [{"id": provincia.pk, "nombre": provincia.nombre} for provincia in queryset]


class EscuelasWebView(_WebView):
    """``GET /api/web/inspecciones/escuelas/``: the Escuelas tab."""

    http_method_names = ["get", "head"]

    def get(self, request):
        django_request = request._request  # pylint: disable=protected-access
        vista = _native(django_request, EscuelasView)
        try:
            vista.object_list = vista.get_queryset()
            context = vista.get_context_data()
        except Http404 as exc:
            raise NotFound() from exc
        context["request"] = request
        filtro = context["filtro"]
        activo = context["a_revisar_activo"]
        sin_revisar = context["parametros_sin_revisar"]
        chip = f"?{sin_revisar}"
        if not activo:
            chip += f"{'&' if sin_revisar else ''}a_revisar=1"
        editar = context["editar_id"]
        return Response(
            {
                "layout": _layout(context),
                "tabs": _pestanas(),
                "totales": _totales(context["totales_panel"]),
                "filters": {
                    "q": _raw(filtro["q"].value()),
                    "provincia": _raw(filtro["provincia"].value()),
                    "localidad": context["localidad_filtro"],
                },
                "options": {
                    "provincias": _provincias(filtro.fields["provincia"].queryset),
                    "localidades_url": reverse("inspecciones_web_localidades"),
                },
                "a_revisar": {
                    "activo": activo,
                    "contador": context["contador_a_revisar"],
                    "url": chip,
                },
                "results": [_fila(escuela) for escuela in context["escuelas"]],
                "page": _pagina(context),
                "urls": {
                    "nueva": reverse("inspecciones_web_escuela_nueva"),
                    "importar": reverse("inspecciones_importar_escuelas"),
                },
                "editar_url": (
                    reverse("inspecciones_web_escuela_editar", args=[editar])
                    if editar
                    else None
                ),
                "messages": pending_messages(request),
            }
        )


def _campo(form, nombre):
    campo = form[nombre]
    return {"value": _raw(campo.value()), "errors": [str(e) for e in campo.errors]}


def _form_payload(context, request, *, mensajes):
    form = context["form"]
    escuela = context["escuela"]
    duplicada = form.escuela_duplicada
    aviso = None
    if escuela is not None and escuela.a_revisar:
        aviso = {
            "motivos": "; ".join(str(m) for m in escuela.motivos_revision_display),
            "localidad_original": escuela.localidad_original or "",
        }
    return {
        "layout": _layout(context),
        "tabs": _pestanas(),
        "totales": _totales(context["totales_panel"]),
        "editar": escuela is not None,
        "aviso": aviso,
        "non_field_errors": [str(e) for e in form.non_field_errors()],
        "fields": {nombre: _campo(form, nombre) for nombre in CAMPOS},
        "localidad_inicial": context["localidad_inicial"],
        "duplicada_url": (
            f"{reverse('inspecciones_panel')}?editar={duplicada.pk}"
            if duplicada is not None and not duplicada.deleted_at
            else None
        ),
        "options": {
            "provincias": _provincias(form.fields["provincia"].queryset),
            "localidades_url": reverse("inspecciones_web_localidades"),
        },
        "messages": pending_messages(request) if mensajes else [],
    }


class _EscuelaFormWebView(_WebView):
    """GET: the native form as data. POST: the native ``post()``."""

    http_method_names = ["get", "post"]
    view_class = EscuelaCrearView

    def _vista(self, request, kwargs):
        django_request = request._request  # pylint: disable=protected-access
        return _native(django_request, self.view_class, **kwargs)

    def get(self, request, **kwargs):
        vista = self._vista(request, kwargs)
        try:
            context = vista.get_context_data()
        except Http404 as exc:
            raise NotFound() from exc
        context["request"] = request
        # The modal fragment does not render messages; the page does.
        return Response(
            _form_payload(context, request, mensajes=not es_parcial(request))
        )

    def post(self, request, **kwargs):
        django_request = request._request  # pylint: disable=protected-access
        vista = self._vista(request, kwargs)
        try:
            respuesta = vista.post(django_request, **kwargs)
        except Http404 as exc:
            raise NotFound() from exc
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


class EscuelaNuevaWebView(_EscuelaFormWebView):
    """``/api/web/inspecciones/escuelas/nueva/`` (``EscuelaCrearView``)."""

    view_class = EscuelaCrearView


class EscuelaEditarWebView(_EscuelaFormWebView):
    """``/api/web/inspecciones/escuelas/<pk>/editar/`` (``EscuelaEditarView``)."""

    view_class = EscuelaEditarView


class LocalidadesWebView(_WebView):
    """``GET /api/web/inspecciones/localidades/``: the J2 locality search.

    Same service, ``provincia`` scope and 30-result limit as
    ``views_ajax.LocalidadesAjaxView``; the response is ``{"results": [...]}``.
    """

    http_method_names = ["get"]

    def get(self, request):
        django_request = request._request  # pylint: disable=protected-access
        return Response({"results": LocalidadesAjaxView().resultados(django_request)})
