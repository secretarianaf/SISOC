"""Web API (G1 v1) of the mass mailing (CM01.01 and CM01.02).

Every test uses the in-memory mail backend and never starts the worker loop:
the upload only queues a ``pending`` batch and nothing sends mail in a request.
"""

from io import BytesIO

import pytest
from django.contrib.auth.models import User
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.utils import timezone
from openpyxl import Workbook

from comunicados.models import MailingJob, MailingJobAttachment, MailingJobRow
from comunicados.services_mailing_jobs import (
    claim_next_mailing_job,
    create_mailing_job,
    process_mailing_job,
)

ROOT = "/api/web/comedores/comunicados/mailing/"
NATIVO = "/comunicados/mailing/"

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True, name="correo")
def correo_fixture(settings, tmp_path):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.MEDIA_ROOT = tmp_path / "media"
    settings.MEDIA_ROOT.mkdir()
    mail.outbox.clear()


def _user(nombre, **flags):
    user = User.objects.create_user(nombre, **flags)
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    return user


def _client(user, **extra):
    client = Client(**extra)
    client.force_login(user)
    return client


@pytest.fixture(name="admin")
def admin_fixture():
    return _user("admin_mailing", is_superuser=True)


@pytest.fixture(name="web")
def web_fixture(admin):
    return _client(admin)


def _xlsx(correos=("uno@example.com",), cabecera="mail", hoja="mailing"):
    libro = Workbook()
    sheet = libro.active
    sheet.title = hoja
    sheet.append([cabecera])
    for correo in correos:
        sheet.append([correo])
    salida = BytesIO()
    libro.save(salida)
    return SimpleUploadedFile("destinos.xlsx", salida.getvalue())


def _lote(usuario, correos=("uno@example.com",), **extra):
    job = create_mailing_job(
        uploaded_file=_xlsx(correos),
        asunto=extra.pop("asunto", "Asunto"),
        cuerpo="Cuerpo",
        requested_by=usuario,
    )
    for clave, valor in extra.items():
        setattr(job, clave, valor)
    job.save()
    return job


def _post(client, **extra):
    datos = {"asunto": "Asunto", "cuerpo": "Cuerpo", "archivo": _xlsx()}
    datos.update(extra)
    return client.post(ROOT, datos)


# --- CM01.01 reads -----------------------------------------------------------


def test_form_lists_only_the_own_recent_batches_and_the_fields(web, admin):
    propio = _lote(admin, asunto="Un asunto bastante largo para truncarlo en la tabla")
    _lote(_user("otro_admin_mailing", is_superuser=True))

    respuesta = web.get(ROOT)

    assert respuesta.status_code == 200
    assert respuesta["Cache-Control"] == "private, no-store"
    data = respuesta.json()
    assert data["form_title"] == "Envío de mailing masivo"
    assert [(f["name"], f["type"], f["required"]) for f in data["fields"]] == [
        ("asunto", "text", True),
        ("cuerpo", "textarea", True),
        ("archivo", "file", True),
        ("archivos_adjuntos", "files", False),
    ]
    assert data["fields"][2]["accept"] == ".xlsx"
    assert data["fields"][2]["label"] == "Archivo Excel"
    assert (
        data["fields"][2]["help_text"]
        == "Cargue un archivo .xlsx con una columna 'mail'."
    )
    assert data["template_download_url"] == f"{NATIVO}plantilla/"
    assert data["gestion_url"] == "/comunicados/gestion/"
    assert [j["id"] for j in data["recent_jobs"]] == [propio.pk]
    fila = data["recent_jobs"][0]
    assert fila["status"] == "pending"
    assert fila["asunto_corto"] == "Un asunto bastante largo para…"
    assert fila["detail_url"] == f"{NATIVO}lotes/{propio.pk}/"
    assert fila["requested_at"] == timezone.localtime(propio.requested_at).strftime(
        "%d/%m/%Y %H:%M"
    )


def test_every_read_needs_an_admin_and_a_session(client, admin):
    lote = _lote(admin)
    comun = _client(_user("comun_mailing"))
    for url in (ROOT, f"{ROOT}jobs/{lote.pk}/", f"{NATIVO}plantilla/"):
        assert client.get(url).status_code in (401, 302), url
        assert comun.get(url).status_code == 403, url
    assert client.get(ROOT).status_code == 401
    assert comun.post(f"{ROOT}jobs/{lote.pk}/resume/").status_code == 403


def test_detail_projects_the_batch_rows_and_pages_by_fifty(web, admin):
    lote = _lote(
        admin,
        status=MailingJob.Status.FAILED,
        total_rows=60,
        processed_rows=2,
        sent_rows=1,
        rejected_rows=1,
        last_successful_mail="ok@example.com",
        last_successful_row=2,
        last_attempted_mail="mal",
        last_attempted_row=3,
        last_error_message="El mail 'mal' no es valido.",
        last_error_at=timezone.now(),
    )
    for n in range(2, 62):
        MailingJobRow.objects.create(
            job=lote,
            fila=n,
            mail_destino=f"u{n}@example.com",
            status="sent",
            attempts=1,
        )
    MailingJobRow.objects.create(job=lote, fila=99, status="failed", mensaje="Error")
    MailingJobAttachment.objects.create(
        job=lote,
        archivo=SimpleUploadedFile("a.txt", b"x"),
        nombre_original="a.txt",
    )

    data = web.get(f"{ROOT}jobs/{lote.pk}/").json()

    assert data["job"]["last_successful"] == {"mail": "ok@example.com", "fila": 2}
    assert data["job"]["last_attempted"] == {"mail": "mal", "fila": 3}
    assert data["job"]["last_error_message"] == "El mail 'mal' no es valido."
    assert data["job"]["attachments"][0]["nombre_original"] == "a.txt"
    assert data["job"]["attachments"][0]["url"].endswith(".txt")
    assert (data["job"]["total_rows"], data["job"]["rejected_rows"]) == (60, 1)
    assert data["is_resume_available"] is True
    assert data["resume_url"] == f"{NATIVO}lotes/{lote.pk}/reanudar/"
    assert data["upload_url"] == NATIVO
    assert len(data["rows"]) == 50 and data["page"]["next"] == 2
    segunda = web.get(f"{ROOT}jobs/{lote.pk}/", {"page": "2"}).json()
    assert [r["fila"] for r in segunda["rows"]][-1] == 99
    assert segunda["rows"][-1]["mail_destino"] == "-"
    # An invalid page is tolerated like the native ``get_page``.
    assert (
        web.get(f"{ROOT}jobs/{lote.pk}/", {"page": "zzz"}).json()["page"]["number"] == 1
    )
    assert (
        web.get(f"{ROOT}jobs/{lote.pk}/", {"page": "99"}).json()["page"]["number"] == 2
    )


def test_detail_of_another_admins_batch_is_visible_and_a_missing_one_404(web):
    ajeno = _lote(_user("ajeno_mailing", is_superuser=True))

    assert web.get(f"{ROOT}jobs/{ajeno.pk}/").status_code == 200
    assert web.get(f"{ROOT}jobs/999999/").status_code == 404
    assert web.get(f"{NATIVO}lotes/999999/").status_code == 404


def test_reads_change_nothing_and_send_nothing(web, admin):
    lote = _lote(admin)
    antes = MailingJob.objects.values().get(pk=lote.pk)

    web.get(ROOT)
    web.get(f"{ROOT}jobs/{lote.pk}/")

    assert MailingJob.objects.values().get(pk=lote.pk) == antes
    assert mail.outbox == []


def test_template_download_stays_native(web):
    respuesta = web.get(f"{NATIVO}plantilla/")

    assert respuesta.status_code == 200
    assert (
        respuesta["Content-Disposition"]
        == 'attachment; filename="plantilla_mailing.xlsx"'
    )
    assert respuesta["Content-Type"].startswith("application/vnd.openxmlformats")


# --- CM01.02 upload and resume -----------------------------------------------


def test_upload_creates_a_pending_batch_with_attachments_and_sends_nothing(web):
    respuesta = _post(
        web,
        archivos_adjuntos=[
            SimpleUploadedFile("a.pdf", b"%PDF"),
            SimpleUploadedFile("b.txt", b"b"),
        ],
    )

    assert respuesta.status_code == 200
    lote = MailingJob.objects.get()
    assert respuesta.json() == {"ok": True, "redirect": f"{NATIVO}lotes/{lote.pk}/"}
    assert lote.status == "pending"
    assert (lote.asunto, lote.cuerpo, lote.original_filename) == (
        "Asunto",
        "Cuerpo",
        "destinos.xlsx",
    )
    assert sorted(lote.attachments.values_list("nombre_original", flat=True)) == [
        "a.pdf",
        "b.txt",
    ]
    assert mail.outbox == []
    assert not MailingJobRow.objects.exists()
    detalle = web.get(f"{ROOT}jobs/{lote.pk}/").json()
    assert detalle["messages"] == [
        {
            "level": "success",
            "message": "Lote de mailing creado. El procesamiento continuará en background. "
            "Puede seguir el estado desde el detalle del lote.",
        }
    ]


def test_upload_rejections_are_400_with_the_native_messages_and_create_nothing(web):
    casos = {
        "sin_mail": (
            _xlsx(cabecera="otro"),
            "El archivo debe incluir una columna llamada 'mail'.",
        ),
        "sin_filas": (
            _xlsx(correos=()),
            "El archivo Excel no contiene filas con datos para procesar.",
        ),
        "ilegible": (
            SimpleUploadedFile("x.xlsx", b"no es un excel"),
            "No se pudo leer el archivo Excel cargado.",
        ),
    }
    for nombre, (archivo, texto) in casos.items():
        respuesta = _post(web, archivo=archivo)
        assert respuesta.status_code == 400, nombre
        campos = {f["name"]: f for f in respuesta.json()["fields"]}
        assert campos["archivo"]["errors"] == [texto], nombre
        assert campos["asunto"]["value"] == "Asunto"
    txt = _post(web, archivo=SimpleUploadedFile("x.txt", b"x"))
    assert txt.status_code == 400
    assert "extensión" in txt.json()["fields"][2]["errors"][0]
    faltan = web.post(ROOT, {"archivo": _xlsx()})
    assert faltan.status_code == 400
    assert [f["errors"] for f in faltan.json()["fields"][:2]] == [
        ["Este campo es requerido."],
        ["Este campo es requerido."],
    ]
    assert not MailingJob.objects.exists()
    assert mail.outbox == []


def test_upload_needs_admin_csrf_multipart_and_a_session(client, admin):
    comun = _client(_user("comun_subida"))
    assert client.post(ROOT).status_code == 401
    assert _post(comun).status_code == 403
    assert comun.post(ROOT, "{}", content_type="application/json").status_code == 403
    estricto = _client(admin, enforce_csrf_checks=True)
    assert estricto.post(ROOT, {"asunto": "a"}).status_code == 403
    assert (
        _client(admin).post(ROOT, "{}", content_type="application/json").status_code
        == 415
    )
    assert not MailingJob.objects.exists()


def test_resume_moves_a_failed_batch_to_pending_and_counts_it(web, admin):
    lote = _lote(
        admin,
        status=MailingJob.Status.FAILED,
        last_error_message="Error",
        last_error_at=timezone.now(),
    )

    respuesta = web.post(f"{ROOT}jobs/{lote.pk}/resume/")

    assert respuesta.status_code == 200
    assert respuesta.json() == {"ok": True, "redirect": f"{NATIVO}lotes/{lote.pk}/"}
    lote.refresh_from_db()
    assert (lote.status, lote.resume_count, lote.last_error_message) == (
        "pending",
        1,
        "",
    )
    assert web.get(f"{ROOT}jobs/{lote.pk}/").json()["messages"] == [
        {"level": "success", "message": "El lote ha sido reanudado."}
    ]
    assert mail.outbox == []


def test_resume_of_a_batch_that_is_not_failed_queues_the_native_error(web, admin):
    lote = _lote(admin, status=MailingJob.Status.COMPLETED)

    respuesta = web.post(f"{ROOT}jobs/{lote.pk}/resume/")

    assert respuesta.status_code == 200
    lote.refresh_from_db()
    assert (lote.status, lote.resume_count) == ("completed", 0)
    assert web.get(f"{ROOT}jobs/{lote.pk}/").json()["messages"] == [
        {"level": "error", "message": "Solo se pueden reanudar lotes fallidos."}
    ]


def test_resume_guards(client, admin):
    lote = _lote(admin, status=MailingJob.Status.FAILED)
    assert client.post(f"{ROOT}jobs/{lote.pk}/resume/").status_code == 401
    assert _client(admin).post(f"{ROOT}jobs/999999/resume/").status_code == 404
    estricto = _client(admin, enforce_csrf_checks=True)
    assert estricto.post(f"{ROOT}jobs/{lote.pk}/resume/").status_code == 403
    lote.refresh_from_db()
    assert (lote.status, lote.resume_count) == ("failed", 0)


# --- The worker, with the in-memory backend ----------------------------------


def test_worker_sends_once_per_row_and_a_bad_address_stops_the_batch(admin):
    lote = _lote(admin, correos=("uno@example.com", "malo", "tres@example.com"))

    process_mailing_job(lote)

    lote.refresh_from_db()
    assert [m.to for m in mail.outbox] == [["uno@example.com"]]
    assert lote.status == "failed"
    assert lote.last_attempted_row == 3
    assert "no es valido" in lote.last_error_message
    assert MailingJobRow.objects.filter(job=lote, status="failed").count() == 1

    # A resume without fixing the file fails on the same row again.
    lote.status = "pending"
    lote.save()
    process_mailing_job(lote)
    lote.refresh_from_db()
    assert lote.status == "failed"
    assert MailingJobRow.objects.get(job=lote, status="failed").attempts == 2
    assert len(mail.outbox) == 1


def test_a_claimed_batch_is_not_taken_twice(admin):
    lote = _lote(admin)

    assert claim_next_mailing_job().pk == lote.pk
    assert claim_next_mailing_job() is None
    assert mail.outbox == []
