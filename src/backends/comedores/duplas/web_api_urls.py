"""Rutas de ``/api/web/comedores/duplas/`` (G1 v1): ver ``duplas.web_api``."""

from django.urls import path

from duplas.web_api import DuplaDetailWebView, DuplaListWebView

urlpatterns = [
    path("", DuplaListWebView.as_view(), name="dupla_web_list"),
    path("<int:pk>/", DuplaDetailWebView.as_view(), name="dupla_web_detalle"),
]
