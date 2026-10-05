"""Settings de prueba: solo el kernel, sin apps de dominio.

Representa lo que instala cualquier backend por vertical (#2309). Lo usa
``src/backends/kernel/tests/test_kernel_arranca_solo.py`` para verificar que el kernel no depende
de dominios (FKs, señales o imports en el arranque).
"""

from config.settings import *  # noqa: F401,F403  pylint: disable=wildcard-import,unused-wildcard-import
from config.settings import MIDDLEWARE, TEMPLATES

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.admindocs",
    "crispy_forms",
    "crispy_bootstrap5",
    "django_extensions",
    "formtools",
    "import_export",
    "auditlog",
    "rest_framework",
    "rest_framework.authtoken",
    "rest_framework_api_key",
    "drf_spectacular",
    "corsheaders",
    # Kernel
    "users",
    "core",
    "organizaciones",
    "catalogo_intervenciones",
    "sentry.apps.SentryConfig",
    "ciudadanos",
    "audittrail",
]
# Encuestas es del core: su middleware corre en el core antes del proxy.
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
ROOT_URLCONF = "healthcheck.urls"
