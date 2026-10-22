"""Rutas historicas de OCR; admin real solamente en su runtime."""

from django.contrib import admin
from django.urls import include, path

from config.backend_urls import urlpatterns_de_backend

backend_urlpatterns = [path("ocr/", include("ocr.urls"))]

urlpatterns = urlpatterns_de_backend(
    [path("admin/", admin.site.urls), *backend_urlpatterns]
)
