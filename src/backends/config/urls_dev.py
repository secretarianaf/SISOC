"""URLs de desarrollo comunes al core y a cada backend.

Con ``DEBUG``, el settings base agrega ``debug_toolbar`` (y opcionalmente
``silk``) a apps y middleware; cada servicio necesita además sus URLs.
"""

from posixpath import normpath

from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.http import Http404
from django.urls import include, path as url_path
from django.views.static import serve

_PREFIJO_PRIVADO_CARGAS_CDF = "centrodefamilia/cargas_masivas"


def _servir_media_dev(request, path, **kwargs):
    ruta = normpath(path.replace("\\", "/")).lstrip("/").casefold()
    if ruta == _PREFIJO_PRIVADO_CARGAS_CDF or ruta.startswith(
        f"{_PREFIJO_PRIVADO_CARGAS_CDF}/"
    ):
        raise Http404
    return serve(request, path, **kwargs)


def dev_urlpatterns():
    if not settings.DEBUG or getattr(settings, "RUNNING_TESTS", False):
        return []
    patterns = [url_path("__debug__/", include("debug_toolbar.urls"))]
    if getattr(settings, "ENABLE_SILK", False):
        patterns += [url_path("silk/", include("silk.urls", namespace="silk"))]
    patterns += staticfiles_urlpatterns()
    patterns += static(
        settings.MEDIA_URL, view=_servir_media_dev, document_root=settings.MEDIA_ROOT
    )
    return patterns
