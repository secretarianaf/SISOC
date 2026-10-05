"""URLs de la composición completa (``config.settings_all``).

Las propias del core más las propias de cada backend (``backend_urlpatterns``
de su URLconf), servidas en el mismo proceso. Sin stubs: todo nombre es real.
"""

from importlib import import_module

from config.backends import load_backends_registry
from config.urls import core_urlpatterns, handler404, handler500

urlpatterns = [
    pattern
    for spec in load_backends_registry().values()
    for pattern in import_module(spec["urlconf"]).backend_urlpatterns
] + list(core_urlpatterns)

__all__ = ["urlpatterns", "handler404", "handler500"]
