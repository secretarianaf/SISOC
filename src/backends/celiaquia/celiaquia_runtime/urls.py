"""URLs del backend de Celiaquía (ver src/backends/config/backend_urls.py)."""

from django.contrib import admin
from django.urls import include, path

from config.backend_urls import urlpatterns_de_backend

backend_urlpatterns = [
    path("", include("celiaquia.global_urls")),
    path("celiaquia/", include("celiaquia.urls")),
    # API del front v2 (/v2/celiaquia/). Vive en el backend y no en
    # config/urls.py, igual que /api/ticketera/ y /api/datacalle/.
    path("api/celiaquia/", include("celiaquia.api_urls")),
]

# El admin queda fuera de backend_urlpatterns: settings_all ya lo monta completo.
urlpatterns = urlpatterns_de_backend(
    [path("admin/", admin.site.urls), *backend_urlpatterns]
)

handler404 = "config.views.page_not_found"
handler500 = "config.views.server_error"
