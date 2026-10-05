"""Métricas de Centro de Familia para el dashboard del core.

El dashboard corre en el core y Centro de Familia en su propio backend: el core
pide estas métricas con la sesión del usuario (core.backend_proxy).
"""

from dataclasses import asdict

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from centrodefamilia.api import obtener_metricas_dashboard


@login_required
def metricas_dashboard(request):
    del request
    return JsonResponse(asdict(obtener_metricas_dashboard()))
