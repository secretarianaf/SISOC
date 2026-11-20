"""Rutas de ``/api/web/comedores/asignar-dupla/`` (G1 v1): ver ``comedores.web_api_dupla_asignar``."""

from django.urls import path

from comedores.web_api_dupla_asignar import AsignarDuplaWebView

urlpatterns = [
    path(
        "<int:pk>/",
        AsignarDuplaWebView.as_view(),
        name="comedores_web_dupla_asignar",
    ),
]
