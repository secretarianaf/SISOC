"""Rutas de ``/api/web/comedores/organizaciones/`` (G1 v1): ver ``gestion_organizaciones.web_api``."""

from django.urls import path

from gestion_organizaciones.web_api import (
    OrganizacionLegajoWebView,
    OrganizacionListadoWebView,
)
from gestion_organizaciones.web_api_convenio import ConvenioWebView
from gestion_organizaciones.web_api_documentos import (
    EstadoWebView,
    HistorialWebView,
    NumeroGdeWebView,
    PersonalizadaWebView,
    SubirWebView,
    VencimientoWebView,
)
from gestion_organizaciones.web_api_firmantes import vistas
from gestion_organizaciones.web_api_rendiciones import RendicionDetalleWebView
from gestion_organizaciones.web_api_abm import (
    OrganizacionBajaWebView,
    OrganizacionCuilWebView,
    OrganizacionFormularioWebView,
    OrganizacionGuardarWebView,
    OrganizacionSubtiposWebView,
)

FIRMANTE_FORMULARIO, FIRMANTE_GUARDAR, FIRMANTE_BAJA = vistas("firmante")
AVAL_FORMULARIO, AVAL_GUARDAR, AVAL_BAJA = vistas("aval")


def _rutas_firmantes(prefijo, formulario, guardar, baja):
    """Create under the organization, edit and baja under the entity (``alta`` selects the native view)."""
    return [
        path(
            f"<int:pk>/{prefijo}/formulario/",
            formulario,
            {"alta": True},
            name=f"organizaciones_web_{prefijo}_formulario_crear",
        ),
        path(
            f"<int:pk>/{prefijo}/",
            guardar,
            {"alta": True},
            name=f"organizaciones_web_{prefijo}_crear",
        ),
        path(
            f"{prefijo}/<int:pk>/formulario/",
            formulario,
            {"alta": False},
            name=f"organizaciones_web_{prefijo}_formulario_editar",
        ),
        path(
            f"{prefijo}/<int:pk>/",
            guardar,
            {"alta": False},
            name=f"organizaciones_web_{prefijo}_editar",
        ),
        path(
            f"{prefijo}/<int:pk>/baja/",
            baja,
            name=f"organizaciones_web_{prefijo}_baja",
        ),
    ]


urlpatterns = [
    path(
        "<int:pk>/rendiciones/<int:rendicion_id>/",
        RendicionDetalleWebView.as_view(),
        name="organizaciones_web_rendicion_detalle",
    ),
    path(
        "<int:pk>/documentacion/<int:documentacion_id>/historial/",
        HistorialWebView.as_view(),
        name="organizaciones_web_documento_historial",
    ),
    path(
        "<int:pk>/documentacion/<int:documentacion_id>/subir/",
        SubirWebView.as_view(),
        name="organizaciones_web_documento_subir",
    ),
    path(
        "<int:pk>/documentacion/personalizada/",
        PersonalizadaWebView.as_view(),
        name="organizaciones_web_documento_personalizada",
    ),
    path(
        "documentacion/<int:archivo_id>/estado/",
        EstadoWebView.as_view(),
        name="organizaciones_web_documento_estado",
    ),
    path(
        "documentacion/<int:archivo_id>/vencimiento/",
        VencimientoWebView.as_view(),
        name="organizaciones_web_documento_vencimiento",
    ),
    path(
        "documentacion/<int:archivo_id>/numero-gde/",
        NumeroGdeWebView.as_view(),
        name="organizaciones_web_documento_gde",
    ),
    path(
        "proyectos/<int:proyecto_id>/convenio/",
        ConvenioWebView.as_view(),
        name="organizaciones_web_convenio",
    ),
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
    *_rutas_firmantes(
        "firmantes", FIRMANTE_FORMULARIO, FIRMANTE_GUARDAR, FIRMANTE_BAJA
    ),
    *_rutas_firmantes("avales", AVAL_FORMULARIO, AVAL_GUARDAR, AVAL_BAJA),
]
