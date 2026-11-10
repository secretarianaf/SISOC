"""Rutas de ``/api/web/inspecciones/`` (G1 v1): ver ``inspecciones.web_api``."""

from django.urls import path

from inspecciones.web_api import ActasWebView, InspectoresWebView

urlpatterns = [
    path("actas/", ActasWebView.as_view(), name="inspecciones_web_actas"),
    path(
        "inspectores/",
        InspectoresWebView.as_view(),
        name="inspecciones_web_inspectores",
    ),
]
