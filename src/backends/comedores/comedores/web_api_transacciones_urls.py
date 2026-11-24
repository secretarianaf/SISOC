"""Rutas de ``/api/web/comedores/comedores/`` (G1 v1) de las transacciones DW: ver ``comedores.web_api_transacciones``."""

from django.urls import path

from comedores.web_api_transacciones import ComedorTransaccionesWebView

urlpatterns = [
    path(
        "comedores/<int:pk>/transacciones/",
        ComedorTransaccionesWebView.as_view(),
        name="comedores_web_transacciones",
    ),
]
