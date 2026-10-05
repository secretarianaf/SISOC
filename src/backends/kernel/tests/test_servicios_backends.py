"""Separación de servicios: core y backends por vertical (src/backends/config/backends.json).

- El core no instala apps de backends y reenvía sus prefijos por proxy.
- Cada backend arranca y renderiza sus páginas con su propio settings.
- ``src/backends/config/url_registry.json`` está al día con la composición completa.
"""

import os
import subprocess

import pytest
import sys
from pathlib import Path

from django.urls import get_resolver

from config.backends import load_backends_registry
from core.url_registry import cargar, generar

REPO_ROOT = Path(__file__).resolve().parents[4]
BACKENDS = load_backends_registry()


def _correr(settings_module, script):
    env = {
        **os.environ,
        "DJANGO_SETTINGS_MODULE": settings_module,
        "WAIT_FOR_DB": "false",
        "DJANGO_DEBUG": "False",
    }
    return subprocess.run(
        [sys.executable, "-c", script],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )


def test_registro_de_urls_al_dia():
    """Si falla: ``DJANGO_SETTINGS_MODULE=config.settings_all python manage.py generar_registro_urls``."""
    assert generar(get_resolver().url_patterns) == cargar()


def test_el_core_no_instala_apps_de_backends():
    apps_backends = [app for spec in BACKENDS.values() for app in spec["apps"]]
    resultado = _correr(
        "config.settings",
        "import config, django; django.setup()\n"
        "from django.apps import apps\n"
        "from django.urls import reverse, resolve\n"
        f"for app in {apps_backends!r}:\n"
        "    assert not apps.is_installed(app), app\n"
        "assert resolve('/dispositivos/').url_name.startswith('backend_proxy_')\n"
        "assert reverse('dispositivos_listar') == '/dispositivos/'\n"
        "print('CORE_OK')",
    )
    assert "CORE_OK" in resultado.stdout, resultado.stdout + resultado.stderr


SCRIPT_BACKEND = """
import config, django
django.setup()
from django.apps import apps
from django.core.management import call_command
from django.db import connections
from django.test import Client, override_settings
from django.urls import URLPattern, URLResolver
from importlib import import_module
from django.conf import settings

class SinMigraciones(dict):
    def __contains__(self, key):
        return True
    def __getitem__(self, key):
        return None

for app in {core_apps!r}:
    assert not apps.is_installed(app.split(".")[0]), app

def rutas_sin_argumentos(patrones, prefijo=""):
    for entry in patrones:
        if isinstance(entry, URLResolver):
            ruta = str(entry.pattern)
            if "<" in ruta or "(" in ruta:
                continue
            yield from rutas_sin_argumentos(entry.url_patterns, prefijo + ruta)
        elif isinstance(entry, URLPattern):
            ruta = str(entry.pattern)
            if "<" in ruta or "(" in ruta or "^" in ruta:
                continue
            yield "/" + prefijo + ruta

with override_settings(
    MIGRATION_MODULES=SinMigraciones(),
    ALLOWED_HOSTS=["*"],
    SECRET_KEY="solo-test",
):
    connections.databases["default"] = {{
        **connections.databases["default"],
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }}
    connections["default"].close()
    del connections["default"]
    call_command("migrate", run_syncdb=True, verbosity=0)
    from django.contrib.auth.models import User
    usuario = User.objects.create_superuser("probe", "p@example.com", "x")
    cliente = Client(raise_request_exception=True)
    cliente.force_login(usuario)
    propias = import_module(settings.ROOT_URLCONF).backend_urlpatterns
    rutas = sorted(set(rutas_sin_argumentos(propias)))
    assert rutas, "sin rutas sin argumentos"
    for ruta in rutas:
        try:
            respuesta = cliente.get(ruta)
        except Exception as exc:
            raise AssertionError(f"{{ruta}}: {{type(exc).__name__}}: {{exc}}") from exc
        assert respuesta.status_code < 500, (ruta, respuesta.status_code)
    assert cliente.get("/health/").status_code == 200
    print("RUTAS", len(rutas))
print("BACKEND_OK")
"""


@pytest.mark.parametrize("backend", sorted(BACKENDS))
def test_backend_arranca_y_sus_paginas_no_fallan(backend):
    """Cada backend, en su propio proceso, sirve sus rutas sin errores."""
    from config.settings import CORE_APPS  # pylint: disable=import-outside-toplevel

    settings_module = BACKENDS[backend]["urlconf"].split(".")[0] + ".settings"
    resultado = _correr(settings_module, SCRIPT_BACKEND.format(core_apps=CORE_APPS))

    assert "BACKEND_OK" in resultado.stdout, resultado.stdout + resultado.stderr[-4000:]
