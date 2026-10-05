"""Composición completa en un solo proceso: core más todos los backends.

La usan los tests y el desarrollo local (``docker-compose.yml``), para
trabajar como antes sin levantar un servicio por vertical. En deploy cada
servicio corre con su propio settings: ``config.settings`` (core) y
``<vertical>_runtime.settings`` (backends).
"""

from config.settings import *  # noqa: F401,F403  pylint: disable=wildcard-import,unused-wildcard-import
from config.settings import INSTALLED_APPS
from config.backends import load_backends_registry

_BACKENDS = load_backends_registry()

INSTALLED_APPS = INSTALLED_APPS + [
    app for spec in _BACKENDS.values() for app in spec["apps"]
]
ROOT_URLCONF = "config.urls_all"

# Todo corre en este proceso: el core no reenvía a ningún backend.
SISOC_BACKENDS = {}
