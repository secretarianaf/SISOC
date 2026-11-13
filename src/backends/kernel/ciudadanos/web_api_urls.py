"""Rutas de ``/api/web/ciudadanos/`` (G1 v1): ficha Ciudadano 360 y su acción en el core."""

from django.urls import path

from ciudadanos.web_api import CiudadanoFichaWebView, CiudadanoMarcarRevisadoWebView
from ciudadanos.web_baja import CiudadanoBajaWebView
from ciudadanos.web_familiar import CiudadanoFamiliarNuevoWebView
from ciudadanos.web_api_importacion import (
    CiudadanoImportacionLoteWebView,
    CiudadanoImportacionReanudarWebView,
    CiudadanoImportacionWebView,
)
from ciudadanos.web_api_cola_revision import (
    CiudadanoColaRevisionWebView,
    CiudadanoDescartarRevisionWebView,
)
from ciudadanos.web_api_familiar_eliminar import GrupoFamiliarEliminarWebView
from ciudadanos.web_form import CiudadanoCrearWebView, CiudadanoEditarWebView

urlpatterns = [
    path("<int:pk>/", CiudadanoFichaWebView.as_view(), name="ciudadanos_web_ficha"),
    path("<int:pk>/baja/", CiudadanoBajaWebView.as_view(), name="ciudadanos_web_baja"),
    path("crear/", CiudadanoCrearWebView.as_view(), name="ciudadanos_web_crear"),
    path(
        "<int:pk>/editar/",
        CiudadanoEditarWebView.as_view(),
        name="ciudadanos_web_editar",
    ),
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
    path(
        "importacion-masiva/",
        CiudadanoImportacionWebView.as_view(),
        name="ciudadanos_web_importacion",
    ),
    path(
        "importacion-masiva/lotes/<int:pk>/",
        CiudadanoImportacionLoteWebView.as_view(),
        name="ciudadanos_web_importacion_lote",
    ),
    path(
        "importacion-masiva/lotes/<int:pk>/reanudar/",
        CiudadanoImportacionReanudarWebView.as_view(),
        name="ciudadanos_web_importacion_reanudar",
    ),
    path(
        "revision/",
        CiudadanoColaRevisionWebView.as_view(),
        name="ciudadanos_web_cola_revision",
    ),
    path(
        "<int:pk>/descartar-revision/",
        CiudadanoDescartarRevisionWebView.as_view(),
        name="ciudadanos_web_descartar_revision",
    ),
    path(
        "familiares/<int:pk>/eliminar/",
        GrupoFamiliarEliminarWebView.as_view(),
        name="ciudadanos_web_familiar_eliminar",
    ),
]
