"""URLs del backend de Centro de Infancia (con Ticketera) (ver src/backends/config/backend_urls.py)."""

from django.urls import include, path

from config.backend_urls import urlpatterns_de_backend

backend_urlpatterns = [
    path("", include("centrodeinfancia.urls")),
    path("api/ticketera/", include("ticketera.api_urls")),
]

urlpatterns = urlpatterns_de_backend(backend_urlpatterns)

handler404 = "config.views.page_not_found"
handler500 = "config.views.server_error"
