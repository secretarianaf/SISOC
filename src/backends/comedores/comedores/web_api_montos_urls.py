"""Rutas de ``/api/web/comedores/montos/`` (G1 v1): ver ``comedores.web_api_montos``."""

from django.urls import path

from comedores.web_api_montos import (
    MontoCreateWebView,
    MontoDeleteWebView,
    MontoDetailWebView,
    MontosListWebView,
    MontoUpdateWebView,
)

urlpatterns = [
    path("montos/", MontosListWebView.as_view(), name="comedores_web_montos"),
    path(
        "montos/crear/",
        MontoCreateWebView.as_view(),
        name="comedores_web_montos_crear",
    ),
    path(
        "montos/<int:pk>/",
        MontoDetailWebView.as_view(),
        name="comedores_web_montos_detalle",
    ),
    path(
        "montos/<int:pk>/editar/",
        MontoUpdateWebView.as_view(),
        name="comedores_web_montos_editar",
    ),
    path(
        "montos/<int:pk>/eliminar/",
        MontoDeleteWebView.as_view(),
        name="comedores_web_montos_eliminar",
    ),
]
