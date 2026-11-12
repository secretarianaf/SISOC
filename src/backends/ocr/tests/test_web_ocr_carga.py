"""Web API (G1 v1) of the OCR upload: ``/api/web/ocr/`` (OCR01.01).

Shares the native form and ``create_ocr_job``; access is the native rule of
``ocr/`` (superuser or ``ocr.use_ocr``). Never calls a real OCR engine.
"""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, override_settings

from core import web_gate
from ocr.models import OCRJob, OCRJobDocument

ROOT = "/api/web/ocr/carga/"
CREAR = "/api/web/ocr/lotes/"

pytestmark = pytest.mark.django_db


def _user(username, permiso=True, **extra):
    user = get_user_model().objects.create_user(username, **extra)
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    if permiso:
        user.user_permissions.add(Permission.objects.get(codename="use_ocr"))
    return user


def _client(user, **kwargs):
    client = Client(**kwargs)
    client.force_login(user)
    return client


def _archivo(nombre="a.png", contenido=b"img"):
    return SimpleUploadedFile(
        nombre, contenido, content_type="application/octet-stream"
    )


@pytest.fixture(name="dueno")
def dueno_fixture():
    return _user("ocr_dueno")


@pytest.fixture(name="web")
def web_fixture(dueno):
    return _client(dueno)


@pytest.fixture(autouse=True, name="media")
def media_fixture(tmp_path):
    with override_settings(MEDIA_ROOT=str(tmp_path)):
        yield


def test_get_lists_options_limits_and_only_own_recent_jobs(web, dueno):
    ajeno = _user("ocr_ajeno")
    propios = [OCRJob.objects.create(requested_by=dueno) for _ in range(11)]
    OCRJob.objects.create(requested_by=ajeno)

    respuesta = web.get(ROOT)

    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["max_file_size_mb"] == 20
    assert datos["allowed_extensions"] == ["jpeg", "jpg", "pdf", "png"]
    assert [o["name"] for o in datos["options"]] == [
        "opt_preprocess",
        "opt_pdf_text_layer",
        "opt_auto_orient",
    ]
    assert all(o["initial"] is True for o in datos["options"])
    assert datos["options"][0]["label"] == "Preprocesado de imagen"
    assert datos["options"][1]["help_text"].startswith("Aprovecha el texto digital")
    assert [j["id"] for j in datos["recent_jobs"]] == [
        j.pk
        for j in sorted(propios, key=lambda j: (j.requested_at, j.pk), reverse=True)
    ][:10]
    assert set(datos["recent_jobs"][0]) == {
        "id",
        "requested_at",
        "status",
        "processed_documents",
        "total_documents",
        "detail_url",
    }
    assert datos["messages"] == []
    assert respuesta["Cache-Control"] == "private, no-store"


def test_superuser_sees_only_own_recent_jobs():
    root = _user("ocr_root", permiso=False, is_superuser=True)
    otro = _user("ocr_otro")
    OCRJob.objects.create(requested_by=otro)
    propio = OCRJob.objects.create(requested_by=root)

    datos = _client(root).get(ROOT).json()

    assert [j["id"] for j in datos["recent_jobs"]] == [propio.pk]


def test_post_without_files_is_400_and_creates_nothing(web):
    respuesta = web.post(CREAR, {"opt_preprocess": "on"})

    assert respuesta.status_code == 400
    assert respuesta.json() == {
        "errors": {"archivos": ["Debe seleccionar al menos un archivo."]}
    }
    assert not OCRJob.objects.exists()


def test_post_reports_every_file_error_together_and_creates_nothing(web):
    grande = _archivo("grande.pdf", b"x" * (21 * 1024 * 1024))

    respuesta = web.post(CREAR, {"archivos": [_archivo("notas.txt"), grande]})

    assert respuesta.status_code == 400
    assert respuesta.json()["errors"]["archivos"] == [
        "'notas.txt': tipo de archivo no admitido (.txt). Use: jpeg, jpg, pdf, png.",
        "'grande.pdf': archivo demasiado grande (21.0 MB, máximo 20 MB).",
    ]
    assert not OCRJob.objects.exists()
    assert not OCRJobDocument.objects.exists()


def test_valid_post_creates_the_batch_with_checkbox_semantics(web, dueno):
    respuesta = web.post(
        CREAR,
        {
            "archivos": [_archivo("uno.png"), _archivo("dos.pdf")],
            "opt_pdf_text_layer": "on",
            "opt_auto_orient": "on",
        },
    )

    assert respuesta.status_code == 201
    job = OCRJob.objects.get()
    assert respuesta.json() == {
        "id": job.pk,
        "message": (
            f"Lote OCR #{job.pk} creado con 2 archivo(s). "
            "El procesamiento se ejecuta en segundo plano."
        ),
        "detail_url": f"/ocr/{job.pk}/",
    }
    assert job.requested_by == dueno
    assert job.status == OCRJob.Status.PENDING
    assert job.total_documents == 2
    assert (job.opt_preprocess, job.opt_pdf_text_layer, job.opt_auto_orient) == (
        False,
        True,
        True,
    )
    assert list(job.documents.values_list("original_filename", flat=True)) == [
        "uno.png",
        "dos.pdf",
    ]
    # The native layout would show it on the next page: the detail consumes it.
    detalle = web.get(f"{CREAR}{job.pk}/").json()
    assert detalle["messages"] == [
        {"message": respuesta.json()["message"], "level": "success"}
    ]
    assert web.get(f"{CREAR}{job.pk}/").json()["messages"] == []


def test_anonymous_gets_401_json(client):
    for metodo, url in (("get", ROOT), ("post", CREAR)):
        respuesta = getattr(client, metodo)(url)
        assert respuesta.status_code == 401, url
        assert respuesta.json() == {"detail": web_gate.DETAIL_UNAUTHENTICATED}


def test_user_without_permission_gets_403_and_creates_nothing():
    web = _client(_user("sin_ocr", permiso=False))

    assert web.get(ROOT).status_code == 403
    assert web.post(CREAR, {"archivos": [_archivo()]}).status_code == 403
    assert not OCRJob.objects.exists()


def test_superuser_without_the_permission_passes():
    web = _client(_user("super_ocr", permiso=False, is_superuser=True))

    assert web.get(ROOT).status_code == 200
    assert web.post(CREAR, {"archivos": [_archivo()]}).status_code == 201


def test_methods_and_csrf(dueno):
    web = _client(dueno)
    protegido = _client(dueno, enforce_csrf_checks=True)

    assert web.post(ROOT, {}).status_code == 405
    assert web.get(CREAR).status_code == 405
    assert protegido.post(CREAR, {"archivos": [_archivo()]}).status_code == 403
    assert not OCRJob.objects.exists()


def test_native_upload_page_is_unchanged(web):
    respuesta = web.get("/ocr/")

    assert respuesta.status_code == 200
    assert "Extracción de texto (OCR)" in respuesta.content.decode()
