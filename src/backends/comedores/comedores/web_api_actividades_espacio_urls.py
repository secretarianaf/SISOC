"""Rutas de ``/api/web/comedores/actividades-espacio/`` (G1 v1): ver ``comedores.web_api_actividades_espacio``."""

from django.urls import path

from comedores.web_api_actividades_espacio import (
    ActividadCrearWebView,
    ActividadEditarWebView,
)

urlpatterns = [
    path(
        "comedor/<int:pk>/crear/",
        ActividadCrearWebView.as_view(),
        name="actividades_espacio_web_crear",
    ),
    path(
        "comedor/<int:pk>/<int:pk2>/editar/",
        ActividadEditarWebView.as_view(),
        name="actividades_espacio_web_editar",
    ),
]
