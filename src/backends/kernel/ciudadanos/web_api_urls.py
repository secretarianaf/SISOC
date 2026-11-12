"""Rutas de ``/api/web/ciudadanos/`` (G1 v1): ficha Ciudadano 360 en el core."""

from django.urls import path

from ciudadanos.web_api import CiudadanoFichaWebView

urlpatterns = [
    path("<int:pk>/", CiudadanoFichaWebView.as_view(), name="ciudadanos_web_ficha"),
]
