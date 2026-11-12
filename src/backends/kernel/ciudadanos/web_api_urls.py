"""Rutas de ``/api/web/ciudadanos/`` (G1 v1): ficha Ciudadano 360 y su acción en el core."""

from django.urls import path

from ciudadanos.web_api import CiudadanoFichaWebView, CiudadanoMarcarRevisadoWebView

urlpatterns = [
    path("<int:pk>/", CiudadanoFichaWebView.as_view(), name="ciudadanos_web_ficha"),
    path(
        "<int:pk>/marcar-revisado/",
        CiudadanoMarcarRevisadoWebView.as_view(),
        name="ciudadanos_web_marcar_revisado",
    ),
]
