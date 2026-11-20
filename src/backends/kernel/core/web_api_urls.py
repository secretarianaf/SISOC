"""Rutas de ``/api/web/core/`` (G1 v1): pantallas del núcleo servidas por el core."""

from django.urls import path

from core.web_api_arquitectura import ArquitecturaWebView
from core.web_api_novedades import NovedadesWebView
from core.web_api_papelera import PapeleraRestaurarWebView, PapeleraWebView
from core.web_api_programas import (
    ProgramaCreateWebView,
    ProgramaDeleteWebView,
    ProgramaDetailWebView,
    ProgramaListWebView,
    ProgramaUpdateWebView,
)

urlpatterns = [
    path("novedades/", NovedadesWebView.as_view(), name="core_web_novedades"),
    path("arquitectura/", ArquitecturaWebView.as_view(), name="core_web_arquitectura"),
    path("programas/", ProgramaListWebView.as_view(), name="core_web_programas"),
    path(
        "programas/crear/",
        ProgramaCreateWebView.as_view(),
        name="core_web_programa_crear",
    ),
    path(
        "programas/<int:pk>/",
        ProgramaDetailWebView.as_view(),
        name="core_web_programa_detalle",
    ),
    path(
        "programas/<int:pk>/editar/",
        ProgramaUpdateWebView.as_view(),
        name="core_web_programa_editar",
    ),
    path(
        "programas/<int:pk>/eliminar/",
        ProgramaDeleteWebView.as_view(),
        name="core_web_programa_eliminar",
    ),
    path("papelera/", PapeleraWebView.as_view(), name="core_web_papelera"),
    path(
        "papelera/restaurar/<str:app_label>/<str:model_name>/<int:pk>/",
        PapeleraRestaurarWebView.as_view(),
        name="core_web_papelera_restaurar",
    ),
]
