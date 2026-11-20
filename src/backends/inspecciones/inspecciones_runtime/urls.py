"""URLs del backend de Inspecciones escolares (ver src/backends/config/backend_urls.py)."""

from django.contrib import admin
from django.urls import include, path

from config.backend_urls import urlpatterns_de_backend
from core.react_activation import react_preview_patterns

backend_urlpatterns = [
    # Entradas React de las pantallas migradas, solo con el flag activo.
    # Antes de las nativas: el GET llega a la entrada; el resto, a la nativa.
    *react_preview_patterns("inspecciones"),
    path("inspecciones/", include("inspecciones.urls")),
    path("api/inspecciones/", include("inspecciones.api_urls")),
    # API web de las pantallas React (G1 v1, inspecciones.web_api).
    path("api/web/inspecciones/", include("inspecciones.web_api_urls")),
]

# El admin queda fuera de backend_urlpatterns: settings_all ya lo monta completo.
urlpatterns = urlpatterns_de_backend(
    [path("admin/", admin.site.urls), *backend_urlpatterns]
)

handler404 = "config.views.page_not_found"
handler500 = "config.views.server_error"
