"""Consumidores kernel sin importar negocio; runtime real se verifica en C3."""

import os
from pathlib import Path
import subprocess
import sys


def test_ciudadano_favoritos_y_auditoria_sin_comedores():
    script = """
import importlib.abc, sys
class RejectDomains(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {
            'pwa', 'comedores', 'duplas', 'relevamientos', 'admisiones',
            'acompanamientos', 'rendicioncuentasfinal', 'rendicioncuentasmensual',
            'expedientespagos', 'importarexpediente', 'intervenciones',
            'gestion_organizaciones', 'historial', 'comunicados',
        }:
            raise AssertionError('Dependencia de dominio: ' + fullname)
sys.meta_path.insert(0, RejectDomains())
import config, django
django.setup()
import ciudadanos.views, ciudadanos.urls, ciudadanos.detail_contributions
import core.views, audittrail.views, audittrail.admin
import usuarios.services_user_import, usuarios.services_user_import_jobs
import usuarios.views_user_import
from django.contrib import admin
from core.models import MontoPrestacionPrograma
assert not admin.site.is_registered(MontoPrestacionPrograma)
print('C2_CONSUMIDORES_SIN_COMEDORES_OK')
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).resolve().parents[4],
        env={
            **os.environ,
            "DJANGO_SETTINGS_MODULE": "tests.settings_solo_kernel",
            "WAIT_FOR_DB": "false",
        },
        capture_output=True,
        text=True,
        check=False,
        timeout=240,
    )
    assert "C2_CONSUMIDORES_SIN_COMEDORES_OK" in result.stdout, (
        result.stdout + result.stderr
    )
