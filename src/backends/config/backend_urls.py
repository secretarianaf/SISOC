"""URLconf común a todos los backends por vertical.

Cada ``src/backends/<x>/<x>_runtime/urls.py`` define ``backend_urlpatterns`` (sus
rutas propias, que coinciden con ``url_prefixes`` de src/backends/config/backends.json y
que ``src/backends/config/urls_all.py`` monta en la composición completa) y hace::

    urlpatterns = urlpatterns_de_backend(backend_urlpatterns)
"""

from django.urls import include, path

from ciudadanos.views import contribucion_detalle_ciudadano
from config.urls_dev import dev_urlpatterns
from core.url_registry import stub_urlpatterns


def urlpatterns_de_backend(backend_urlpatterns):
    patrones = [
        # Salud del proceso, para el healthcheck del contenedor.
        path("", include("healthcheck.urls")),
        *backend_urlpatterns,
        # Endpoints del kernel (filtros favoritos, etc.): el core reenvía acá
        # los de secciones de este backend (``favorite_sections``).
        path("", include("core.urls")),
        # Secciones de Ciudadano 360 que aporta este backend: las pide el core
        # (ciudadanos.detail_contributions).
        path(
            "ciudadanos/<int:pk>/contribucion/<str:nombre>/",
            contribucion_detalle_ciudadano,
            name="ciudadano_contribucion",
        ),
        *dev_urlpatterns(),
    ]
    # Nombres del core y de otros backends, solo para reverse()
    # (core/url_registry.py).
    return patrones + stub_urlpatterns(patrones)
