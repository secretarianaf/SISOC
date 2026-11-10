"""URLs del backend de Centro de Infancia (con Ticketera) (ver src/backends/config/backend_urls.py)."""

from django.contrib import admin
from django.urls import include, path

from config.backend_urls import urlpatterns_de_backend

backend_urlpatterns = [
    path("", include("centrodeinfancia.urls")),
    path("api/ticketera/", include("ticketera.api_urls")),
    # API web de las pantallas React (G1 v1, cdi_runtime.web_api_urls).
    path("api/web/cdi/", include("cdi_runtime.web_api_urls")),
]

# El admin queda fuera de backend_urlpatterns: settings_all ya lo monta completo.
urlpatterns = urlpatterns_de_backend(
    [path("admin/", admin.site.urls), *backend_urlpatterns]
)

handler404 = "config.views.page_not_found"
handler500 = "config.views.server_error"
