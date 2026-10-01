"""Settings del backend de Dispositivos.

Hereda del core la configuración común (DB, sesión, seguridad, logging,
integraciones) y cambia solo lo que define el proceso: apps, URLs y WSGI.
La imagen de este backend no contiene las apps del core, así que
``INSTALLED_APPS`` no puede nombrarlas.
"""

from config.settings import *  # noqa: F401,F403  pylint: disable=wildcard-import,unused-wildcard-import
from config.settings import CORE_APPS, INSTALLED_APPS, MIDDLEWARE, TEMPLATES
from config.backends import load_backends_registry

BACKEND_NAME = "dispositivos"
BACKEND_APPS = load_backends_registry()[BACKEND_NAME]["apps"]

# Las del settings base menos las del core: así se conservan las compartidas,
# el kernel y las que el base suma según el entorno (debug_toolbar, silk).
INSTALLED_APPS = [app for app in INSTALLED_APPS if app not in CORE_APPS] + BACKEND_APPS
ROOT_URLCONF = "dispositivos_runtime.urls"
# WSGI_APPLICATION se hereda: config.wsgi importa config (que arma el
# sys.path) antes de cargar este settings desde DJANGO_SETTINGS_MODULE.

# El backend no es proxy de nadie.
SISOC_BACKENDS = {}

# Encuestas vive en el core. Su middleware ya corre en el core antes de que el
# proxy reenvíe el request (kernel/core/backend_proxy.py), así que el bloqueo
# por encuesta obligatoria sigue aplicando sobre las páginas de este backend.
MIDDLEWARE = [m for m in MIDDLEWARE if not m.startswith("encuestas.")]
TEMPLATES = [
    {
        **TEMPLATES[0],
        "OPTIONS": {
            **TEMPLATES[0]["OPTIONS"],
            "context_processors": [
                cp
                for cp in TEMPLATES[0]["OPTIONS"]["context_processors"]
                if not cp.startswith("encuestas.")
            ],
        },
    }
]
