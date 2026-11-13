"""API web del backend CDI (``/api/web/cdi/``, G1 v1): rutas de cada app del backend."""

from django.urls import include, path

urlpatterns = [
    path("", include("centrodeinfancia.web_api_urls")),
    path("", include("centrodeinfancia.web_api_urls_trabajadores")),
    path("", include("centrodeinfancia.web_api_urls_formularios")),
]
