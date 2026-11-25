"""Web API (G1 v1) of an OCR batch: ``/api/web/ocr/lotes/<pk>/`` (OCR01.02, OCR02.01)."""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client
from django.utils import timezone

from ocr.models import OCRJob, OCRJobDocument

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


def _client(user):
    client = Client()
    client.force_login(user)
    return client


def _url(job):
    return f"/api/web/ocr/lotes/{job.pk}/"


def _doc(job, nombre, estado, **extra):
    return OCRJobDocument.objects.create(
        job=job, original_filename=nombre, status=estado, **extra
    )


@pytest.fixture(name="dueno")
def dueno_fixture():
    return _user("lote_dueno")


@pytest.fixture(name="lote")
def lote_fixture(dueno):
    job = OCRJob.objects.create(
        requested_by=dueno,
        status=OCRJob.Status.COMPLETED_WITH_ERRORS,
        total_documents=4,
        processed_documents=3,
        failed_documents=1,
        last_error_message="Fallo parcial",
        opt_preprocess=False,
    )
    _doc(
        job,
        "bueno.pdf",
        "completed",
        extracted_text="Hola\nmundo",
        page_count=2,
        file_size=2048,
        processed_at=timezone.now(),
    )
    _doc(job, "vacio.png", "no_text", error_message="Imagen en blanco")
    _doc(job, "roto.png", "failed", error_message="Boom")
    _doc(job, "hueco.pdf", "completed", extracted_text="")
    return job


def test_owner_sees_the_batch_with_documents_in_id_order(lote):
    respuesta = _client(lote.requested_by).get(_url(lote))

    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["id"] == lote.pk
    assert datos["status"] == "completed_with_errors"
    assert (
        datos["total_documents"],
        datos["processed_documents"],
        datos["failed_documents"],
    ) == (4, 3, 1)
    assert datos["last_error_message"] == "Fallo parcial"
    assert datos["options"] == {
        "preprocess": False,
        "pdf_text_layer": True,
        "auto_orient": True,
    }
    assert [d["original_filename"] for d in datos["documents"]] == [
        "bueno.pdf",
        "vacio.png",
        "roto.png",
        "hueco.pdf",
    ]
    bueno = datos["documents"][0]
    assert bueno["page_count"] == 2
    assert bueno["file_size_label"] == "2,0\xa0KB"
    assert bueno["extracted_text"] == "Hola\nmundo"
    assert bueno["processed_at"] == timezone.localtime(
        OCRJobDocument.objects.get(original_filename="bueno.pdf").processed_at
    ).strftime("%d/%m/%Y %H:%M:%S")
    assert datos["upload_url"] == "/ocr/"
    assert respuesta["Cache-Control"] == "private, no-store"


def test_download_link_only_for_completed_documents_with_text(lote):
    datos = _client(lote.requested_by).get(_url(lote)).json()

    enlaces = {d["original_filename"]: d["download_url"] for d in datos["documents"]}
    bueno = OCRJobDocument.objects.get(original_filename="bueno.pdf")
    assert enlaces == {
        "bueno.pdf": f"/ocr/documentos/{bueno.pk}/descargar/",
        "vacio.png": None,
        "roto.png": None,
        "hueco.pdf": None,
    }


def test_other_user_with_permission_gets_404_and_superuser_gets_200(lote):
    otro = _client(_user("lote_otro"))
    root = _client(_user("lote_root", permiso=False, is_superuser=True))

    assert otro.get(_url(lote)).status_code == 404
    assert otro.get("/api/web/ocr/lotes/999999/").status_code == 404
    assert root.get(_url(lote)).status_code == 200


def test_access_guards(lote, client):
    assert client.get(_url(lote)).status_code == 401
    sin_permiso = _client(_user("lote_sin", permiso=False))
    assert sin_permiso.get(_url(lote)).status_code == 403
    assert _client(lote.requested_by).post(_url(lote), {}).status_code == 405


def test_empty_batch_has_no_documents(dueno):
    job = OCRJob.objects.create(requested_by=dueno)

    datos = _client(dueno).get(_url(job)).json()

    assert datos["documents"] == []
    assert datos["status"] == "pending"


def test_native_download_still_rejects_foreign_batches(lote):
    bueno = OCRJobDocument.objects.get(original_filename="bueno.pdf")
    url = f"/ocr/documentos/{bueno.pk}/descargar/"

    assert _client(lote.requested_by).get(url).status_code == 200
    assert _client(_user("lote_ajeno_dl")).get(url).status_code == 404
