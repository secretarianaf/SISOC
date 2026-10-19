"""Fronteras C3, cobertura de rutas y navegacion admin sin modelos remotos."""

import importlib
import os
import re
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from django.test import RequestFactory, override_settings
from django.urls import clear_url_caches, resolve

from config.backends import load_backends_registry
from core.context_processors import admin_backends
from core.url_registry import recolectar


def test_todas_las_rutas_publicas_del_dueno_tienen_prefijo_de_proxy():
    from comedores_runtime.urls import (  # pylint: disable=import-outside-toplevel
        backend_urlpatterns,
    )

    spec = load_backends_registry()["comedores"]
    prefixes = [re.escape(prefix) for prefix in spec["url_prefixes"]]
    for route in recolectar(backend_urlpatterns):
        regex = route["regex"].lstrip("^")
        if regex.startswith("interno/"):
            continue
        assert any(regex.startswith(prefix) for prefix in prefixes), route
    assert not any(prefix.startswith("interno/") for prefix in spec["url_prefixes"])
    assert "ajax/" not in spec["url_prefixes"]
    assert "admin/" not in spec["url_prefixes"]


@pytest.mark.parametrize(
    "path,proxied",
    [
        ("/comedores/listar", True),
        ("/montoprestacion/listar", True),
        ("/ajax/actualizar-numero-gde/", True),
        ("/api/relevamiento", True),
        ("/admin/pwa/nominaespaciopwa/", True),
        ("/admin/core/montoprestacionprograma/", True),
        ("/login/", False),
        ("/api/users/login/", False),
        ("/admin/pwa/auditoriasesionpwa/", False),
        ("/admin/auth/user/", False),
    ],
)
def test_portal_enruta_solo_los_prefijos_del_dueno(path, proxied):
    import config.urls  # pylint: disable=import-outside-toplevel

    spec = load_backends_registry()["comedores"]
    try:
        with override_settings(
            ROOT_URLCONF="config.urls",
            SISOC_BACKENDS={"comedores": {**spec, "origin": "http://owner.invalid"}},
        ):
            # Los patrones se construyen al importar; settings_all ya cargo el
            # modulo sin proxy. Simular su carga en el proceso del portal.
            importlib.reload(config.urls)
            clear_url_caches()
            match = resolve(path)
            assert str(match.url_name).startswith("backend_proxy_comedores_") == proxied
    finally:
        importlib.reload(config.urls)
        clear_url_caches()


@pytest.mark.parametrize("module", ["config.settings", "comedores_runtime.settings"])
def test_cada_runtime_arranca_sin_instalar_las_apps_del_otro(module):
    script = """
import config, django
django.setup()
from django.apps import apps
from django.conf import settings
from django.core.checks import run_checks
from django.contrib import admin
from core.models import MontoPrestacionPrograma
spec = __import__('config.backends', fromlist=['load_backends_registry']).load_backends_registry()['comedores']
owner = settings.SETTINGS_MODULE == 'comedores_runtime.settings'
assert all(apps.is_installed(app) == owner for app in spec['apps'])
assert apps.is_installed('usuarios') != owner
assert admin.site.is_registered(MontoPrestacionPrograma) == owner
errors = [e for e in run_checks() if e.level >= 40]
assert not errors, errors
print('C3_RUNTIME_OK')
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).resolve().parents[4],
        env={**os.environ, "DJANGO_SETTINGS_MODULE": module, "WAIT_FOR_DB": "false"},
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "C3_RUNTIME_OK" in result.stdout


def test_indice_admin_filtra_links_y_no_los_duplica_en_composicion_local():
    request = RequestFactory().get("/admin/")
    request.user = SimpleNamespace(
        is_active=True,
        is_staff=True,
        has_module_perms=lambda app: app == "pwa",
        has_perm=lambda perm: perm == "core.view_montoprestacionprograma",
    )
    spec = load_backends_registry()["comedores"]
    with override_settings(SISOC_BACKENDS={"comedores": spec}):
        links = admin_backends(request)["backend_admin_links"]
        assert [link["label"] for link in links] == [
            "Espacios comunitarios",
            "Montos de prestación",
        ]
        request.user.is_staff = False
        assert admin_backends(request)["backend_admin_links"] == []
    with override_settings(SISOC_BACKENDS={}):
        assert admin_backends(request)["backend_admin_links"] == []
