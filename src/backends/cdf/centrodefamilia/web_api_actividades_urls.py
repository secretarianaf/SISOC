"""Rutas de ``/api/web/cdf/`` de la actividad y sus participantes (CDF-C).

Ver ``centrodefamilia.web_api_actividades``.
"""

from django.urls import path

from centrodefamilia.web_api_actividad_form import (
    ActividadCrearWebView,
    ActividadEditarWebView,
)
from centrodefamilia.web_api_actividades import (
    ActividadDetailWebView,
    ParticipanteCrearWebView,
    ParticipanteEliminarWebView,
    ParticipantePromoverWebView,
)
from centrodefamilia.web_api_actividades_gestion import (
    ActividadCatalogoWebView,
    ActividadListWebView,
)
from centrodefamilia.web_api_asistencia import AsistenciaWebView

_ACTIVIDAD = "centros/<int:centro_id>/actividades/<int:actividad_id>/"

urlpatterns = [
    path(
        "actividades/",
        ActividadListWebView.as_view(),
        name="web_cdf_actividades_list",
    ),
    path(
        "actividades/nueva/",
        ActividadCatalogoWebView.as_view(),
        name="web_cdf_actividades_catalogo",
    ),
    path(
        "actividades/<int:pk>/",
        ActividadDetailWebView.as_view(),
        name="web_cdf_actividades_detail",
    ),
    path(
        "actividades/<int:pk>/editar/",
        ActividadEditarWebView.as_view(),
        name="web_cdf_actividades_editar",
    ),
    path(
        "centros/<int:centro_id>/actividades/nueva/",
        ActividadCrearWebView.as_view(),
        name="web_cdf_actividades_crear",
    ),
    path(
        "actividades/<int:pk>/asistencia/",
        AsistenciaWebView.as_view(),
        name="web_cdf_actividades_asistencia",
    ),
    path(
        _ACTIVIDAD + "participantes/",
        ParticipanteCrearWebView.as_view(),
        name="web_cdf_participantes_crear",
    ),
    path(
        _ACTIVIDAD + "participantes/<int:pk>/eliminar/",
        ParticipanteEliminarWebView.as_view(),
        name="web_cdf_participantes_eliminar",
    ),
    path(
        _ACTIVIDAD + "lista-espera/<int:pk>/promover/",
        ParticipantePromoverWebView.as_view(),
        name="web_cdf_participantes_promover",
    ),
]
