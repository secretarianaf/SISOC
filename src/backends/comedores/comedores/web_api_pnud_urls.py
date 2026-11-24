"""Rutas de ``/api/web/comedores/actividades-pnud/`` (G1 v1): ver ``comedores.web_api_pnud``."""

from django.urls import path

from comedores.web_api_pnud import (
    ActividadCreateWebView,
    ActividadDeactivateWebView,
    ActividadesListWebView,
    ActividadUpdateWebView,
)

urlpatterns = [
    path(
        "actividades-pnud/",
        ActividadesListWebView.as_view(),
        name="comedores_web_actividades_pnud",
    ),
    path(
        "actividades-pnud/crear/",
        ActividadCreateWebView.as_view(),
        name="comedores_web_actividades_pnud_crear",
    ),
    path(
        "actividades-pnud/<int:pk>/editar/",
        ActividadUpdateWebView.as_view(),
        name="comedores_web_actividades_pnud_editar",
    ),
    path(
        "actividades-pnud/<int:pk>/baja/",
        ActividadDeactivateWebView.as_view(),
        name="comedores_web_actividades_pnud_baja",
    ),
]
