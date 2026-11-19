"""Rutas de ``/api/web/comedores/admisiones/plantillas-informe/`` (G1 v1).

Ver ``admisiones.web_api_templates``.
"""

from django.urls import path

from admisiones.web_api_template_crear import PlantillaCrearWebView
from admisiones.web_api_template_version import VersionEditarWebView
from admisiones.web_api_templates import (
    IncidenciaDetailWebView,
    IncidenciasListWebView,
    PlantillaDetailWebView,
    PlantillasListWebView,
    VariablesListWebView,
)

urlpatterns = [
    path("", PlantillasListWebView.as_view(), name="gestor_templates_web_listar"),
    path(
        "variables/",
        VariablesListWebView.as_view(),
        name="gestor_templates_web_variables",
    ),
    path(
        "incidencias/",
        IncidenciasListWebView.as_view(),
        name="gestor_templates_web_incidencias",
    ),
    path(
        "incidencias/<int:pk>/",
        IncidenciaDetailWebView.as_view(),
        name="gestor_templates_web_incidencia",
    ),
    path(
        "crear/",
        PlantillaCrearWebView.as_view(),
        name="gestor_templates_web_crear",
    ),
    path(
        "<int:pk>/versiones/<int:version_pk>/",
        VersionEditarWebView.as_view(),
        name="gestor_templates_web_version_editar",
    ),
    path(
        "<int:pk>/",
        PlantillaDetailWebView.as_view(),
        name="gestor_templates_web_detalle",
    ),
]
