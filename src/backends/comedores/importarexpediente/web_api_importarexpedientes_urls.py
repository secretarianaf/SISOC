"""Rutas de ``/api/web/comedores/importarexpedientes/`` (G1 v1): ver ``importarexpediente.web_api_importarexpedientes``."""

from django.urls import path

from importarexpediente.web_api_importarexpedientes import (
    BorrarDatosWebView,
    EliminarWebView,
    FechasAcreditacionWebView,
    ImportarWebView,
    LoteDetailWebView,
    LotesListWebView,
    SubirWebView,
)

urlpatterns = [
    path("", LotesListWebView.as_view(), name="importarexpedientes_web_list"),
    path("subir/", SubirWebView.as_view(), name="importarexpedientes_web_subir"),
    path(
        "<int:pk>/", LoteDetailWebView.as_view(), name="importarexpedientes_web_detalle"
    ),
    path(
        "<int:pk>/importar/",
        ImportarWebView.as_view(),
        name="importarexpedientes_web_importar",
    ),
    path(
        "<int:pk>/borrar-datos/",
        BorrarDatosWebView.as_view(),
        name="importarexpedientes_web_borrar",
    ),
    path(
        "<int:pk>/eliminar/",
        EliminarWebView.as_view(),
        name="importarexpedientes_web_eliminar",
    ),
    path(
        "<int:pk>/fechas-acreditacion/",
        FechasAcreditacionWebView.as_view(),
        name="importarexpedientes_web_fechas",
    ),
]
