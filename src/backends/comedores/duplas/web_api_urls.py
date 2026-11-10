"""Rutas de ``/api/web/comedores/duplas/`` (G1 v1): ver ``duplas.web_api``."""

from django.urls import path

from duplas.web_api import (
    DuplaCreateWebView,
    DuplaDeleteWebView,
    DuplaDetailWebView,
    DuplaListWebView,
    DuplaUpdateWebView,
)

urlpatterns = [
    path("", DuplaListWebView.as_view(), name="dupla_web_list"),
    path("crear/", DuplaCreateWebView.as_view(), name="dupla_web_crear"),
    path("<int:pk>/", DuplaDetailWebView.as_view(), name="dupla_web_detalle"),
    path("<int:pk>/editar/", DuplaUpdateWebView.as_view(), name="dupla_web_editar"),
    path(
        "<int:pk>/eliminar/",
        DuplaDeleteWebView.as_view(),
        name="dupla_web_eliminar",
    ),
]
