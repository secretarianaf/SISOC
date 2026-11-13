"""Rutas de ``/api/web/auditoria/`` (G1 v1): historial de auditoría en el core."""

from django.urls import path

from audittrail.web_historial import HistorialInstanciaWebView

urlpatterns = [
    path(
        "<str:app_label>/<str:model_name>/<str:object_pk>/",
        HistorialInstanciaWebView.as_view(),
        name="audittrail_web_historial",
    ),
]
