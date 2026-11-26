"""Mapa de arquitectura para React (T03.01, G1 v1): ``/api/web/core/arquitectura/``.

Informa lo mismo que ``mapa_arquitectura_view``: si el grafo existe y cuándo se generó.
El grafo describe estructura interna: sigue entregándose solo por
``mapa_arquitectura_datos`` (sesión) y nunca se copia a un asset ni a esta respuesta.
"""

import logging
from datetime import datetime

from django.urls import reverse
from django.utils import timezone
from rest_framework.response import Response

from core.views import _ruta_grafo_arquitectura  # pylint: disable=protected-access
from core.web_api_core_base import CoreWebView

logger = logging.getLogger(__name__)


class ArquitecturaWebView(CoreWebView):
    """``mapa_arquitectura_view`` (cualquier usuario autenticado)."""

    def get(self, request):
        grafo = _ruta_grafo_arquitectura()
        disponible = False
        generado = None
        try:
            if grafo.is_file():
                generado = datetime.fromtimestamp(
                    grafo.stat().st_mtime, tz=timezone.get_current_timezone()
                ).strftime("%d/%m/%Y %H:%M")
                disponible = True
        except OSError as exc:
            logger.warning("No se pudo consultar el grafo de arquitectura: %s", exc)
        return Response(
            {
                "grafo_disponible": disponible,
                "generado": generado,
                "urls": {
                    "data": reverse("mapa_arquitectura_datos"),
                    "back": reverse("changelog"),
                },
            }
        )
