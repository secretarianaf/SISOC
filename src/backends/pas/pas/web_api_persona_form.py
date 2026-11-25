"""Web API (G1 v1) of the PAS titular form: create and edit (PAS06.02).

Same forms and services as ``PasPersonaCreateView`` and ``PasPersonaUpdateView``
(``PasPersonaCreateForm`` + ``registrar_persona``; ``PasPersonaUpdateForm``),
under the native rules ``permissions_any_required(["pas.add_paspersona"])`` and
``["pas.change_paspersona"]`` evaluated after G1. The options come from the
form's own querysets, so they match what the server validates. The native
success message travels in the body: the screen shows it on the panel it
navigates to. A POST is never retried.
"""

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils.cache import patch_vary_headers
from rest_framework.authentication import SessionAuthentication
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from core.web_gate import WebGatePermission
from pas.forms import PasPersonaCreateForm, PasPersonaUpdateForm
from pas.models import PasPersona
from pas.services.persona_service import registrar_persona
from pas.views import _avisos_por_estado
from pas.web_api_views import CHANGE, native_rule

ADD = "pas.add_paspersona"
CREADO = "Registro PAS creado correctamente."
ACTUALIZADO = "Registro PAS actualizado correctamente."
TEXTOS = (
    "id_persona",
    "apellidos",
    "nombres",
    "dni",
    "cuit",
    "genero",
    "domicilio",
    "correo_electronico",
    "telefono_celular",
)


def _private(response):
    response["Cache-Control"] = "private, no-store"
    patch_vary_headers(response, ("Cookie",))
    return response


def _choices(queryset):
    return [{"value": str(item.pk), "label": str(item)} for item in queryset]


def _options(form):
    return {
        "provincias": _choices(form.fields["provincia"].queryset),
        "municipios": _choices(form.fields["municipio"].queryset),
        "estados": (
            _choices(form.fields["estado"].queryset) if "estado" in form.fields else []
        ),
        "avisos_por_estado": _avisos_por_estado() if "estado" in form.fields else {},
        "generos": [
            {"value": value, "label": label}
            for value, label in PasPersona._meta.get_field("genero").choices
        ],
    }


def _errors(form):
    return {"errors": form.errors.get_json_data()}


class PasPersonaFormWebView(APIView):
    authentication_classes = [SessionAuthentication]
    renderer_classes = [JSONRenderer]
    parser_classes = [FormParser, MultiPartParser]


class PasPersonaOpcionesWebView(PasPersonaFormWebView):
    """``GET .../personas/opciones/?provincia=<id>``: options of the form (add or change)."""

    permission_classes = [WebGatePermission, native_rule([ADD, CHANGE])]
    http_method_names = ["get", "head"]

    def get(self, request):
        provincia = request.query_params.get("provincia", "")
        # The bound form is how the native form picks the municipios of a province.
        form = PasPersonaCreateForm({"provincia": provincia})
        return _private(Response(_options(form)))


class PasPersonaCrearWebView(PasPersonaFormWebView):
    """``POST .../personas/crear/``: ``PasPersonaCreateForm`` + ``registrar_persona``."""

    permission_classes = [WebGatePermission, native_rule([ADD])]
    http_method_names = ["post"]

    def post(self, request):
        form = PasPersonaCreateForm(request.POST)
        if not form.is_valid():
            return _private(Response(_errors(form), status=400))
        with transaction.atomic():
            persona = registrar_persona(form, usuario=request.user)
        return _private(Response({"id": persona.pk, "message": CREADO}, status=201))


class PasPersonaEditarWebView(PasPersonaFormWebView):
    """``GET .../personas/<pk>/`` initial data and options; ``POST .../editar/`` saves."""

    permission_classes = [WebGatePermission, native_rule([CHANGE])]
    http_method_names = ["get", "head", "post"]

    def get(self, request, pk):
        persona = get_object_or_404(PasPersona, pk=pk)
        form = PasPersonaUpdateForm(instance=persona)
        initial = {name: str(form.initial.get(name) or "") for name in TEXTOS}
        initial["provincia"] = str(persona.provincia_id or "")
        initial["municipio"] = str(persona.municipio_id or "")
        return _private(
            Response({"id": persona.pk, "initial": initial, **_options(form)})
        )

    def post(self, request, pk):
        persona = get_object_or_404(PasPersona, pk=pk)
        form = PasPersonaUpdateForm(request.POST, instance=persona)
        if not form.is_valid():
            return _private(Response(_errors(form), status=400))
        form.save()
        return _private(Response({"id": persona.pk, "message": ACTUALIZADO}))
