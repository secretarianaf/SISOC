"""Rutas de ``/api/web/auditoria/`` (G1 v1): auditoría en el core."""

from django.urls import path

from audittrail.web_auditoria import AuditoriaEventoWebView, AuditoriaListadoWebView
from audittrail.web_historial import HistorialInstanciaWebView

urlpatterns = [
    path(
        "listado/",
        AuditoriaListadoWebView.as_view(),
        name="audittrail_web_listado",
    ),
    path(
        "evento/<int:pk>/",
        AuditoriaEventoWebView.as_view(),
        name="audittrail_web_evento",
    ),
    path(
        "<str:app_label>/<str:model_name>/<str:object_pk>/",
        HistorialInstanciaWebView.as_view(),
        name="audittrail_web_historial",
    ),
]
