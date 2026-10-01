"""URLs del backend de Dispositivos.

``backend_urlpatterns`` son las rutas propias: sus prefijos coinciden con
``url_prefixes`` de ``config/backends.json`` (el core reenvía esos prefijos a
este proceso) y ``config/urls_all.py`` las monta en la composición completa.
"""

from django.urls import include, path

from config.urls_dev import dev_urlpatterns
from core.url_registry import stub_urlpatterns

backend_urlpatterns = [
    path("", include("dispositivos.urls")),
    path("", include("datacalle.urls")),
    path("api/datacalle/", include("datacalle.api_urls")),
]

urlpatterns = [
    # Salud del proceso, para el healthcheck del contenedor.
    path("", include("healthcheck.urls")),
    *backend_urlpatterns,
    *dev_urlpatterns(),
]
# Nombres del core y de otros backends, solo para reverse() (core/url_registry.py).
urlpatterns += stub_urlpatterns(urlpatterns)

handler404 = "config.views.page_not_found"
handler500 = "config.views.server_error"
