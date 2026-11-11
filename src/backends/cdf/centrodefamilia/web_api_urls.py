"""Rutas de ``/api/web/cdf/`` de Centro de Familia (G1 v1).

Ver ``centrodefamilia.web_api`` (consulta de centros, CDF04.01).
"""

from django.urls import path

from centrodefamilia.web_api import (
    CentroDetailWebView,
    CentroListWebView,
    CentroUsuariosWebView,
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
]
