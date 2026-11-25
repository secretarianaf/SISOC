"""Rutas de ``/api/web/comedores/comedores/`` (G1 v1) de la nómina: ver ``comedores.web_api_nomina``."""

from django.urls import path

from comedores.web_api_nomina_acciones import (
    nomina_cambiar_estado_web,
    nomina_derivar_web,
)
from comedores.web_api_nomina import NominaAdmisionWebView, NominaDirectaWebView
from comedores.web_api_nomina_baja import (
    NominaBajaAdmisionWebView,
    NominaBajaDirectaWebView,
)

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
        "comedores/<int:pk>/admision/<int:admision_pk>/nomina/<int:pk2>/eliminar/",
        NominaBajaAdmisionWebView.as_view(),
        name="comedores_web_nomina_baja_admision",
    ),
    path(
        "comedores/<int:pk>/nomina/<int:pk2>/eliminar/",
        NominaBajaDirectaWebView.as_view(),
        name="comedores_web_nomina_baja_directa",
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
