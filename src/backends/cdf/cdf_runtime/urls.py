"""URLs del backend de Centro de Familia (ver src/backends/config/backend_urls.py)."""

from django.contrib import admin
from django.urls import include, path

from config.backend_urls import urlpatterns_de_backend

backend_urlpatterns = [
    # Antes sin prefijo (/centros/, /beneficiarios/...): el core redirige
    # esas rutas acá (src/backends/config/urls.py, solo por compatibilidad).
    path("centrodefamilia/", include("centrodefamilia.urls")),
    path("api/centrodefamilia/", include("centrodefamilia.api_urls")),
]

# El admin queda fuera de backend_urlpatterns: settings_all ya lo monta completo.
urlpatterns = urlpatterns_de_backend(
    [path("admin/", admin.site.urls), *backend_urlpatterns]
)

handler404 = "config.views.page_not_found"
handler500 = "config.views.server_error"
