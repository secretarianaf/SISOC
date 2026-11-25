"""URLConf reducido para generar el contrato INET, no para servir tráfico."""

from django.urls import include, path

urlpatterns = [path("api/web/vat/", include("VAT.web_api_urls"))]
