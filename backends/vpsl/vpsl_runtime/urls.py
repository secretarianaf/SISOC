"""URLs del backend de Ver para Ser Libre (ver config/backend_urls.py)."""

from django.urls import include, path

from config.backend_urls import urlpatterns_de_backend

backend_urlpatterns = [
    path("", include("ver_para_ser_libre.urls")),
    path("api/vpsl/", include("ver_para_ser_libre.api_urls")),
]

urlpatterns = urlpatterns_de_backend(backend_urlpatterns)

handler404 = "config.views.page_not_found"
handler500 = "config.views.server_error"
