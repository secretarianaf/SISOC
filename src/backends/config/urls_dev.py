"""URLs de desarrollo comunes al core y a cada backend.

Con ``DEBUG``, el settings base agrega ``debug_toolbar`` (y opcionalmente
``silk``) a apps y middleware; cada servicio necesita además sus URLs.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path


def dev_urlpatterns():
    if not settings.DEBUG or getattr(settings, "RUNNING_TESTS", False):
        return []
    patterns = [path("__debug__/", include("debug_toolbar.urls"))]
    if getattr(settings, "ENABLE_SILK", False):
        patterns += [path("silk/", include("silk.urls", namespace="silk"))]
    patterns += staticfiles_urlpatterns()
    patterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    return patterns
