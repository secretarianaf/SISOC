"""JSON transport for the public DDJJ form; the native form and service stay the authority.

Routes live under ``/pas/ddjj/formulario/<token>/`` (not ``/api/``) so the web
session middleware applies exactly as on the HTML form (P1, #2806).
"""

from django.http import JsonResponse
from django.urls import reverse
from django.utils.cache import patch_cache_control, patch_vary_headers
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from pas.forms import PasDeclaracionJuradaForm
from pas.services.ddjj_service import presentar_ddjj
from pas.views import PasDDJJFormularioView

NO_DISPONIBLE = "Este enlace ya fue utilizado o se encuentra vencido."
CAMPOS_TEXTO = (
    "calle",
    "altura",
    "provincia",
    "municipio",
    "correo_electronico",
    "telefono_celular",
)
CAMPOS_RESPUESTA = (
    "embarazada",
    "controles_embarazo_cumplidos",
    "hijos_menores_a_cargo",
    "vacunacion_cumplida",
    "regularidad_escolar_acreditada",
    "gastos_bajo_limite_smvm",
    "no_accedio_mercado_cambios",
)
CAMPOS_CON_ETIQUETA = (*CAMPOS_TEXTO, "embarazada", "acepto_declaracion")


def _opciones(field):
    return [
        {"id": str(objeto.pk), "label": field.label_from_instance(objeto)}
        for objeto in field.queryset
    ]


def _texto(valor):
    return "" if valor is None else str(valor)


def formulario_payload(form, invitacion):
    """Serialize what the native template renders from ``form``."""
    valores = {campo: _texto(form[campo].value()) for campo in CAMPOS_TEXTO}
    valores.update({campo: _texto(form[campo].value()) for campo in CAMPOS_RESPUESTA})
    valores["acepto_declaracion"] = bool(form["acepto_declaracion"].value())
    return {
        "values": valores,
        "existing": dict(form.campos_datos_existentes),
        "labels": {
            campo: str(form.fields[campo].label) for campo in CAMPOS_CON_ETIQUETA
        },
        "empty_label": str(form.fields["provincia"].empty_label),
        "provinces": _opciones(form.fields["provincia"]),
        "municipalities": _opciones(form.fields["municipio"]),
        "urls": {
            "municipalities": reverse(
                "pas_ddjj_municipios", kwargs={"token": invitacion.token}
            ),
            "submit": reverse(
                "pas_ddjj_formulario_enviar", kwargs={"token": invitacion.token}
            ),
            "confirmation": reverse("pas_ddjj_confirmacion"),
        },
    }


def _privada(response):
    patch_cache_control(response, private=True, no_store=True)
    patch_vary_headers(response, ("Cookie",))
    return response


def _no_disponible():
    return _privada(JsonResponse({"detail": NO_DISPONIBLE}, status=410))


@method_decorator(ensure_csrf_cookie, name="dispatch")
class PasDDJJFormularioDatosView(PasDDJJFormularioView):
    """Initial form data for an available invitation; same 404/410 as the HTML form."""

    http_method_names = ["get", "head"]

    def get(self, request, token):
        invitacion = self._invitacion(token)
        if not invitacion.disponible:
            return _no_disponible()
        form = PasDeclaracionJuradaForm(persona=invitacion.persona)
        return _privada(JsonResponse(formulario_payload(form, invitacion)))


class PasDDJJFormularioEnvioView(PasDDJJFormularioView):
    """URL-encoded submission validated by the native form and saved by ``presentar_ddjj``."""

    http_method_names = ["post"]

    def post(self, request, token):
        invitacion = self._invitacion(token)
        if not invitacion.disponible:
            return _no_disponible()
        form = PasDeclaracionJuradaForm(request.POST, persona=invitacion.persona)
        if not form.is_valid():
            payload = formulario_payload(form, invitacion)
            payload["errors"] = {
                campo: [error["message"] for error in errores]
                for campo, errores in form.errors.get_json_data().items()
            }
            return _privada(JsonResponse(payload, status=400))
        try:
            presentar_ddjj(invitacion, form)
        except ValueError:
            return _no_disponible()
        return _privada(JsonResponse({"redirect": reverse("pas_ddjj_confirmacion")}))
