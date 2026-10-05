"""Reporte de Celiaquia por provincia.

La logica vive en `celiaquia/services/reporte_service/`, para que la API REST
calcule lo mismo. Aca queda el shell de la pantalla.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from celiaquia.services.reporte_service import (
    _anotar_clasificacion_pagina,
    _apply_report_filters,
    _build_case_context,
    _build_clasificacion_aprobados,
    _build_current_querystring,
    _build_expedientes_por_provincia,
    _build_filtros_activos,
    _build_metricas_principales,
    _build_pagination,
    _build_status_items,
    _build_subtotales_aprobados,
    _build_tendencia_mensual,
    _clasificar_legajo_aprobado,
    _es_menor,
    _extract_filter_values,
    _format_percentage,
    _get_provincia_actual,
    _get_provincias_disponibles,
    _group_counts,
    _percentage,
    build_report_context,
    CLASIFICACION_APROBADOS_ITEMS,
    CLASIFICACION_APROBADOS_LABELS,
    CLASIFICACION_APROBADOS_TONES,
    CUPO_ITEMS,
    CUPO_LABELS,
    PAGE_SIZE,
    QUERY_PARAM_LABELS,
    SINTYS_ITEMS,
    SINTYS_LABELS,
    VALIDACION_ITEMS,
    VALIDACION_LABELS,
)

# Reexportados a proposito: los tests los importan desde aca.
__all__ = [
    "ReporterProvinciasView",
    *[
        "CLASIFICACION_APROBADOS_ITEMS",
        "CLASIFICACION_APROBADOS_LABELS",
        "CLASIFICACION_APROBADOS_TONES",
        "CUPO_ITEMS",
        "CUPO_LABELS",
        "PAGE_SIZE",
        "QUERY_PARAM_LABELS",
        "SINTYS_ITEMS",
        "SINTYS_LABELS",
        "VALIDACION_ITEMS",
        "VALIDACION_LABELS",
        "_anotar_clasificacion_pagina",
        "_apply_report_filters",
        "_build_case_context",
        "_build_clasificacion_aprobados",
        "_build_current_querystring",
        "_build_expedientes_por_provincia",
        "_build_filtros_activos",
        "_build_metricas_principales",
        "_build_pagination",
        "_build_status_items",
        "_build_subtotales_aprobados",
        "_build_tendencia_mensual",
        "_clasificar_legajo_aprobado",
        "_es_menor",
        "_extract_filter_values",
        "_format_percentage",
        "_get_provincia_actual",
        "_get_provincias_disponibles",
        "_group_counts",
        "_percentage",
        "build_report_context",
    ],
]


class ReporterProvinciasView(LoginRequiredMixin, TemplateView):
    template_name = "celiaquia/reporter_provincias.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_report_context(self.request))
        return context
