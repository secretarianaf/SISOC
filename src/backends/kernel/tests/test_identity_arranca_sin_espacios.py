"""Probe real de imports: identidad arranca sin módulos de Comedores."""

import os
import subprocess
import sys
from pathlib import Path


def test_componentes_de_identidad_sin_apps_de_comedores():
    script = """
import importlib.abc, sys
class RejectDomains(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'pwa', 'comedores', 'duplas', 'relevamientos'}:
            raise AssertionError('Dependencia de dominio: ' + fullname)
sys.meta_path.insert(0, RejectDomains())
import config, django
django.setup()
import usuarios.auth_forms, usuarios.auth_views
import usuarios.api_views, usuarios.api_serializers, usuarios.forms
import audittrail.auth, audittrail.admin
print('IDENTIDAD_SIN_ESPACIOS_OK')
"""
    env = {
        **os.environ,
        "DJANGO_SETTINGS_MODULE": "tests.settings_solo_kernel",
        "WAIT_FOR_DB": "false",
    }
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).resolve().parents[4],
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=240,
    )
    assert "IDENTIDAD_SIN_ESPACIOS_OK" in result.stdout, result.stdout + result.stderr
