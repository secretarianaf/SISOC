"""Rutas de ``/api/web/cdi/`` de Centro de Infancia (G1 v1).

Ver ``centrodeinfancia.web_api`` (reportes),
``centrodeinfancia.web_api_observaciones`` (observaciones),
``centrodeinfancia.web_api_centros`` (listado de centros) y
``centrodeinfancia.web_api_nomina`` (ficha de un destinatario de la nómina).
"""

from django.urls import path

from centrodeinfancia.web_api import ReportesWebView
from centrodeinfancia.web_api_centros import CentrosListWebView
from centrodeinfancia.web_api_nomina import NominaDestinatarioWebView
from centrodeinfancia.web_api_observaciones import (
    ObservacionCrearWebView,
    ObservacionDetalleWebView,
    ObservacionEditarWebView,
    ObservacionEliminarWebView,
)

urlpatterns = [
    path("reportes/", ReportesWebView.as_view(), name="centrodeinfancia_web_reportes"),
    path("centros/", CentrosListWebView.as_view(), name="centrodeinfancia_web_centros"),
    path(
        "centros/<int:pk>/nomina/<int:nomina_id>/",
        NominaDestinatarioWebView.as_view(),
        name="centrodeinfancia_web_nomina_destinatario",
    ),
    path(
        "centros/<int:pk>/observaciones/crear/",
        ObservacionCrearWebView.as_view(),
        name="centrodeinfancia_web_observacion_crear",
    ),
    path(
        "observaciones/<int:pk>/",
        ObservacionDetalleWebView.as_view(),
        name="centrodeinfancia_web_observacion_detalle",
    ),
    path(
        "observaciones/<int:pk>/editar/",
        ObservacionEditarWebView.as_view(),
        name="centrodeinfancia_web_observacion_editar",
    ),
    path(
        "observaciones/<int:pk>/eliminar/",
        ObservacionEliminarWebView.as_view(),
        name="centrodeinfancia_web_observacion_eliminar",
    ),
]
