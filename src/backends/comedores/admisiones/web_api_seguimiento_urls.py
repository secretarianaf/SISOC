"""Rutas de ``/api/web/comedores/admisiones/`` del circuito técnico/legal (AD03).

Ver ``admisiones.web_api_listas``.
"""

from django.urls import include, path

from admisiones.web_api_detalle import AdmisionDetailWebView
from admisiones.web_api_documentos import (
    DocumentoEliminarWebView,
    DocumentoPersonalizadoWebView,
    DocumentoSubirWebView,
)
from admisiones.web_api_editor import EditorAccionWebView, EditorWebView
from admisiones.web_api_listas import LegalesListaWebView, TecnicosListaWebView

urlpatterns = [
    path("tecnicos/", TecnicosListaWebView.as_view(), name="admisiones_web_tecnicos"),
    path("legales/", LegalesListaWebView.as_view(), name="admisiones_web_legales"),
    path(
        "<int:comedor_pk>/<int:pk>/detalle/",
        AdmisionDetailWebView.as_view(),
        name="admisiones_web_detalle",
    ),
    path("legales/", include("admisiones.web_api_legales_urls")),
    path("<int:pk>/", EditorWebView.as_view(), name="admisiones_web_editor"),
    path(
        "<int:pk>/acciones/<slug:accion>/",
        EditorAccionWebView.as_view(),
        name="admisiones_web_editor_accion",
    ),
    path(
        "<int:admision_id>/documentacion/<int:documentacion_id>/subir/",
        DocumentoSubirWebView.as_view(),
        name="admisiones_web_documento_subir",
    ),
    path(
        "<int:admision_id>/documentacion/personalizada/agregar/",
        DocumentoPersonalizadoWebView.as_view(),
        name="admisiones_web_documento_personalizado",
    ),
    path(
        "<int:admision_id>/documentacion/<int:documentacion_id>/eliminar/",
        DocumentoEliminarWebView.as_view(),
        name="admisiones_web_documento_eliminar",
    ),
]
