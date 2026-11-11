"""Rutas de ``/api/web/comedores/expedientespagos/`` (G1 v1): ver ``expedientespagos.web_api``."""

from django.urls import path

from expedientespagos.web_api import (
    ExpedienteCreateWebView,
    ExpedienteDeleteWebView,
    ExpedienteDetailWebView,
    ExpedientesListWebView,
    ExpedienteUpdateWebView,
)

urlpatterns = [
    path(
        "comedores/<int:comedor_id>/",
        ExpedientesListWebView.as_view(),
        name="expedientespagos_web_list",
    ),
    path(
        "comedores/<int:comedor_id>/crear/",
        ExpedienteCreateWebView.as_view(),
        name="expedientespagos_web_crear",
    ),
    path(
        "<int:pk>/",
        ExpedienteDetailWebView.as_view(),
        name="expedientespagos_web_detalle",
    ),
    path(
        "<int:pk>/editar/",
        ExpedienteUpdateWebView.as_view(),
        name="expedientespagos_web_editar",
    ),
    path(
        "<int:pk>/eliminar/",
        ExpedienteDeleteWebView.as_view(),
        name="expedientespagos_web_eliminar",
    ),
]
