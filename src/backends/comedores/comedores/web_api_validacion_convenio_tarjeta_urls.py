"""Rutas de ``/api/web/comedores/comedores/`` (G1 v1): validación, convenio y tarjeta (CO07.03)."""

from django.urls import path

from comedores.web_api_convenio import ComedorConvenioWebView
from comedores.web_api_tarjeta import ComedorTarjetaWebView
from comedores.web_api_validacion import (
    ComedorValidacionWebView,
    ComedorValidarWebView,
)

urlpatterns = [
    path(
        "comedores/<int:pk>/validacion/",
        ComedorValidacionWebView.as_view(),
        name="comedores_web_validacion",
    ),
    path(
        "comedores/<int:pk>/validar/",
        ComedorValidarWebView.as_view(),
        name="comedores_web_validar",
    ),
    path(
        "comedores/<int:pk>/convenio-pnud/",
        ComedorConvenioWebView.as_view(),
        name="comedores_web_convenio_pnud",
    ),
    path(
        "comedores/<int:pk>/responsable-tarjeta/",
        ComedorTarjetaWebView.as_view(),
        name="comedores_web_responsable_tarjeta",
    ),
]
