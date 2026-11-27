"""Settings del backend de Celiaquía."""

import os

from config.settings import *  # noqa: F401,F403  pylint: disable=wildcard-import,unused-wildcard-import
from config.backend_settings import aplicar

aplicar(globals(), "celiaquia")

# Origen del núcleo en la red privada; nunca proviene de la solicitud.
SISOC_CORE_ORIGIN = os.environ.get("SISOC_CORE_ORIGIN", "")
