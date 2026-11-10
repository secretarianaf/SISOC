"""Rutas de ``/api/web/cdi/`` de Centro de Infancia (G1 v1): ver ``centrodeinfancia.web_api``."""

from django.urls import path

from centrodeinfancia.web_api import ReportesWebView

urlpatterns = [
    path("reportes/", ReportesWebView.as_view(), name="centrodeinfancia_web_reportes"),
]
