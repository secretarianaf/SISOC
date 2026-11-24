"""Rutas de ``/api/web/cdf/`` de preinscripción, beneficiarios y responsables (CDF03).

Ver ``centrodefamilia.web_api_beneficiarios``.
"""

from django.urls import path

from centrodefamilia.web_api_beneficiarios import (
    BeneficiarioDetailWebView,
    BeneficiariosExportDisponibleWebView,
    BeneficiariosListWebView,
    BuscarCuilWebView,
    BuscarResponsableWebView,
    PreinscripcionOptionsWebView,
    PreinscripcionWebView,
    ResponsableDetailWebView,
    ResponsablesListWebView,
)

urlpatterns = [
    path(
        "beneficiarios/preinscripcion/options/",
        PreinscripcionOptionsWebView.as_view(),
        name="web_cdf_preinscripcion_options",
    ),
    path(
        "beneficiarios/preinscripcion/",
        PreinscripcionWebView.as_view(),
        name="web_cdf_preinscripcion",
    ),
    path(
        "beneficiarios/buscar-cuil/",
        BuscarCuilWebView.as_view(),
        name="web_cdf_buscar_cuil",
    ),
    path(
        "beneficiarios/buscar-responsable/",
        BuscarResponsableWebView.as_view(),
        name="web_cdf_buscar_responsable",
    ),
    path(
        "beneficiarios/",
        BeneficiariosListWebView.as_view(),
        name="web_cdf_beneficiarios_list",
    ),
    path(
        "beneficiarios/exportar/disponible/",
        BeneficiariosExportDisponibleWebView.as_view(),
        name="web_cdf_beneficiarios_exportar_disponible",
    ),
    path(
        "beneficiarios/<int:pk>/",
        BeneficiarioDetailWebView.as_view(),
        name="web_cdf_beneficiarios_detail",
    ),
    path(
        "responsables/",
        ResponsablesListWebView.as_view(),
        name="web_cdf_responsables_list",
    ),
    path(
        "responsables/<int:pk>/",
        ResponsableDetailWebView.as_view(),
        name="web_cdf_responsables_detail",
    ),
]
