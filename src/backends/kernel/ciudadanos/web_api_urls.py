"""Rutas de ``/api/web/ciudadanos/`` (G1 v1): ficha Ciudadano 360 y su acción en el core."""

from django.urls import path

from ciudadanos.web_api import CiudadanoFichaWebView, CiudadanoMarcarRevisadoWebView
from ciudadanos.web_baja import CiudadanoBajaWebView
from ciudadanos.web_familiar import CiudadanoFamiliarNuevoWebView

urlpatterns = [
    path("<int:pk>/", CiudadanoFichaWebView.as_view(), name="ciudadanos_web_ficha"),
    path("<int:pk>/baja/", CiudadanoBajaWebView.as_view(), name="ciudadanos_web_baja"),
    path(
        "<int:pk>/familiares/nuevo/",
        CiudadanoFamiliarNuevoWebView.as_view(),
        name="ciudadanos_web_familiar_nuevo",
    ),
    path(
        "<int:pk>/marcar-revisado/",
        CiudadanoMarcarRevisadoWebView.as_view(),
        name="ciudadanos_web_marcar_revisado",
    ),
]
