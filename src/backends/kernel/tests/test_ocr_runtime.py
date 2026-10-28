"""Frontera OCR, rutas historicas y navegacion sin modelos en el portal."""

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
from core.url_registry import recolectar


def test_ocr_conserva_mixin_tablas_y_permiso():
    from ocr.models import OCRJob, OCRJobDocument
    from ocr.views import OCRUploadView
    from users.view_mixins import AdminRequiredMixin

    assert issubclass(OCRUploadView, AdminRequiredMixin)
    assert OCRUploadView.required_permissions == ("ocr.use_ocr",)
    assert OCRJob._meta.db_table == "ocr_ocrjob"
    assert OCRJobDocument._meta.db_table == "ocr_ocrjobdocument"


def test_rutas_publicas_ocr_conservan_prefijo_y_nombres():
    from ocr_runtime.urls import backend_urlpatterns

    assert {route["name"] for route in recolectar(backend_urlpatterns)} == {
        "ocr_upload",
        "ocr_job_detail",
        "ocr_document_download",
    }
    assert all(
        route["regex"].startswith("^ocr/") for route in recolectar(backend_urlpatterns)
    )
    assert load_backends_registry()["ocr"]["url_prefixes"] == ["ocr/", "admin/ocr/"]


@pytest.mark.parametrize(
    "path", ["/ocr/", "/ocr/17/", "/ocr/documentos/8/descargar/", "/admin/ocr/ocrjob/"]
)
def test_portal_reenvia_ocr_al_dueno(path):
    import config.urls

    spec = load_backends_registry()["ocr"]
    try:
        with override_settings(
            ROOT_URLCONF="config.urls",
            SISOC_BACKENDS={"ocr": {**spec, "origin": "http://ocr.invalid"}},
        ):
            importlib.reload(config.urls)
            clear_url_caches()
            assert resolve(path).url_name.startswith("backend_proxy_ocr_")
            assert not resolve("/login/").url_name.startswith("backend_proxy_")
    finally:
        importlib.reload(config.urls)
        clear_url_caches()


@pytest.mark.parametrize("module", ["config.settings", "ocr_runtime.settings"])
def test_arranque_frio_ocr_y_portal_sin_instalarse_mutuamente(module):
    script = """
import config, django
django.setup()
from django.apps import apps
from django.conf import settings
from django.core.checks import run_checks
from django.contrib import admin
owner = settings.SETTINGS_MODULE == 'ocr_runtime.settings'
assert apps.is_installed('ocr') == owner
assert apps.is_installed('usuarios') != owner
assert not apps.is_installed('comedores')
if owner:
    from ocr.models import OCRJob, OCRJobDocument
    from ocr.views import OCRUploadView
    from users.view_mixins import AdminRequiredMixin
    assert issubclass(OCRUploadView, AdminRequiredMixin)
    assert OCRJob._meta.db_table == 'ocr_ocrjob'
    assert OCRJobDocument._meta.db_table == 'ocr_ocrjobdocument'
    assert admin.site.is_registered(OCRJob)
    assert 'process_ocr_jobs' in __import__('django.core.management', fromlist=['get_commands']).get_commands()
errors = [error for error in run_checks() if error.level >= 40]
assert not errors, errors
print('OCR_RUNTIME_OK')
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
    assert "OCR_RUNTIME_OK" in result.stdout


def test_admin_ocr_remoto_solo_para_superusuarios():
    request = RequestFactory().get("/admin/")
    request.user = SimpleNamespace(
        is_authenticated=True,
        is_active=True,
        is_staff=True,
        is_superuser=True,
    )
    with override_settings(SISOC_BACKENDS={"ocr": load_backends_registry()["ocr"]}):
        assert admin_backends(request)["backend_admin_links"] == [
            {"label": "OCR", "url": "/admin/ocr/", "app_label": "ocr"}
        ]
        # Issue #2789: el permiso del módulo ya no alcanza sin superusuario.
        request.user.is_superuser = False
        assert not admin_backends(request)["backend_admin_links"]
