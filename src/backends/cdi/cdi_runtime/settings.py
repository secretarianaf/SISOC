"""Settings del backend de Centro de Infancia (con Ticketera)."""

from config.settings import *  # noqa: F401,F403  pylint: disable=wildcard-import,unused-wildcard-import
from config.backend_settings import aplicar

aplicar(globals(), "cdi")
