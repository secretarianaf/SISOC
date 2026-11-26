"""Rutas de ``/api/web/cdi/`` del detalle del formulario de nómina (G1 v1).

Ver ``centrodeinfancia.web_api_nomina_formulario``.
"""

from django.urls import path

from centrodeinfancia.web_api_nomina_formulario import NominaFormularioWebView

urlpatterns = [
    path(
        "nomina/<int:pk>/formulario/",
        NominaFormularioWebView.as_view(),
        name="centrodeinfancia_web_nomina_formulario",
    ),
]
