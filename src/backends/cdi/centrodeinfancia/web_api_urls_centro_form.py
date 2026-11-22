"""Rutas de ``/api/web/cdi/`` del alta y la edición de un centro (G1 v1).

Ver ``centrodeinfancia.web_api_centro_form``.
"""

from django.urls import path

from centrodeinfancia.web_api_centro_form import (
    CentroCrearWebView,
    CentroEditarWebView,
)

urlpatterns = [
    path(
        "centros/crear/",
        CentroCrearWebView.as_view(),
        name="centrodeinfancia_web_centro_crear",
    ),
    path(
        "centros/<int:pk>/editar/",
        CentroEditarWebView.as_view(),
        name="centrodeinfancia_web_centro_editar",
    ),
]
