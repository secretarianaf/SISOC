"""Issue #2741: cada vertical separado expone su admin real desde el índice del portal."""

import importlib
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from django.test import RequestFactory, override_settings
from django.urls import clear_url_caches, resolve

from config.backends import load_backends_registry
from core.context_processors import admin_backends

# backend -> app label con ModelAdmins propios (URL /admin/<app_label>/).
ADMINS_DE_VERTICALES = {
    "cdf": "centrodefamilia",
    "cdi": "centrodeinfancia",
    "celiaquia": "celiaquia",
    "dispositivos": "dispositivos",
    "inspecciones": "inspecciones",
    "pas": "pas",
    "vat": "VAT",
    "vpsl": "ver_para_ser_libre",
}


def test_todo_backend_con_admin_py_tiene_enlace_en_el_portal():
    backends_dir = Path(__file__).resolve().parents[2]
    registro = load_backends_registry()
    con_admin = {
        nombre
        for nombre, spec in registro.items()
        if any(
            (backends_dir / nombre / app / "admin.py").exists() for app in spec["apps"]
        )
    }
    con_enlace = {
        nombre for nombre, spec in registro.items() if spec.get("admin_links")
    }
    assert con_admin <= con_enlace


@pytest.mark.parametrize("backend,app_label", ADMINS_DE_VERTICALES.items())
def test_registro_declara_prefijo_y_enlace_admin(backend, app_label):
    spec = load_backends_registry()[backend]
    assert f"admin/{app_label}/" in spec["url_prefixes"]
    assert "admin/" not in spec["url_prefixes"]
    assert {"url": f"/admin/{app_label}/", "app_label": app_label}.items() <= next(
        link for link in spec["admin_links"] if link["app_label"] == app_label
    ).items()


@pytest.mark.parametrize("backend,app_label", ADMINS_DE_VERTICALES.items())
def test_portal_reenvia_solo_el_admin_del_dueno(backend, app_label):
    import config.urls  # pylint: disable=import-outside-toplevel

    spec = load_backends_registry()[backend]
    try:
        with override_settings(
            ROOT_URLCONF="config.urls",
            SISOC_BACKENDS={backend: {**spec, "origin": "http://owner.invalid"}},
        ):
            importlib.reload(config.urls)
            clear_url_caches()
            proxy = f"backend_proxy_{backend}_"
            assert str(resolve(f"/admin/{app_label}/").url_name).startswith(proxy)
            assert not str(resolve("/admin/auth/user/").url_name).startswith(proxy)
    finally:
        importlib.reload(config.urls)
        clear_url_caches()


@pytest.mark.parametrize("backend,app_label", ADMINS_DE_VERTICALES.items())
def test_indice_admin_muestra_el_vertical_solo_a_superusuarios(backend, app_label):
    # Issue #2789: el admin es solo para superusuarios; staff con permiso del
    # módulo ya no alcanza.
    request = RequestFactory().get("/admin/")
    request.user = SimpleNamespace(
        is_authenticated=True,
        is_active=True,
        is_staff=True,
        is_superuser=True,
    )
    spec = load_backends_registry()[backend]
    with override_settings(SISOC_BACKENDS={backend: spec}):
        urls = [link["url"] for link in admin_backends(request)["backend_admin_links"]]
        assert urls == [f"/admin/{app_label}/"]
        request.user.is_superuser = False
        assert not admin_backends(request)["backend_admin_links"]


@pytest.mark.parametrize("backend,app_label", ADMINS_DE_VERTICALES.items())
def test_runtime_del_dueno_sirve_su_admin(backend, app_label):
    script = f"""
import config, django
django.setup()
from django.apps import apps
from django.contrib import admin
from django.core.checks import run_checks
from django.urls import resolve
modelos = apps.get_app_config({app_label!r}).get_models()
assert any(admin.site.is_registered(modelo) for modelo in modelos)
assert resolve('/admin/{app_label}/').url_name == 'app_list'
errors = [e for e in run_checks() if e.level >= 40]
assert not errors, errors
print('ADMIN_VERTICAL_OK')
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).resolve().parents[4],
        env={
            **os.environ,
            "DJANGO_SETTINGS_MODULE": f"{backend}_runtime.settings",
            "WAIT_FOR_DB": "false",
        },
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "ADMIN_VERTICAL_OK" in result.stdout
