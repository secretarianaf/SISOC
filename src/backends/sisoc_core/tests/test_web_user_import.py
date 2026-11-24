"""Public session contracts for the React user-import job transport (U05)."""

import json
from datetime import datetime, timezone
from io import BytesIO

import pytest
from django.contrib.auth.models import Permission, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from openpyxl import Workbook

from users.models import UserImportJob, UserImportJobRow

pytestmark = pytest.mark.django_db
FORM = "/api/web/users/import/"
SECRET = "Temporal-Sintetica-4821"


def job_path(pk):
    return f"{FORM}jobs/{pk}/"


def resume_path(pk):
    return f"{FORM}jobs/{pk}/resume/"


def workbook(rows=(("Ana", "Prueba", "Grupo", "CABA", "TERRITORIAL"),)):
    book = Workbook()
    sheet = book.active
    sheet.title = "usuarios"
    sheet.append(["Nombre", "Apellido", "Permisos", "Provincias", "Rol"])
    for row in rows:
        sheet.append(list(row))
    output = BytesIO()
    book.save(output)
    return SimpleUploadedFile("usuarios.xlsx", output.getvalue())


def ready_user(username, *, codenames=("add_user",), **flags):
    user = User.objects.create_user(username=username, **flags)
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.dni = "12345678"
    profile.cuil = "20123456786"
    profile.save()
    user.user_permissions.set(
        Permission.objects.filter(
            content_type__app_label="auth", codename__in=codenames
        )
    )
    return user


def session(user):
    client = Client(enforce_csrf_checks=True, REMOTE_ADDR="203.0.113.42")
    client.force_login(user)
    client.get("/api/web/session/")
    return client


def csrf(client):
    return {"HTTP_X_CSRFTOKEN": client.cookies["csrftoken"].value}


@pytest.fixture
def actor(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    user = ready_user("import_synthetic")
    return user, session(user)


def snapshot():
    return (
        list(UserImportJob.objects.order_by("pk").values()),
        list(UserImportJobRow.objects.order_by("pk").values()),
        User.objects.count(),
    )


def make_job(owner, status=UserImportJob.Status.PENDING, rows=0, **fields):
    job = UserImportJob.objects.create(
        requested_by=owner,
        original_filename="usuarios.xlsx",
        status=status,
        total_rows=rows,
        **fields,
    )
    for index in reversed(range(rows)):
        UserImportJobRow.objects.create(
            job=job,
            fila=index + 2,
            nombre=f"Nombre{index}",
            apellido="Prueba",
            email=f"fila{index}@example.invalid",
            status=(
                UserImportJobRow.Status.FAILED
                if index % 2
                else UserImportJobRow.Status.PENDING
            ),
        )
    return job


@pytest.mark.parametrize("path", [FORM, job_path(999999), resume_path(999999)])
def test_anonymous_is_rejected_before_any_lookup(path):
    before = snapshot()
    client = Client()
    assert client.get(path).status_code == 401
    assert client.post(path).status_code == 401
    assert snapshot() == before


def test_unmet_prerequisite_is_reported_before_permissions(actor):
    user, client = actor
    user.profile.must_change_password = True
    user.profile.save()
    response = client.get(FORM)
    assert response.status_code == 403
    assert response.json()["state"] == "password_change_required"
    assert response.json()["required_action_url"] == "/password/first-change/"


@pytest.mark.parametrize("method", ["get", "post"])
def test_guard_requires_add_user_before_job_lookup(settings, tmp_path, method):
    settings.MEDIA_ROOT = tmp_path
    owner = ready_user("import_owner_guard")
    job = make_job(owner, UserImportJob.Status.FAILED)
    client = session(ready_user("import_viewer", codenames=("view_user",)))
    before = snapshot()
    for path in (FORM, job_path(job.pk), resume_path(job.pk)):
        response = getattr(client, method)(path, **csrf(client))
        assert response.status_code == 403
        assert response.json() == {"detail": "No tiene permisos para esta acción."}
    assert snapshot() == before


def test_superuser_keeps_existing_bypass(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    admin = ready_user("import_super", codenames=(), is_superuser=True)
    client = session(admin)
    assert client.get(FORM).status_code == 200


def test_form_exposes_native_fields_initials_and_only_own_history(actor):
    user, client = actor
    own = make_job(user, UserImportJob.Status.COMPLETED, created_rows=2)
    make_job(ready_user("import_other_owner"))
    response = client.get(FORM)
    assert response.status_code == 200
    assert response["Cache-Control"] == "private, no-store"
    assert "Cookie" in response["Vary"]
    data = response.json()
    assert [field["name"] for field in data["fields"]] == [
        "archivo",
        "enviar_credenciales",
        "es_pwa",
    ]
    assert data["fields"][0]["label"] == "Archivo Excel"
    assert data["fields"][0]["accept"] == ".xlsx"
    assert data["fields"][0]["required"] is True
    assert data["initial"] == {"enviar_credenciales": True, "es_pwa": False}
    assert data["errors"] == {}
    assert data["template_download_url"] == "/usuarios/importar/plantilla/"
    assert [job["id"] for job in data["recent_jobs"]] == [own.pk]
    assert data["recent_jobs"][0]["status"] == "completed"
    assert data["recent_jobs"][0]["created_rows"] == 2
    assert data["recent_jobs"][0]["detail_url"] == f"/usuarios/importar/lotes/{own.pk}/"
    assert data["presentation"]["user"]["username"] == "import_synthetic"


def test_missing_file_is_a_field_error_without_writes(actor):
    _, client = actor
    before = snapshot()
    response = client.post(FORM, {"enviar_credenciales": "on"}, **csrf(client))
    assert response.status_code == 400
    data = response.json()
    assert data["errors"]["archivo"][0]["message"] == "Este campo es requerido."
    assert data["initial"] == {"enviar_credenciales": True, "es_pwa": False}
    assert snapshot() == before


def test_invalid_workbook_reports_the_service_error_on_the_file(actor):
    _, client = actor
    before = snapshot()
    broken = SimpleUploadedFile("usuarios.xlsx", b"not a workbook")
    response = client.post(FORM, {"archivo": broken, "es_pwa": "on"}, **csrf(client))
    assert response.status_code == 400
    data = response.json()
    assert data["errors"]["archivo"][0]["message"] == (
        "No se pudo leer el archivo Excel cargado."
    )
    assert data["initial"] == {"enviar_credenciales": False, "es_pwa": True}
    assert snapshot() == before


def test_valid_upload_enqueues_pending_rows_and_redirects_to_detail(actor):
    user, client = actor
    users_before = User.objects.count()
    response = client.post(
        FORM,
        {"archivo": workbook(), "enviar_credenciales": "on"},
        **csrf(client),
    )
    job = UserImportJob.objects.get()
    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "redirect": f"/usuarios/importar/lotes/{job.pk}/",
    }
    assert job.requested_by == user
    assert job.status == UserImportJob.Status.PENDING
    assert job.send_credentials is True
    assert job.is_pwa_import is False
    assert job.total_rows == 1
    assert job.started_at is None
    assert list(job.rows.values_list("fila", "nombre", "status")) == [
        (2, "Ana", "pending")
    ]
    assert User.objects.count() == users_before
    detail = client.get(job_path(job.pk)).json()
    assert detail["messages"] == [
        {
            "message": (
                "Lote de importacion creado con 1 filas. El procesamiento continua "
                "en background. Puede seguir el estado desde el detalle del lote."
            ),
            "level": "success",
        }
    ]
    assert client.get(job_path(job.pk)).json()["messages"] == []


def test_repeating_the_upload_creates_another_job(actor):
    _, client = actor
    for _ in range(2):
        response = client.post(FORM, {"archivo": workbook()}, **csrf(client))
        assert response.status_code == 200
    assert UserImportJob.objects.count() == 2


def test_post_requires_multipart_and_csrf(actor):
    _, client = actor
    before = snapshot()
    assert (
        client.post(
            FORM,
            "enviar_credenciales=on",
            content_type="application/x-www-form-urlencoded",
            **csrf(client),
        ).status_code
        == 415
    )
    assert client.post(FORM, {"archivo": workbook()}).status_code == 403
    assert snapshot() == before


def test_detail_pages_fifty_rows_by_row_and_keeps_status_filter(actor):
    user, client = actor
    job = make_job(user, rows=120)
    first = client.get(job_path(job.pk)).json()
    assert [row["fila"] for row in first["rows"]] == list(range(2, 52))
    assert first["page"] == {"number": 1, "num_pages": 3, "previous": None, "next": 2}
    third = client.get(job_path(job.pk) + "?page=3").json()
    assert [row["fila"] for row in third["rows"]] == list(range(102, 122))
    filtered = client.get(job_path(job.pk) + "?estado=failed&page=2").json()
    assert filtered["status_filter"] == "failed"
    assert filtered["page"]["number"] == 2
    assert {row["status"] for row in filtered["rows"]} == {"failed"}
    assert set(filtered["rows"][0]) == {
        "id",
        "fila",
        "nombre",
        "apellido",
        "email",
        "status",
        "attempts",
        "mensaje",
    }


def test_detail_matches_native_context(actor):
    user, client = actor
    job = make_job(
        user,
        UserImportJob.Status.FAILED,
        rows=60,
        last_error_message="Fila 3: rol inexistente.",
    )
    api = client.get(job_path(job.pk) + "?estado=pending&page=2").json()
    native = client.get(f"/usuarios/importar/lotes/{job.pk}/?estado=pending&page=2")
    assert native.status_code == 200
    page = native.context["page_obj"]
    assert [row["id"] for row in api["rows"]] == [row.pk for row in page]
    assert api["page"]["num_pages"] == page.paginator.num_pages
    assert api["is_resume_available"] is native.context["is_resume_available"] is True
    assert api["job"]["last_error_message"] == "Fila 3: rol inexistente."
    assert api["upload_url"] == native.context["upload_url"]


def test_timestamps_render_in_the_native_local_time(actor):
    user, client = actor
    moment = datetime(2026, 11, 6, 20, 2, tzinfo=timezone.utc)
    job = make_job(
        user,
        UserImportJob.Status.FAILED,
        last_error_message="Fila 2: rol inexistente.",
        last_error_at=moment,
    )
    UserImportJob.objects.filter(pk=job.pk).update(requested_at=moment)
    native = client.get(f"/usuarios/importar/lotes/{job.pk}/").content.decode()
    assert "06/11/2026 17:02" in native
    assert "06/11/2026 20:02" not in native
    form = client.get(FORM).json()
    assert form["recent_jobs"][0]["requested_at"] == "06/11/2026 17:02"
    detail = client.get(job_path(job.pk)).json()["job"]
    assert detail["requested_at"] == "06/11/2026 17:02"
    assert detail["last_error_at"] == "06/11/2026 17:02"


def test_status_read_never_starts_or_changes_the_job(actor):
    user, client = actor
    job = make_job(user, rows=3)
    before = snapshot()
    for _ in range(3):
        assert client.get(job_path(job.pk)).status_code == 200
    assert snapshot() == before
    job.refresh_from_db()
    assert job.status == "pending"
    assert job.lease_token is None
    assert job.started_at is None


def test_detail_is_visible_to_other_importers_but_missing_job_is_404(actor):
    _, client = actor
    other = make_job(ready_user("import_detail_owner"))
    assert client.get(job_path(other.pk)).status_code == 200
    assert client.get(job_path(999999)).status_code == 404


def test_csv_link_points_to_native_endpoint_and_dto_carries_no_password(
    actor, settings, tmp_path
):
    user, client = actor
    created = User.objects.create_user(username="importado.sintetico")
    created.profile.must_change_password = True
    created.profile.temporary_password_plaintext = SECRET
    created.profile.save()
    job = make_job(user, UserImportJob.Status.COMPLETED)
    UserImportJobRow.objects.create(
        job=job,
        created_user=created,
        fila=2,
        nombre="Importado",
        status=UserImportJobRow.Status.CREATED,
        mensaje="Usuario creado.",
    )
    detail = client.get(job_path(job.pk))
    csv_url = f"/usuarios/importar/lotes/{job.pk}/descargar-csv/"
    assert detail.json()["csv_url"] == csv_url
    form = client.get(FORM)
    for response in (detail, form):
        assert SECRET not in response.content.decode()
    assert SECRET in client.get(csv_url).content.decode("utf-8-sig")
    observer = session(ready_user("import_csv_observer"))
    assert observer.get(job_path(job.pk)).json()["csv_url"] == csv_url
    assert observer.get(csv_url).status_code == 404


def test_csv_link_is_absent_without_created_users(actor):
    user, client = actor
    job = make_job(user, rows=2)
    assert client.get(job_path(job.pk)).json()["csv_url"] is None


def test_resume_moves_only_failed_jobs_back_to_pending(actor):
    user, client = actor
    failed = make_job(
        user,
        UserImportJob.Status.FAILED,
        rows=2,
        next_row_index=1,
        last_error_message="Fila 3: error.",
    )
    response = client.post(
        resume_path(failed.pk),
        **csrf(client),
        CONTENT_TYPE="application/x-www-form-urlencoded",
    )
    assert response.json() == {
        "ok": True,
        "redirect": f"/usuarios/importar/lotes/{failed.pk}/",
    }
    failed.refresh_from_db()
    assert failed.status == "pending"
    assert failed.resume_count == 1
    assert failed.next_row_index == 1
    assert failed.last_error_message == ""
    assert client.get(job_path(failed.pk)).json()["messages"] == [
        {
            "message": "El lote quedo pendiente para reanudarse desde la ultima fila fallida.",
            "level": "success",
        }
    ]


def test_resume_of_a_non_failed_job_reports_error_without_changes(actor):
    user, client = actor
    job = make_job(user, UserImportJob.Status.PROCESSING)
    before = snapshot()
    response = client.post(
        resume_path(job.pk),
        **csrf(client),
        CONTENT_TYPE="application/x-www-form-urlencoded",
    )
    assert response.json()["ok"] is True
    assert snapshot() == before
    assert client.get(job_path(job.pk)).json()["messages"] == [
        {"message": "Solo se pueden reanudar lotes fallidos.", "level": "error"}
    ]


def test_resume_accepts_only_post(actor):
    user, client = actor
    job = make_job(user, UserImportJob.Status.FAILED)
    assert client.get(resume_path(job.pk)).status_code == 405
    job.refresh_from_db()
    assert job.status == "failed"
    assert json.loads(client.get(job_path(job.pk)).content)["is_resume_available"]


def test_internal_head_returns_private_json_without_admindocs_header(
    settings, tmp_path
):
    settings.MEDIA_ROOT = tmp_path
    settings.INTERNAL_IPS = ["127.0.0.1"]
    user = ready_user("import_head", is_staff=True)
    job = make_job(user, UserImportJob.Status.FAILED)
    client = Client(REMOTE_ADDR="127.0.0.1")
    client.force_login(user)
    before = snapshot()
    for path in (FORM, job_path(job.pk)):
        response = client.head(path)
        assert response.status_code == 200
        assert response.content == b""
        assert "X-View" not in response
        assert response["Content-Type"].startswith("application/json")
        assert "no-store" in response["Cache-Control"]
    assert client.head(resume_path(job.pk)).status_code == 405
    assert "X-View" not in client.head(resume_path(job.pk))
    assert snapshot() == before
