"""Rutas de ``/api/web/comedores/admisiones/legales/`` del detalle legal (AD03.03).

Ver ``admisiones.web_api_legales``. Se incluyen con prefijo ``legales/`` después de la
ruta del listado.
"""

from django.urls import path

from admisiones.web_api_legales import (
    LegalesAccionWebView,
    LegalesDetalleWebView,
    RevisionComplementarioWebView,
)

urlpatterns = [
    path("<int:pk>/", LegalesDetalleWebView.as_view(), name="admisiones_web_legal"),
    path(
        "<int:pk>/acciones/<slug:accion>/",
        LegalesAccionWebView.as_view(),
        name="admisiones_web_legal_accion",
    ),
    path(
        "<int:pk>/complementario/revision/",
        RevisionComplementarioWebView.as_view(),
        name="admisiones_web_legal_revision",
    ),
]
