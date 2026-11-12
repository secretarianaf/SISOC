"""Rutas historicas de OCR; admin real solamente en su runtime."""

from django.contrib import admin
from django.urls import include, path

from config.backend_urls import urlpatterns_de_backend

backend_urlpatterns = [
    path("ocr/", include("ocr.urls")),
    # API web de las pantallas React (G1 v1, ocr.web_api_urls).
    path("api/web/ocr/", include("ocr.web_api_urls")),
]

urlpatterns = urlpatterns_de_backend(
    [path("admin/", admin.site.urls), *backend_urlpatterns]
)
