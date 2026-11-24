"""Rutas de ``/api/web/comedores/comedores/`` (G1 v1) de la nómina: ver ``comedores.web_api_nomina``."""

from django.urls import path

from comedores.web_api_nomina_acciones import (
    nomina_cambiar_estado_web,
    nomina_derivar_web,
)
from comedores.web_api_nomina import NominaAdmisionWebView, NominaDirectaWebView

urlpatterns = [
    path(
        "comedores/<int:pk>/admision/<int:admision_pk>/nomina/",
        NominaAdmisionWebView.as_view(),
        name="comedores_web_nomina_admision",
    ),
    path(
        "comedores/<int:pk>/nomina/",
        NominaDirectaWebView.as_view(),
        name="comedores_web_nomina_directa",
    ),
    path(
        "comedores/nomina/<int:pk>/cambiar-estado/",
        nomina_cambiar_estado_web,
        name="comedores_web_nomina_cambiar_estado",
    ),
    path(
        "comedores/nomina/<int:pk>/derivar/",
        nomina_derivar_web,
        name="comedores_web_nomina_derivar",
    ),
]
