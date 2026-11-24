"""Rutas de ``/api/web/cdi/`` de los formularios institucionales (CDI03, G1 v1).

Ver ``centrodeinfancia.web_api_formularios_institucionales`` (listado y ficha) y
``centrodeinfancia.web_api_formulario_form`` (alta y edición).
"""

from django.urls import path

from centrodeinfancia.web_api_formulario_form import (
    FormularioCrearWebView,
    FormularioEditarWebView,
)
from centrodeinfancia.web_api_formularios_institucionales import (
    FormularioDetalleWebView,
    FormularioListaWebView,
)

urlpatterns = [
    path(
        "centros/<int:pk>/formularios/",
        FormularioListaWebView.as_view(),
        name="centrodeinfancia_web_formulario_lista",
    ),
    path(
        "centros/<int:pk>/formularios/<int:form_pk>/",
        FormularioDetalleWebView.as_view(),
        name="centrodeinfancia_web_formulario_detalle",
    ),
    path(
        "centros/<int:pk>/formularios/crear/",
        FormularioCrearWebView.as_view(),
        name="centrodeinfancia_web_formulario_crear",
    ),
    path(
        "centros/<int:pk>/formularios/<int:form_pk>/editar/",
        FormularioEditarWebView.as_view(),
        name="centrodeinfancia_web_formulario_editar",
    ),
]
