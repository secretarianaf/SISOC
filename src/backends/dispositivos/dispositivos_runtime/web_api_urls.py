"""API web del backend Dispositivos (``/api/web/dispositivos/``, G1 v1): rutas de cada app del backend."""

from django.urls import include, path

urlpatterns = [
    path("", include("dispositivos.web_api_urls")),
]
