"""Rutas de ``/api/web/cdi/`` del alta y la edición de intervenciones (CDI06, G1 v1).

Ver ``centrodeinfancia.web_api_intervencion_form``.
"""

from django.urls import path

from centrodeinfancia.web_api_intervencion_form import (
    IntervencionCrearWebView,
    IntervencionEditarWebView,
)

urlpatterns = [
    path(
        "centros/<int:pk>/intervenciones/crear/",
        IntervencionCrearWebView.as_view(),
        name="centrodeinfancia_web_intervencion_crear",
    ),
    path(
        "centros/<int:pk>/intervenciones/<int:pk2>/editar/",
        IntervencionEditarWebView.as_view(),
        name="centrodeinfancia_web_intervencion_editar",
    ),
]
