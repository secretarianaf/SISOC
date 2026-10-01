"""Separación de servicios: core y backends por vertical (config/backends.json).

- El core no instala apps de backends y reenvía sus prefijos por proxy.
- Cada backend arranca y renderiza sus páginas con su propio settings.
- ``config/url_registry.json`` está al día con la composición completa.
"""

import os
import subprocess
import sys
from pathlib import Path

from django.urls import get_resolver

from config.backends import load_backends_registry
from core.url_registry import cargar, generar

REPO_ROOT = Path(__file__).resolve().parent.parent
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
import os
import config, django
from django.conf import settings
django.setup()
from django.apps import apps
from django.core.management import call_command
from django.db import connections
from django.test import Client, override_settings

class SinMigraciones(dict):
    def __contains__(self, key):
        return True
    def __getitem__(self, key):
        return None

for app in {core_apps!r}:
    assert not apps.is_installed(app.split(".")[0]), app

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
    for path in {paths!r}:
        respuesta = cliente.get(path)
        assert respuesta.status_code == 200, (path, respuesta.status_code)
    assert cliente.get("/comedores/").status_code == 404
print("BACKEND_OK")
"""


def test_backend_dispositivos_arranca_y_renderiza_sus_paginas():
    from config.settings import CORE_APPS  # pylint: disable=import-outside-toplevel

    script = SCRIPT_BACKEND.format(
        core_apps=CORE_APPS,
        paths=[
            "/health/",
            "/dispositivos/",
            "/dispositivos/crear",
            "/datacalle/relevamientos/",
            "/datacalle/relevamientos/crear/",
        ],
    )
    resultado = _correr("dispositivos_runtime.settings", script)

    assert "BACKEND_OK" in resultado.stdout, resultado.stdout + resultado.stderr[-4000:]
