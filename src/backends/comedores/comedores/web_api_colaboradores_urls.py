"""Rutas de ``/api/web/comedores/colaboradores/`` (G1 v1): ver ``comedores.web_api_colaboradores``."""

from django.urls import path

from comedores.web_api_colaboradores import (
    ColaboradorBajaWebView,
    ColaboradorCrearWebView,
    ColaboradorEditarWebView,
)

urlpatterns = [
    path(
        "comedor/<int:pk>/crear/",
        ColaboradorCrearWebView.as_view(),
        name="colaboradores_web_crear",
    ),
    path(
        "comedor/<int:pk>/<int:pk2>/editar/",
        ColaboradorEditarWebView.as_view(),
        name="colaboradores_web_editar",
    ),
    path(
        "comedor/<int:pk>/<int:pk2>/eliminar/",
        ColaboradorBajaWebView.as_view(),
        name="colaboradores_web_eliminar",
    ),
]
