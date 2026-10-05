"""URLs del backend de Dispositivos (ver src/backends/config/backend_urls.py)."""

from django.urls import include, path

from config.backend_urls import urlpatterns_de_backend

backend_urlpatterns = [
    path("", include("dispositivos.urls")),
    path("", include("datacalle.urls")),
    path("api/datacalle/", include("datacalle.api_urls")),
]

urlpatterns = urlpatterns_de_backend(backend_urlpatterns)

handler404 = "config.views.page_not_found"
handler500 = "config.views.server_error"
