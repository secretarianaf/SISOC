"""Public session contracts for the React bulk-credentials job transport (U04)."""

import json
from datetime import datetime, timezone
from io import BytesIO

import pytest
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from openpyxl import Workbook

from users.models import BulkCredentialsJob, BulkCredentialsJobRow

pytestmark = pytest.mark.django_db
FORM = "/api/web/users/bulk-credentials/"
SECRET = "Temporal-Sintetica-7342"
BULK_CODENAME = "role_enviar_credenciales_masivas"


def job_path(pk):
    return f"{FORM}jobs/{pk}/"


def resume_path(pk):
    return f"{FORM}jobs/{pk}/resume/"


def workbook(headers=("usuario", "mail"), rows=(("destino", "otro@example.invalid"),)):
    book = Workbook()
    sheet = book.active
    sheet.append(list(headers))
    for row in rows:
        sheet.append(list(row))
    output = BytesIO()
    book.save(output)
    return SimpleUploadedFile("credenciales.xlsx", output.getvalue())


def bulk_permission():
    permission, _ = Permission.objects.get_or_create(
        content_type=ContentType.objects.get_for_model(Group),
        codename=BULK_CODENAME,
        defaults={"name": "Enviar credenciales masivas"},
    )
    return permission


def ready_user(username, *, codenames=("change_user",), bulk=True, **flags):
    user = User.objects.create_user(username=username, **flags)
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.dni = "12345678"
    profile.cuil = "20123456786"
    profile.save()
    permissions = list(
        Permission.objects.filter(
            content_type__app_label="auth", codename__in=codenames
        )
    )
    if bulk:
        permissions.append(bulk_permission())
    user.user_permissions.set(permissions)
    return user


def session(user):
    client = Client(enforce_csrf_checks=True, REMOTE_ADDR="203.0.113.43")
    client.force_login(user)
    client.get("/api/web/session/")
    return client


def csrf(client):
    return {"HTTP_X_CSRFTOKEN": client.cookies["csrftoken"].value}


def form_post(client, data):
    return client.post(FORM, data, **csrf(client))


def empty_post(client, path):
    return client.post(
        path, **csrf(client), CONTENT_TYPE="application/x-www-form-urlencoded"
    )


@pytest.fixture
def actor(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    user = ready_user("bulk_synthetic")
    return user, session(user)


def snapshot():
    return (
        list(BulkCredentialsJob.objects.order_by("pk").values()),
        list(BulkCredentialsJobRow.objects.order_by("pk").values()),
        list(User.objects.order_by("pk").values("pk", "password", "email")),
        len(mail.outbox),
    )


def make_job(owner, status=BulkCredentialsJob.Status.PENDING, rows=0, **fields):
    job = BulkCredentialsJob.objects.create(
        requested_by=owner,
        original_filename="credenciales.xlsx",
        send_type="standard",
        status=status,
        total_rows=rows,
        **fields,
    )
    for index in reversed(range(rows)):
        BulkCredentialsJobRow.objects.create(
            job=job,
            fila=index + 2,
            usuario=f"usuario{index}",
            mail_destino=f"fila{index}@example.invalid" if index % 2 else "",
            status=(
                BulkCredentialsJobRow.Status.FAILED
                if index == 1
                else BulkCredentialsJobRow.Status.SENT
            ),
            attempts=1,
            mensaje="Correo enviado.",
        )
    return job


@pytest.mark.parametrize("path", [FORM, job_path(999999), resume_path(999999)])
def test_anonymous_is_rejected_before_any_lookup(path):
    client = Client(enforce_csrf_checks=True)
    response = client.get(path)
    assert response.status_code == 401
    assert response.json()["state"] == "unauthenticated"
    assert response["Cache-Control"] == "private, no-store"


def test_unmet_prerequisite_is_reported_before_permissions(actor):
    user, client = actor
    user.profile.must_change_password = True
    user.profile.save()
    response = client.get(job_path(999999))
    assert response.status_code == 403
    assert response.json()["state"] == "password_change_required"


@pytest.mark.parametrize(
    "codenames,bulk",
    [((), True), (("change_user",), False), (("add_user",), False)],
)
def test_guard_requires_change_user_and_bulk_permission(
    settings, tmp_path, codenames, bulk
):
    settings.MEDIA_ROOT = tmp_path
    owner = ready_user("bulk_owner")
    job = make_job(owner, BulkCredentialsJob.Status.FAILED)
    client = session(ready_user("bulk_denied", codenames=codenames, bulk=bulk))
    before = snapshot()
    for path in (FORM, job_path(job.pk), job_path(999999)):
        response = client.get(path)
        assert response.status_code == 403
        assert response.json() == {"detail": "No tiene permisos para esta acción."}
    assert empty_post(client, resume_path(job.pk)).status_code == 403
    assert (
        form_post(client, {"tipo_envio": "standard", "archivo": workbook()}).status_code
        == 403
    )
    assert snapshot() == before


def test_superuser_keeps_existing_bypass(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    admin = User.objects.create_superuser(
        username="bulk_admin", email="bulk-admin@example.invalid"
    )
    profile = admin.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.dni = "12345678"
    profile.cuil = "20123456786"
    profile.save()
    assert session(admin).get(FORM).status_code == 200


def test_form_exposes_native_fields_send_types_and_only_own_history(actor):
    user, client = actor
    own = make_job(
        user,
        BulkCredentialsJob.Status.FAILED,
        last_successful_username="usuario0",
        last_successful_row=2,
        last_error_message="Fila 3: sin temporal.",
    )
    make_job(ready_user("bulk_other_owner"))
    response = client.get(FORM)
    assert response.status_code == 200
    assert response["Cache-Control"] == "private, no-store"
    assert "Cookie" in response["Vary"]
    assert "csrftoken" in response.cookies
    data = response.json()
    assert data["form_title"] == "Enviar credenciales masivas"
    assert [field["name"] for field in data["fields"]] == ["tipo_envio", "archivo"]
    tipo, archivo = data["fields"]
    assert tipo["label"] == "Tipo de envio"
    assert tipo["required"] is True
    assert tipo["choices"] == [
        {"value": "standard", "label": "Estandar"},
        {"value": "inet", "label": "INET"},
    ]
    assert archivo["accept"] == ".xlsx"
    assert archivo["required"] is True
    assert data["values"] == {"tipo_envio": "standard"}
    assert data["errors"] == {}
    assert data["template_download_url"] == "/usuarios/credenciales-masivas/plantilla/"
    assert [option["key"] for option in data["send_type_options"]] == [
        "standard",
        "inet",
    ]
    assert data["send_type_options"][1]["required_columns"] == [
        "usuario",
        "mail",
        "Nombre del Centro",
    ]
    assert [job["id"] for job in data["recent_jobs"]] == [own.pk]
    recent = data["recent_jobs"][0]
    assert recent["status"] == "failed"
    assert recent["send_type"] == "STANDARD"
    assert recent["last_successful_username"] == "usuario0"
    assert recent["last_successful_row"] == 2
    assert recent["last_error_message"] == "Fila 3: sin temporal."
    assert recent["detail_url"] == f"/usuarios/credenciales-masivas/lotes/{own.pk}/"
    assert data["presentation"]["user"]["username"] == "bulk_synthetic"


def test_missing_file_is_a_field_error_and_keeps_the_send_type(actor):
    _, client = actor
    before = snapshot()
    response = form_post(client, {"tipo_envio": "inet"})
    assert response.status_code == 400
    data = response.json()
    assert data["errors"]["archivo"][0]["message"] == "Este campo es requerido."
    assert data["values"] == {"tipo_envio": "inet"}
    assert snapshot() == before


def test_invalid_workbook_reports_the_service_error_on_the_file(actor):
    _, client = actor
    before = snapshot()
    response = form_post(
        client, {"tipo_envio": "inet", "archivo": workbook(("usuario", "mail"))}
    )
    assert response.status_code == 400
    errors = response.json()["errors"]
    assert list(errors) == ["archivo"]
    assert errors["archivo"][0]["message"] == (
        "El archivo debe incluir las columnas obligatorias: nombre_del_centro."
    )
    assert snapshot() == before


def test_valid_upload_enqueues_a_pending_job_and_redirects_to_detail(actor):
    user, client = actor
    before_mail = len(mail.outbox)
    response = form_post(client, {"tipo_envio": "standard", "archivo": workbook()})
    assert response.status_code == 200
    job = BulkCredentialsJob.objects.get()
    assert response.json() == {
        "ok": True,
        "redirect": f"/usuarios/credenciales-masivas/lotes/{job.pk}/",
    }
    assert job.requested_by == user
    assert job.send_type == "standard"
    assert job.status == BulkCredentialsJob.Status.PENDING
    assert job.original_filename == "credenciales.xlsx"
    assert job.resume_count == 0
    assert len(mail.outbox) == before_mail
    message = client.get(job_path(job.pk)).json()["messages"]
    assert message == [
        {
            "message": (
                "Lote creado para Estandar. El procesamiento continuara en "
                "background. Puede seguir el estado desde el detalle del lote."
            ),
            "level": "success",
        }
    ]
    form_post(client, {"tipo_envio": "standard", "archivo": workbook()})
    assert BulkCredentialsJob.objects.count() == 2


def test_post_requires_multipart_and_csrf(actor):
    _, client = actor
    before = snapshot()
    no_csrf = client.post(FORM, {"tipo_envio": "standard", "archivo": workbook()})
    assert no_csrf.status_code == 403
    urlencoded = client.post(
        FORM,
        "tipo_envio=standard",
        content_type="application/x-www-form-urlencoded",
        **csrf(client),
    )
    assert urlencoded.status_code == 415
    as_json = client.post(
        FORM, json.dumps({}), content_type="application/json", **csrf(client)
    )
    assert as_json.status_code == 415
    assert snapshot() == before


def test_detail_pages_fifty_rows_by_row_and_matches_native_context(actor):
    user, client = actor
    job = make_job(user, BulkCredentialsJob.Status.FAILED, rows=60)
    api = client.get(job_path(job.pk) + "?page=2").json()
    native = client.get(f"/usuarios/credenciales-masivas/lotes/{job.pk}/?page=2")
    assert native.status_code == 200
    page = native.context["page_obj"]
    assert [row["id"] for row in api["rows"]] == [row.pk for row in page]
    assert [row["fila"] for row in api["rows"]] == list(range(52, 62))
    assert api["page"] == {"number": 2, "num_pages": 2, "previous": 1, "next": None}
    assert api["is_resume_available"] is native.context["is_resume_available"] is True
    assert api["upload_url"] == native.context["upload_url"]
    first = client.get(job_path(job.pk)).json()["rows"]
    assert len(first) == 50
    assert [row["fila"] for row in first[:3]] == [2, 3, 4]
    assert set(first[0]) == {
        "id",
        "fila",
        "usuario",
        "status",
        "mail_destino",
        "attempts",
        "mensaje",
    }


def test_detail_exposes_counters_checkpoints_and_local_time(actor):
    user, client = actor
    moment = datetime(2026, 11, 6, 20, 2, tzinfo=timezone.utc)
    job = make_job(
        user,
        BulkCredentialsJob.Status.FAILED,
        rows=2,
        processed_rows=2,
        sent_rows=1,
        rejected_rows=1,
        resume_count=3,
        last_successful_username="usuario0",
        last_successful_row=2,
        last_attempted_username="usuario1",
        last_attempted_row=3,
        last_error_message="Fila 3: sin temporal.",
        last_error_at=moment,
    )
    BulkCredentialsJob.objects.filter(pk=job.pk).update(requested_at=moment)
    native = client.get(f"/usuarios/credenciales-masivas/lotes/{job.pk}/")
    assert "06/11/2026 17:02" in native.content.decode()
    data = client.get(job_path(job.pk)).json()["job"]
    assert data == {
        "id": job.pk,
        "original_filename": "credenciales.xlsx",
        "requested_at": "06/11/2026 17:02",
        "status": "failed",
        "send_type": "STANDARD",
        "resume_count": 3,
        "total_rows": 2,
        "processed_rows": 2,
        "sent_rows": 1,
        "rejected_rows": 1,
        "last_successful_username": "usuario0",
        "last_successful_row": 2,
        "last_attempted_username": "usuario1",
        "last_attempted_row": 3,
        "last_error_message": "Fila 3: sin temporal.",
        "last_error_at": "06/11/2026 17:02",
    }


def test_status_read_never_starts_or_changes_the_job(actor):
    user, client = actor
    job = make_job(user, BulkCredentialsJob.Status.PENDING, rows=3)
    before = snapshot()
    for _ in range(3):
        assert client.get(job_path(job.pk)).status_code == 200
        assert client.head(job_path(job.pk)).status_code == 200
    assert snapshot() == before


def test_detail_and_resume_are_not_limited_to_the_requester(actor):
    _, client = actor
    owner = ready_user("bulk_job_owner")
    job = make_job(owner, BulkCredentialsJob.Status.FAILED)
    assert client.get(job_path(job.pk)).status_code == 200
    assert empty_post(client, resume_path(job.pk)).status_code == 200
    job.refresh_from_db()
    assert job.status == BulkCredentialsJob.Status.PENDING
    assert client.get(job_path(999999)).status_code == 404


def test_no_password_reaches_the_dto_or_messages(actor):
    user, client = actor
    target = User.objects.create_user(
        username="destino", email="destino@example.invalid"
    )
    target.profile.temporary_password_plaintext = SECRET
    target.profile.must_change_password = True
    target.profile.save()
    job = make_job(user, BulkCredentialsJob.Status.FAILED, rows=2)
    BulkCredentialsJobRow.objects.filter(job=job).update(password_actualizada=True)
    form_post(client, {"tipo_envio": "standard", "archivo": workbook()})
    responses = [
        client.get(FORM),
        client.get(job_path(job.pk)),
        empty_post(client, resume_path(job.pk)),
        client.get(job_path(job.pk)),
    ]
    for response in responses:
        assert SECRET.encode() not in response.content
        # The shared presentation frame (menu links) is outside the job DTO.
        data = {k: v for k, v in response.json().items() if k != "presentation"}
        assert "password" not in json.dumps(data).lower()


def test_resume_moves_only_failed_jobs_back_to_pending(actor):
    user, client = actor
    failed = make_job(
        user,
        BulkCredentialsJob.Status.FAILED,
        rows=2,
        next_row_index=1,
        last_error_message="Fila 3: error.",
    )
    response = empty_post(client, resume_path(failed.pk))
    assert response.json() == {
        "ok": True,
        "redirect": f"/usuarios/credenciales-masivas/lotes/{failed.pk}/",
    }
    failed.refresh_from_db()
    assert failed.status == "pending"
    assert failed.resume_count == 1
    assert failed.next_row_index == 1
    assert client.get(job_path(failed.pk)).json()["messages"] == [
        {
            "message": "El lote quedo pendiente para reanudarse desde la ultima fila fallida.",
            "level": "success",
        }
    ]


def test_resume_of_a_non_failed_job_reports_error_without_changes(actor):
    user, client = actor
    job = make_job(user, BulkCredentialsJob.Status.COMPLETED)
    before = snapshot()
    response = empty_post(client, resume_path(job.pk))
    assert response.json()["ok"] is True
    assert snapshot() == before
    messages = client.get(job_path(job.pk)).json()["messages"]
    assert [m["level"] for m in messages] == ["error"]


def test_resume_accepts_only_post(actor):
    user, client = actor
    job = make_job(user, BulkCredentialsJob.Status.FAILED)
    assert client.get(resume_path(job.pk)).status_code == 405
    assert client.put(resume_path(job.pk), **csrf(client)).status_code == 405
    job.refresh_from_db()
    assert job.status == "failed"


def test_internal_head_returns_private_json_without_admindocs_header(actor):
    user, client = actor
    job = make_job(user)
    for path in (FORM, job_path(job.pk)):
        response = client.head(path, REMOTE_ADDR="127.0.0.1")
        assert response.status_code == 200
        assert "X-View" not in response
        assert response["Content-Type"] == "application/json"
