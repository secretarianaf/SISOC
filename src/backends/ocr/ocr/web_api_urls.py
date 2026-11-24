"""Routes of ``/api/web/ocr/`` (G1 v1): see ``ocr.web_api_views``."""

from django.urls import path

from ocr.web_api_views import (
    OcrLoteCrearWebView,
    OcrLoteDetailWebView,
    OcrUploadWebView,
)

urlpatterns = [
    path("carga/", OcrUploadWebView.as_view(), name="ocr_web_carga"),
    path("lotes/", OcrLoteCrearWebView.as_view(), name="ocr_web_lote_crear"),
    path("lotes/<int:pk>/", OcrLoteDetailWebView.as_view(), name="ocr_web_lote"),
]
