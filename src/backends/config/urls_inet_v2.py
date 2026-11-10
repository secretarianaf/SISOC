"""URLConf reducido para generar el contrato INET, no para servir tráfico."""

from django.urls import include, path

urlpatterns = [path("api/inet/", include("VAT.api_inet_urls"))]
