"""Rutas de ``/api/web/comedores/organizaciones/`` (G1 v1): ver ``gestion_organizaciones.web_api``."""

from django.urls import path

from gestion_organizaciones.web_api import (
    OrganizacionLegajoWebView,
    OrganizacionListadoWebView,
)
from gestion_organizaciones.web_api_abm import (
    OrganizacionBajaWebView,
    OrganizacionCuilWebView,
    OrganizacionFormularioWebView,
    OrganizacionGuardarWebView,
    OrganizacionSubtiposWebView,
)

urlpatterns = [
    path(
        "listado/",
        OrganizacionListadoWebView.as_view(),
        name="organizaciones_web_listado",
    ),
    path(
        "<int:pk>/",
        OrganizacionLegajoWebView.as_view(),
        name="organizaciones_web_legajo",
    ),
    path(
        "formulario/",
        OrganizacionFormularioWebView.as_view(),
        name="organizaciones_web_formulario",
    ),
    path(
        "<int:pk>/formulario/",
        OrganizacionFormularioWebView.as_view(),
        name="organizaciones_web_formulario_editar",
    ),
    path(
        "crear/", OrganizacionGuardarWebView.as_view(), name="organizaciones_web_crear"
    ),
    path(
        "<int:pk>/editar/",
        OrganizacionGuardarWebView.as_view(),
        name="organizaciones_web_editar",
    ),
    path(
        "<int:pk>/baja/",
        OrganizacionBajaWebView.as_view(),
        name="organizaciones_web_baja",
    ),
    path(
        "subtipos/",
        OrganizacionSubtiposWebView.as_view(),
        name="organizaciones_web_subtipos",
    ),
    path("cuil/", OrganizacionCuilWebView.as_view(), name="organizaciones_web_cuil"),
]
