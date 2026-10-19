"""Agregado global de Comedores: se calcula y autoriza junto a su dominio."""

from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from comedores.api import obtener_metricas_dashboard
from core.internal_services import RespuestaInterna, registrar_servicio_interno
from relevamientos.api import contar_relevamientos

METRICS_PATH = "/api/comedores/metricas-dashboard/"


def metricas_dashboard(request, _data=None):
    if not request.user.is_authenticated:
        return RespuestaInterna(401, {"detail": "Autenticación requerida."})
    if not request.user.has_perm("dashboard.view_dashboard"):
        return RespuestaInterna(
            403, {"detail": "No tiene permiso para ver el dashboard."}
        )
    metrics = obtener_metricas_dashboard()
    # Dashboard.cantidad ya es BigInteger: conservar el truncado actual, sin
    # cambiar unidades ni convertir un agregado territorial en uno global.
    return RespuestaInterna(
        200,
        {
            "cantidad_comedores_activos": metrics.cantidad_espacios,
            "cantidad_relevamientos_activos": contar_relevamientos(),
            "presupuesto_desayuno": int(metrics.presupuesto_desayuno),
            "presupuesto_merienda": int(metrics.presupuesto_merienda),
            "presupuesto_comida": int(metrics.presupuesto_comida),
        },
    )


def registrar_metricas_dashboard():
    registrar_servicio_interno(METRICS_PATH, metricas_dashboard)


class MetricasDashboardView(APIView):
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        result = metricas_dashboard(request)
        return Response(result.data, status=result.status)
