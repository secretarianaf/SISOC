"""Web API (G1 v1) of the signers (firmantes) and guarantors (avales) (O03).

The forms and the baja run the native views themselves
(``FirmanteCreateView`` / ``FirmanteUpdateView`` / ``FirmanteDeleteView`` and
the ``Aval`` equivalents): the allowed roles by tipo de entidad, the limited
programs, the one-role-per-organization rule, the ``organizacion_id`` taken
from the body (never from the URL, as the native create does), the
"guardar y agregar otro" flow, the logical baja with its cascade preview and
messages. Access is today's: ``organizaciones.view_organizacion`` on the route,
no object scope (see
``docs/registro/decisiones/2026-11-10-2785-brechas-acceso-conservadas.md``).
The legajo "Firmantes" tables (``legajo/firmantes.html``) are delivered as
sections (``web_api_secciones``); the "Avales" table is inline markup in the
legajo block, so it is delivered through ``seccion_en_linea``.
"""

from django.http import HttpResponseRedirect
from django.urls import reverse
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from core.web_gate import WebGatePermission
from gestion_organizaciones.views import (
    AvalCreateView,
    AvalDeleteView,
    AvalUpdateView,
    FirmanteCreateView,
    FirmanteDeleteView,
    FirmanteUpdateView,
)
from gestion_organizaciones.web_api import _pending_messages
from gestion_organizaciones.web_api_abm import OrganizacionAbmAccess, _campo
from gestion_organizaciones.web_api_secciones import seccion, seccion_en_linea


@seccion("organizaciones/partials/legajo/firmantes.html")
def seccion_firmantes(contexto):
    """``legajo/firmantes.html``: one table of signers (a program or "sin programa")."""
    organizacion = contexto["organizacion"]
    gestionar = bool(contexto.get("puede_gestionar_organizaciones"))
    return {
        "kind": "firmantes",
        "title": contexto.get("titulo") or "",
        "color": contexto.get("color") or "otro",
        "show_program": bool(contexto.get("mostrar_programa")),
        "can_manage": gestionar,
        "add_url": (
            reverse("firmante_crear", args=[organizacion.pk])
            if gestionar and not contexto.get("sin_alta")
            else None
        ),
        "rows": [
            {
                "id": firmante.pk,
                "name": firmante.nombre,
                "role": firmante.rol.nombre if firmante.rol else None,
                "cuit": str(firmante.cuit) if firmante.cuit else "-",
                "program": firmante.programa.nombre if firmante.programa else None,
                "edit_url": reverse("firmante_editar", args=[firmante.pk]),
                "delete_url": reverse("firmante_eliminar", args=[firmante.pk]),
            }
            for firmante in contexto.get("firmantes") or []
        ],
    }


@seccion_en_linea("avales")
def seccion_avales(contexto):
    """The inline "Avales" table of the legajo (only "Asociación de hecho")."""
    organizacion = contexto["organizacion"]
    gestionar = bool(contexto.get("puede_gestionar_organizaciones"))
    return {
        "kind": "avales",
        "can_manage": gestionar,
        "add_url": reverse("aval_crear", args=[organizacion.pk]) if gestionar else None,
        "rows": [
            {
                "id": aval.pk,
                "name": aval.nombre or "-",
                "cuit": str(aval.cuit) if aval.cuit else "-",
                "edit_url": reverse("aval_editar", args=[aval.pk]),
                "delete_url": reverse("aval_eliminar", args=[aval.pk]),
            }
            for aval in contexto.get("avales_data") or []
        ],
    }


def _formulario(form, titulo, organizacion_pk, otro):
    return {
        "title": titulo,
        "organization_id": organizacion_pk,
        "allow_another": otro,
        "fields": [_campo(form[nombre]) for nombre in form.fields],
        "non_field_errors": [str(e) for e in form.non_field_errors()],
    }


class _FirmanteAvalView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, OrganizacionAbmAccess]
    renderer_classes = [JSONRenderer]
    # ``as_view`` replaces these with the native views of the entity and its card title.
    crear = FirmanteCreateView
    actualizar = FirmanteUpdateView
    eliminar = FirmanteDeleteView
    titulo = "Datos de Firmantes"

    @staticmethod
    def _django(request):
        return request._request  # pylint: disable=protected-access

    @staticmethod
    def _errores(form):
        return {
            nombre: [str(e) for e in errores]
            for nombre, errores in form.errors.items()
            if nombre != "__all__"
        }


class FormularioWebView(_FirmanteAvalView):
    """``GET .../<id>/firmantes|avales/formulario/`` and ``.../firmantes|avales/<pk>/formulario/``."""

    http_method_names = ["get", "head"]

    def get(self, request, pk, alta):
        django_request = self._django(request)
        if alta:
            vista = self.crear()
            vista.setup(django_request, organizacion_pk=pk)
            vista.object = None
            contexto = vista.get_context_data()
            otro = True
            retorno = contexto["back_button"]["url"]
        else:
            vista = self.actualizar()
            vista.setup(django_request, pk=pk)
            vista.object = vista.get_object()
            contexto = vista.get_context_data()
            otro = False
            retorno = None
        return Response(
            {
                **_formulario(
                    contexto["form"], self.titulo, pk if otro else None, otro
                ),
                "urls": {"back": retorno},
                "messages": _pending_messages(django_request),
            }
        )


class GuardarWebView(_FirmanteAvalView):
    """``POST .../<id>/firmantes|avales/`` (201) and ``.../firmantes|avales/<pk>/`` (200)."""

    http_method_names = ["post"]

    def post(self, request, pk, alta):
        django_request = self._django(request)
        if alta:
            vista = self.crear()
            vista.setup(django_request, organizacion_pk=pk)
        else:
            vista = self.actualizar()
            vista.setup(django_request, pk=pk)
        respuesta = vista.post(django_request)
        if isinstance(respuesta, HttpResponseRedirect):
            return Response(
                {
                    "redirect": respuesta.url,
                    "otro": "guardar_otro" in django_request.POST,
                    "messages": _pending_messages(django_request),
                },
                status=status.HTTP_201_CREATED if alta else status.HTTP_200_OK,
            )
        form = respuesta.context_data["form"]
        return Response(
            {
                "errors": self._errores(form),
                "form": _formulario(form, self.titulo, pk if alta else None, alta),
                "messages": _pending_messages(django_request),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )


class BajaWebView(_FirmanteAvalView):
    """``GET/POST .../firmantes|avales/<pk>/baja/``: the native delete view."""

    http_method_names = ["get", "head", "post"]

    def _baja(self, request, pk):
        vista = self.eliminar()
        vista.setup(self._django(request), pk=pk)
        vista.object = vista.get_object()
        return vista

    def get(self, request, pk):
        vista = self._baja(request, pk)
        contexto = vista.get_context_data()
        return Response(
            {
                "id": vista.object.pk,
                "title": "Atención!",
                "message": contexto["delete_message"],
                "cascade_preview": contexto.get("cascade_preview"),
                "urls": {"cancel": contexto["cancel_url"]},
                "messages": _pending_messages(self._django(request)),
            }
        )

    def post(self, request, pk):
        django_request = self._django(request)
        respuesta = self._baja(request, pk).post(django_request)
        return Response(
            {
                "redirect": respuesta.url,
                "messages": _pending_messages(django_request),
            }
        )


def vistas(entidad):
    """The three API views of ``entidad`` (``"firmante"`` or ``"aval"``)."""
    nativas = {
        "firmante": (
            FirmanteCreateView,
            FirmanteUpdateView,
            FirmanteDeleteView,
            "Datos de Firmantes",
        ),
        "aval": (AvalCreateView, AvalUpdateView, AvalDeleteView, "Datos de Avales"),
    }[entidad]
    config = dict(zip(("crear", "actualizar", "eliminar", "titulo"), nativas))
    return (
        FormularioWebView.as_view(**config),
        GuardarWebView.as_view(**config),
        BajaWebView.as_view(**config),
    )
