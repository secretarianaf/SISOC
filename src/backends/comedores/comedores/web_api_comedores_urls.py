"""Rutas de ``/api/web/comedores/comedores/`` (G1 v1): ver ``comedores.web_api_comedores``."""

from django.urls import path

from comedores.web_api_comedores import ComedoresListWebView

urlpatterns = [
    path("comedores/", ComedoresListWebView.as_view(), name="comedores_web_listado"),
]
