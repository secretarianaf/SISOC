"""Settings del backend de Inspecciones escolares."""

from config.settings import *  # noqa: F401,F403  pylint: disable=wildcard-import,unused-wildcard-import
from config.backend_settings import aplicar

aplicar(globals(), "inspecciones")
