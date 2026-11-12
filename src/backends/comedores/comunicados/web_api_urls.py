"""Rutas de ``/api/web/comedores/comunicados/`` (G1 v1): ver ``comunicados.web_api_views``."""

from django.urls import path

from comunicados.web_api_views import (
    ComunicadoArchivarWebView,
    ComunicadoCreateWebView,
    ComunicadoDeleteWebView,
    ComunicadoDestacadoWebView,
    ComunicadoPublicarWebView,
    ComunicadoUpdateWebView,
    DestinatariosBuscarWebView,
    DestinatariosTodosWebView,
    ComunicadoDetailWebView,
    ComunicadoGestionWebView,
    ComunicadoListWebView,
)

urlpatterns = [
    path("", ComunicadoListWebView.as_view(), name="comunicados_web_listado"),
    path(
        "gestion/", ComunicadoGestionWebView.as_view(), name="comunicados_web_gestion"
    ),
    path(
        "<int:pk>/", ComunicadoDetailWebView.as_view(), name="comunicados_web_detalle"
    ),
    path(
        "<int:pk>/publicar/",
        ComunicadoPublicarWebView.as_view(),
        name="comunicados_web_publicar",
    ),
    path(
        "<int:pk>/archivar/",
        ComunicadoArchivarWebView.as_view(),
        name="comunicados_web_archivar",
    ),
    path(
        "<int:pk>/destacado/",
        ComunicadoDestacadoWebView.as_view(),
        name="comunicados_web_destacado",
    ),
    path(
        "<int:pk>/eliminar/",
        ComunicadoDeleteWebView.as_view(),
        name="comunicados_web_eliminar",
    ),
    path("crear/", ComunicadoCreateWebView.as_view(), name="comunicados_web_crear"),
    path(
        "<int:pk>/editar/",
        ComunicadoUpdateWebView.as_view(),
        name="comunicados_web_editar",
    ),
    path(
        "destinatarios/<str:universo>/buscar/",
        DestinatariosBuscarWebView.as_view(),
        name="comunicados_web_destinatarios_buscar",
    ),
    path(
        "destinatarios/<str:universo>/todos/",
        DestinatariosTodosWebView.as_view(),
        name="comunicados_web_destinatarios_todos",
    ),
]
