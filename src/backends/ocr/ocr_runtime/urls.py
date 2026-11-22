"""Rutas historicas de OCR; admin real solamente en su runtime."""

from django.contrib import admin
from django.urls import include, path

from config.backend_urls import urlpatterns_de_backend
from core.react_activation import react_preview_patterns

backend_urlpatterns = [
    # Entradas React de las pantallas migradas, solo con el flag activo.
    # Antes de las nativas: el GET llega a la entrada; el resto, a la nativa.
    *react_preview_patterns("ocr"),
    path("ocr/", include("ocr.urls")),
    # API web de las pantallas React (G1 v1, ocr.web_api_urls).
    path("api/web/ocr/", include("ocr.web_api_urls")),
]

urlpatterns = urlpatterns_de_backend(
    [path("admin/", admin.site.urls), *backend_urlpatterns]
)
