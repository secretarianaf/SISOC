"""Web API (G1 v1) of the PAS crossings (PAS03): ``/api/web/pas/cruces/``.

Same access as the native routes of ``pas/urls.py``: G1 first
(``WebGatePermission``), then the native ``permissions_any_required`` rule,
evaluated with the same ``iam`` function. The read runs ``PasCrucesView`` and
projects its context (PAS03.02); the three actions (PAS03.01) call the same
services as the native views. Nothing here reaches SINTyS or RENAPER: the
export builds the file locally, the import stores the uploaded file without
reading it and the RENAPER update only registers the monthly run.
"""

from django.utils.cache import patch_vary_headers
from django.utils.dateformat import format as format_date
from rest_framework.authentication import SessionAuthentication
from rest_framework.parsers import MultiPartParser
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from core.web_gate import WebGatePermission
from iam.services import user_has_permission_code
from pas import web_api_serializers as proyectar
from pas.forms import PasRetornoSintysForm
from pas.services.cruces_service import (
    obtener_circuito_actual,
    registrar_importacion_sintys,
)
from pas.services.supervivencia_jobs import request_run
from pas.views import PasCrucesExportarSintysView, PasCrucesView
from pas.web_api_views import CHANGE, VIEW, native_rule

IMPORTADO = "Retorno SINTyS importado correctamente."
IMPORT_ERROR = "No se pudo importar el retorno: "


def _private(response):
    response["Cache-Control"] = "private, no-store"
    patch_vary_headers(response, ("Cookie",))
    return response


def _incompatibilidad(item):
    return {
        "titular": f"{item.persona.apellidos}, {item.persona.nombres}",
        "dni": item.persona.dni,
        "categoria": item.get_categoria_display(),
        "detalle": item.detalle,
        "fecha_deteccion": proyectar.fecha_hora(item.fecha_deteccion),
        "periodo_impacto": format_date(item.periodo_impacto, "m/Y"),
        "estado": item.get_estado_display(),
    }


def _etapa(etapa):
    return {
        "numero": etapa["numero"],
        "nombre": etapa["nombre"],
        "fecha": proyectar.fecha_iso(etapa["fecha"]) or None,
        "fecha_texto": proyectar.fecha_hora(etapa["fecha"]),
        "completada": etapa["completada"],
        "integracion_pendiente": etapa["integracion_pendiente"],
    }


class PasCrucesWebView(APIView):
    """``GET /api/web/pas/cruces/``: the data of ``pas/cruces`` (PAS03.02).

    ``corrida`` is in the native context but the template never prints it, so
    it is not part of the payload. The read creates nothing: without a circuit
    for the month ``circuito.existe`` is false.
    """

    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, native_rule([VIEW])]
    renderer_classes = [JSONRenderer]
    http_method_names = ["get", "head"]

    def get(self, request):
        vista = PasCrucesView()
        vista.setup(request._request)  # pylint: disable=protected-access
        context = vista.get_context_data()
        circuito = context["circuito"]
        renaper = context["resumen_renaper"]
        return Response(
            {
                "can_change": user_has_permission_code(request.user, CHANGE),
                "total_padron": context["total_padron"],
                "circuito": {
                    "periodo": circuito.periodo.isoformat(),
                    "periodo_texto": format_date(circuito.periodo, "m/Y"),
                    "existe": circuito.pk is not None,
                },
                "etapas": [_etapa(etapa) for etapa in context["etapas_circuito"]],
                "renaper": {
                    "fecha": proyectar.fecha(renaper["fecha"]) or None,
                    "total": renaper["total"],
                    "fallecidas": renaper["fallecidas"],
                    "errores": renaper["errores"],
                },
                "incompatibilidades": [
                    _incompatibilidad(item) for item in context["incompatibilidades"]
                ],
                "areas": proyectar.workflow(context["pas_areas"]),
            }
        )


class PasCrucesAccionWebView(APIView):
    """Base of the actions: the native rule of the three POST routes."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, native_rule([CHANGE])]
    renderer_classes = [JSONRenderer]
    http_method_names = ["post"]


class PasCrucesExportarSintysWebView(PasCrucesAccionWebView):
    """``POST .../cruces/exportar-sintys/``: creates the record and answers the XLSX.

    The native view does both in one response, so the API runs that view's own
    ``post`` and returns its file.
    """

    def post(self, request):
        django_request = request._request  # pylint: disable=protected-access
        vista = PasCrucesExportarSintysView()
        vista.setup(django_request)
        return _private(vista.post(django_request))


class PasCrucesImportarSintysWebView(PasCrucesAccionWebView):
    """``POST .../cruces/importar-sintys/`` (multipart ``archivo``): stores the return file."""

    parser_classes = [MultiPartParser]

    def post(self, request):
        form = PasRetornoSintysForm(request.POST, request.FILES)
        if not form.is_valid():
            errores = {campo: list(items) for campo, items in form.errors.items()}
            mensaje = IMPORT_ERROR + " ".join(
                error for items in errores.values() for error in items
            )
            return Response({"message": mensaje, "errors": errores}, status=400)
        registrar_importacion_sintys(
            obtener_circuito_actual(crear=True),
            form.cleaned_data["archivo"],
            request.user,
        )
        return Response({"message": IMPORTADO})


class PasCrucesActualizarRenaperWebView(PasCrucesAccionWebView):
    """``POST .../cruces/actualizar-renaper/``: registers the monthly run (idempotent)."""

    def post(self, request):
        run = request_run(actor=request.user)
        return Response(
            {
                "run_id": run.pk,
                "message": (
                    f"Control mensual #{run.pk} registrado. "
                    "Consulte el avance en esta pantalla."
                ),
            }
        )
