"""Rutas de ``/api/web/comedores/admisiones/`` del circuito técnico/legal (AD03).

Ver ``admisiones.web_api_listas``.
"""

from django.urls import path

from admisiones.web_api_detalle import AdmisionDetailWebView
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
    path("<int:pk>/", EditorWebView.as_view(), name="admisiones_web_editor"),
    path(
        "<int:pk>/acciones/<slug:accion>/",
        EditorAccionWebView.as_view(),
        name="admisiones_web_editor_accion",
    ),
]
