"""URLs del backend de Centro de Familia (ver config/backend_urls.py)."""

from django.urls import include, path

from config.backend_urls import urlpatterns_de_backend

backend_urlpatterns = [
    # Antes sin prefijo (/centros/, /beneficiarios/...): el core redirige
    # esas rutas acá (config/urls.py, solo por compatibilidad).
    path("centrodefamilia/", include("centrodefamilia.urls")),
    path("api/centrodefamilia/", include("centrodefamilia.api_urls")),
]

urlpatterns = urlpatterns_de_backend(backend_urlpatterns)

handler404 = "config.views.page_not_found"
handler500 = "config.views.server_error"
