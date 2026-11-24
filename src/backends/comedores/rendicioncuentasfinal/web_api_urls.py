"""Rutas de ``/api/web/comedores/rendicion_cuentas_final/`` (G1 v1): ver ``rendicioncuentasfinal.web_api``."""

from django.urls import path

from rendicioncuentasfinal.web_api import (
    AdjuntarWebView,
    CrearWebView,
    EliminarWebView,
    FisicamentePresentadaWebView,
    SubsanarWebView,
    ValidarWebView,
    RendicionFinalDetalleWebView,
    RendicionFinalDocumentosWebView,
)

urlpatterns = [
    path(
        "comedor/<int:pk>/",
        RendicionFinalDetalleWebView.as_view(),
        name="rendicioncuentasfinal_web_detalle",
    ),
    path(
        "documentos/",
        RendicionFinalDocumentosWebView.as_view(),
        name="rendicioncuentasfinal_web_documentos",
    ),
    path(
        "documentos/adjuntar/",
        AdjuntarWebView.as_view(),
        name="rendicioncuentasfinal_web_adjuntar",
    ),
    path(
        "documentos/<int:documento_id>/validar/",
        ValidarWebView.as_view(),
        name="rendicioncuentasfinal_web_validar",
    ),
    path(
        "documentos/<int:documento_id>/subsanar/",
        SubsanarWebView.as_view(),
        name="rendicioncuentasfinal_web_subsanar",
    ),
    path(
        "documentos/<int:documento_id>/eliminar/",
        EliminarWebView.as_view(),
        name="rendicioncuentasfinal_web_eliminar",
    ),
    path(
        "<int:rendicion_id>/crear/",
        CrearWebView.as_view(),
        name="rendicioncuentasfinal_web_crear",
    ),
    path(
        "<int:rendicion_id>/fisicamente_presentada/",
        FisicamentePresentadaWebView.as_view(),
        name="rendicioncuentasfinal_web_switch",
    ),
]
