"""Rutas de ``/api/web/cdf/`` del Informe Cabal (CDF01).

Ver ``centrodefamilia.web_api_informecabal``.
"""

from django.urls import path

from centrodefamilia.web_api_informecabal import (
    InformeCabalArchivoWebView,
    InformeCabalListWebView,
    InformeCabalPorCentroWebView,
    InformeCabalRegistroWebView,
)

urlpatterns = [
    path(
        "informecabal/",
        InformeCabalListWebView.as_view(),
        name="web_cdf_informecabal_list",
    ),
    path(
        "informecabal/registro/<int:pk>/",
        InformeCabalRegistroWebView.as_view(),
        name="web_cdf_informecabal_registro",
    ),
    path(
        "informecabal/<int:pk>/",
        InformeCabalArchivoWebView.as_view(),
        name="web_cdf_informecabal_archivo",
    ),
    path(
        "centros/<int:centro_id>/informecabal/<int:pk>/",
        InformeCabalPorCentroWebView.as_view(),
        name="web_cdf_informecabal_por_centro",
    ),
]
