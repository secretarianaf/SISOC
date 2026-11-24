"""Rutas de ``/api/web/comedores/cursos-app-mobile/`` (G1 v1): ver ``comedores.web_api_cursos``."""

from django.urls import path

from comedores.web_api_cursos import (
    CursoBajaWebView,
    CursoCrearWebView,
    CursoEditarWebView,
    CursosListWebView,
)

urlpatterns = [
    path("", CursosListWebView.as_view(), name="cursos_app_mobile_web_listado"),
    path("crear/", CursoCrearWebView.as_view(), name="cursos_app_mobile_web_crear"),
    path(
        "<int:pk>/editar/",
        CursoEditarWebView.as_view(),
        name="cursos_app_mobile_web_editar",
    ),
    path(
        "<int:pk>/eliminar/",
        CursoBajaWebView.as_view(),
        name="cursos_app_mobile_web_eliminar",
    ),
]
