"""Rutas de ``/api/web/comedores/nomina-crear/`` (G1 v1): ver ``comedores.web_api_nomina_crear``."""

from django.urls import path

from comedores.web_api_nomina_crear import (
    NominaCrearAdmisionWebView,
    NominaCrearDirectaWebView,
)

urlpatterns = [
    path(
        "<int:pk>/",
        NominaCrearDirectaWebView.as_view(),
        name="comedores_web_nomina_crear_directa",
    ),
    path(
        "<int:pk>/admision/<int:admision_pk>/",
        NominaCrearAdmisionWebView.as_view(),
        name="comedores_web_nomina_crear_admision",
    ),
]
