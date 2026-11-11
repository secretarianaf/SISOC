"""API web del backend CDF (``/api/web/cdf/``, G1 v1): rutas de cada app del backend."""

from django.urls import include, path

urlpatterns = [
    path("", include("centrodefamilia.web_api_urls")),
    path("", include("centrodefamilia.web_api_beneficiarios_urls")),
]
