"""Worker real en otro proceso: XLSX, proveedor local y checkpoint MySQL."""

import os
import subprocess
import sys
from io import BytesIO
from pathlib import Path

import pytest
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.db import connection
from openpyxl import Workbook

from comedores.models import Comedor
from pwa.models import AccesoComedorPWA
from users.models import UserImportJob, UserImportJobRow

pytestmark = [
    pytest.mark.mysql_compat,
    pytest.mark.django_db(transaction=True),
    pytest.mark.skipif(
        connection.vendor != "mysql", reason="Los dos procesos comparten MySQL real."
    ),
]


def _crear_lote():
    actor = User.objects.create_superuser(username="actor_worker_c3")
    comedor = Comedor.objects.create(nombre="Espacio worker C3")
    book = Workbook()
    book.active.append(
        ["username", "nombre", "apellido", "rol", "comedores", "permisos", "provincias"]
    )
    book.active.append(
        ["importado_worker_c3", "Persona", "C3", "operadora", str(comedor.pk), "", ""]
    )
    output = BytesIO()
    book.save(output)
    job = UserImportJob(
        requested_by=actor,
        original_filename="worker-c3.xlsx",
        send_credentials=False,
        is_pwa_import=True,
    )
    job.archivo.save("worker-c3.xlsx", ContentFile(output.getvalue()))
    return job, comedor


def _ejecutar_worker(tmp_path, settings, *, fallo_checkpoint=False):
    # settings_all y el mismo media temporal de pytest en ambos procesos.
    (tmp_path / "c3_worker_settings.py").write_text(
        "from config.settings_all import *\n"
        f"MEDIA_ROOT = {str(settings.MEDIA_ROOT)!r}\n"
        "EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'\n",
        encoding="utf-8",
    )
    script = """
import config, django
django.setup()
from django.core.management import call_command
from users import pwa_import_access
assert pwa_import_access._adaptador is not None
"""
    if fallo_checkpoint:
        script += """
from unittest.mock import patch
with patch('usuarios.services_user_import_jobs._record_row_created', side_effect=RuntimeError('checkpoint C3')):
    call_command('process_user_import_jobs', once=True)
"""
    else:
        script += "call_command('process_user_import_jobs', once=True)\n"
    return subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).resolve().parents[4],
        env={
            **os.environ,
            "DJANGO_SETTINGS_MODULE": "c3_worker_settings",
            "DJANGO_SERVICE_ROLE": "user_import_worker",
            "DATABASE_NAME": connection.settings_dict["NAME"],
            "WAIT_FOR_DB": "false",
            "PYTHONPATH": os.pathsep.join(
                [str(tmp_path), os.environ.get("PYTHONPATH", "")]
            ),
        },
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )


def test_worker_completo_importa_xlsx_usuario_acceso_y_checkpoint(tmp_path, settings):
    job, comedor = _crear_lote()
    result = _ejecutar_worker(tmp_path, settings)
    assert result.returncode == 0, result.stdout + result.stderr
    user = User.objects.get(username="importado_worker_c3")
    assert AccesoComedorPWA.objects.filter(user=user, comedor=comedor).exists()
    job.refresh_from_db()
    assert job.status == UserImportJob.Status.COMPLETED
    assert job.next_row_index == job.processed_rows == job.created_rows == 1
    assert job.rows.get().status == UserImportJobRow.Status.CREATED


def test_worker_completo_revierte_usuario_y_acceso_si_falla_checkpoint(
    tmp_path, settings
):
    job, comedor = _crear_lote()
    result = _ejecutar_worker(tmp_path, settings, fallo_checkpoint=True)
    assert result.returncode != 0
    assert "checkpoint C3" in result.stderr
    assert not User.objects.filter(username="importado_worker_c3").exists()
    assert not AccesoComedorPWA.objects.filter(comedor=comedor).exists()
    job.refresh_from_db()
    assert job.next_row_index == job.created_rows == 0
