"""Novedades del sistema para React (T02.01, G1 v1): ``/api/web/core/novedades/``.

Proyecta el mismo contexto que ``changelog_view``: el parseo del ``CHANGELOG.md`` y el
caché de 24 horas siguen en el backend (``core.views``); React recibe el HTML ya
convertido y no lo vuelve a analizar.
"""

import logging

from django.core.cache import cache
from django.urls import reverse
from rest_framework.response import Response

from core.views import (
    fetch_changelog_content,
    get_current_version,
    parse_changelog_versions,
)
from core.web_api_core_base import CoreWebView, pending_messages

logger = logging.getLogger(__name__)

CACHE_KEY = "changelog_content"
CACHE_TIMEOUT = 86400


def _contenido():
    """Misma secuencia que ``changelog_view``: caché, archivo/GitHub y no cachear lo vacío."""
    cacheado = cache.get(CACHE_KEY)
    if cacheado and cacheado.get("versions"):
        return cacheado["versions"], cacheado["version"]
    contenido = fetch_changelog_content()
    if not contenido:
        return None, get_current_version()
    versions = parse_changelog_versions(contenido)
    version = get_current_version()
    if versions:
        cache.set(CACHE_KEY, {"versions": versions, "version": version}, CACHE_TIMEOUT)
    else:
        logger.warning("Se leyó CHANGELOG.md pero no se detectaron bloques de versión.")
    return versions, version


class NovedadesWebView(CoreWebView):
    """``changelog_view`` (cualquier usuario autenticado)."""

    def get(self, request):
        versions, current_version = _contenido()
        return Response(
            {
                "current_version": current_version,
                "versions": [
                    {"version": item["version"], "html": item["html"]}
                    for item in versions or []
                ],
                "error": not versions,
                "urls": {
                    "architecture": reverse("mapa_arquitectura"),
                    "home": reverse("inicio"),
                },
                "messages": pending_messages(request),
            }
        )
