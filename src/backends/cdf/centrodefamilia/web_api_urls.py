"""Rutas de ``/api/web/cdf/`` de Centro de Familia (G1 v1).

Ver ``centrodefamilia.web_api`` (consulta de centros, CDF04.01) y
``centrodefamilia.web_api_gestion`` (alta, edición y baja, CDF04.02).
"""

from django.urls import path

from centrodefamilia.web_api import (
    CentroDetailWebView,
    CentroListWebView,
    CentroUsuariosWebView,
)
from centrodefamilia.web_api_gestion import (
    CentroCrearWebView,
    CentroEditarWebView,
    CentroEliminarWebView,
    CentroOptionsWebView,
)

urlpatterns = [
    path("centros/", CentroListWebView.as_view(), name="web_cdf_centros_list"),
    path(
        "centros/<int:pk>/",
        CentroDetailWebView.as_view(),
        name="web_cdf_centros_detail",
    ),
    path(
        "centros/<int:pk>/usuarios/",
        CentroUsuariosWebView.as_view(),
        name="web_cdf_centros_usuarios",
    ),
    path(
        "centros/options/",
        CentroOptionsWebView.as_view(),
        name="web_cdf_centros_options",
    ),
    path("centros/crear/", CentroCrearWebView.as_view(), name="web_cdf_centros_crear"),
    path(
        "centros/<int:pk>/editar/",
        CentroEditarWebView.as_view(),
        name="web_cdf_centros_editar",
    ),
    path(
        "centros/<int:pk>/eliminar/",
        CentroEliminarWebView.as_view(),
        name="web_cdf_centros_eliminar",
    ),
]
