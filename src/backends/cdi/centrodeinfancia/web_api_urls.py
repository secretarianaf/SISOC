"""Rutas de ``/api/web/cdi/`` de Centro de Infancia (G1 v1).

Ver ``centrodeinfancia.web_api`` (reportes),
``centrodeinfancia.web_api_observaciones`` (observaciones),
``centrodeinfancia.web_api_centros`` (listado de centros) y
``centrodeinfancia.web_api_nomina`` (ficha de un destinatario de la nómina) y
``centrodeinfancia.web_api_nomina_lista`` (lista de la nómina y derivación) y
``centrodeinfancia.web_api_legajo`` (ficha del centro y sus acciones) y
``centrodeinfancia.web_api_intervenciones`` (detalle de intervención y su documento) y
``centrodeinfancia.web_api_bajas`` (confirmación de baja de centro y de nómina).
"""

from django.urls import path

from centrodeinfancia.web_api import ReportesWebView
from centrodeinfancia.web_api_bajas import CentroEliminarWebView, NominaEliminarWebView
from centrodeinfancia.web_api_centros import CentrosListWebView
from centrodeinfancia.web_api_formulario_calidad import (
    CalidadCargarWebView,
    CalidadDetalleWebView,
    CalidadHistorialWebView,
)
from centrodeinfancia.web_api_legajo import (
    CentroDetalleWebView,
    centro_estado_web,
    trabajador_eliminar_web,
    usuario_estado_web,
)
from centrodeinfancia.web_api_intervenciones import (
    IntervencionDetalleWebView,
    IntervencionDocumentacionWebView,
    intervencion_documentacion_eliminar_web,
)
from centrodeinfancia.web_api_nomina import NominaDestinatarioWebView
from centrodeinfancia.web_api_nomina_lista import (
    NominaListaWebView,
    nomina_derivar_web,
)
from centrodeinfancia.web_api_observaciones import (
    ObservacionCrearWebView,
    ObservacionDetalleWebView,
    ObservacionEditarWebView,
    ObservacionEliminarWebView,
)

urlpatterns = [
    path(
        "centros/<int:pk>/calidad/",
        CalidadHistorialWebView.as_view(),
        name="centrodeinfancia_web_calidad_listado",
    ),
    path(
        "centros/<int:pk>/calidad/cargar/",
        CalidadCargarWebView.as_view(),
        name="centrodeinfancia_web_calidad_cargar",
    ),
    path(
        "centros/<int:pk>/calidad/<int:form_pk>/",
        CalidadDetalleWebView.as_view(),
        name="centrodeinfancia_web_calidad_detalle",
    ),
    path("reportes/", ReportesWebView.as_view(), name="centrodeinfancia_web_reportes"),
    path("centros/", CentrosListWebView.as_view(), name="centrodeinfancia_web_centros"),
    path(
        "centros/<int:pk>/",
        CentroDetalleWebView.as_view(),
        name="centrodeinfancia_web_centro_detalle",
    ),
    path(
        "centros/<int:pk>/usuarios/<int:acceso_id>/estado/",
        usuario_estado_web,
        name="centrodeinfancia_web_usuario_estado",
    ),
    path(
        "centros/<int:pk>/estado/",
        centro_estado_web,
        name="centrodeinfancia_web_centro_estado",
    ),
    path(
        "centros/<int:pk>/trabajadores/<int:trabajador_id>/eliminar/",
        trabajador_eliminar_web,
        name="centrodeinfancia_web_trabajador_eliminar",
    ),
    path(
        "centros/<int:pk>/nomina/",
        NominaListaWebView.as_view(),
        name="centrodeinfancia_web_nomina_lista",
    ),
    path(
        "nomina/<int:pk>/derivar/",
        nomina_derivar_web,
        name="centrodeinfancia_web_nomina_derivar",
    ),
    path(
        "centros/<int:pk>/nomina/<int:nomina_id>/",
        NominaDestinatarioWebView.as_view(),
        name="centrodeinfancia_web_nomina_destinatario",
    ),
    path(
        "intervenciones/<int:pk>/",
        IntervencionDetalleWebView.as_view(),
        name="centrodeinfancia_web_intervencion_detalle",
    ),
    path(
        "intervenciones/<int:pk>/documentacion/",
        IntervencionDocumentacionWebView.as_view(),
        name="centrodeinfancia_web_intervencion_documentacion",
    ),
    path(
        "intervenciones/<int:intervencion_id>/documentacion/eliminar/",
        intervencion_documentacion_eliminar_web,
        name="centrodeinfancia_web_intervencion_documentacion_eliminar",
    ),
    path(
        "centros/<int:pk>/observaciones/crear/",
        ObservacionCrearWebView.as_view(),
        name="centrodeinfancia_web_observacion_crear",
    ),
    path(
        "observaciones/<int:pk>/",
        ObservacionDetalleWebView.as_view(),
        name="centrodeinfancia_web_observacion_detalle",
    ),
    path(
        "observaciones/<int:pk>/editar/",
        ObservacionEditarWebView.as_view(),
        name="centrodeinfancia_web_observacion_editar",
    ),
    path(
        "observaciones/<int:pk>/eliminar/",
        ObservacionEliminarWebView.as_view(),
        name="centrodeinfancia_web_observacion_eliminar",
    ),
    path(
        "centros/<int:pk>/eliminar/",
        CentroEliminarWebView.as_view(),
        name="centrodeinfancia_web_centro_eliminar",
    ),
    path(
        "centros/<int:pk>/nomina/<int:pk2>/eliminar/",
        NominaEliminarWebView.as_view(),
        name="centrodeinfancia_web_nomina_eliminar",
    ),
]
