"""Rutas globales cuyo dominio funcional pertenece a Celiaquía."""

from django.urls import path

from celiaquia.canonical_report import canonical_report
from core.decorators import permissions_any_required

urlpatterns = [
    path(
        "reporter-provincias/",
        permissions_any_required(["celiaquia.view_reporte_provincias"])(
            canonical_report
        ),
        name="reporter_provincias",
    ),
]
