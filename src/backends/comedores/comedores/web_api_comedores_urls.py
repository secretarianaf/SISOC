"""Rutas de ``/api/web/comedores/comedores/`` (G1 v1): ver ``comedores.web_api_comedores``."""

from django.urls import path

from comedores.web_api_comedor_form import (
    ComedorFormularioWebView,
    ComedorGuardarWebView,
)
from comedores.web_api_comedores import ComedorBajaWebView, ComedoresListWebView

urlpatterns = [
    path("comedores/", ComedoresListWebView.as_view(), name="comedores_web_listado"),
    path(
        "comedores/<int:pk>/baja/",
        ComedorBajaWebView.as_view(),
        name="comedores_web_baja",
    ),
    path(
        "comedores/formulario/",
        ComedorFormularioWebView.as_view(),
        name="comedores_web_formulario_crear",
    ),
    path(
        "comedores/<int:pk>/formulario/",
        ComedorFormularioWebView.as_view(),
        name="comedores_web_formulario_editar",
    ),
    path(
        "comedores/crear/",
        ComedorGuardarWebView.as_view(),
        name="comedores_web_crear",
    ),
    path(
        "comedores/<int:pk>/editar/",
        ComedorGuardarWebView.as_view(),
        name="comedores_web_editar",
    ),
]
