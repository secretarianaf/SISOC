"""Rutas de ``/api/web/comedores/comunicados/`` (G1 v1): ver ``comunicados.web_api_views``."""

from django.urls import path

from comunicados.web_api_views import ComunicadoDetailWebView, ComunicadoListWebView

urlpatterns = [
    path("", ComunicadoListWebView.as_view(), name="comunicados_web_listado"),
    path(
        "<int:pk>/", ComunicadoDetailWebView.as_view(), name="comunicados_web_detalle"
    ),
]
