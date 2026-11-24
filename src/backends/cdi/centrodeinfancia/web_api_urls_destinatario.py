"""Rutas de ``/api/web/cdi/`` del alta y la edición de destinatarios (nómina CDI, G1 v1).

Ver ``centrodeinfancia.web_api_destinatario``.
"""

from django.urls import path

from centrodeinfancia.web_api_destinatario import (
    DestinatarioCrearWebView,
    DestinatarioEditarWebView,
)

urlpatterns = [
    path(
        "centros/<int:pk>/nomina/crear/",
        DestinatarioCrearWebView.as_view(),
        name="centrodeinfancia_web_destinatario_crear",
    ),
    path(
        "centros/<int:pk>/nomina/<int:nomina_id>/editar/",
        DestinatarioEditarWebView.as_view(),
        name="centrodeinfancia_web_destinatario_editar",
    ),
]
