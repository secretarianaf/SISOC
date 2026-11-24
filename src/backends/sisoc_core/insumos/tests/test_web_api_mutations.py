"""HTTP seams for the session-only INS-A form and mutation API."""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from rest_framework.test import APIClient

from core.models import Programa
from insumos.models import Insumo, InsumoCategoria


@pytest.fixture
def api_user(db):
    user = User.objects.create_user(
        username="mutation_reader", first_name="Persona Sintética"
    )
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    return user


def grant(user, codename):
    content_type = ContentType.objects.get_for_model(Insumo)
    permission = Permission.objects.get(content_type=content_type, codename=codename)
    user.user_permissions.add(permission)


@pytest.fixture
def form_catalog(db):
    active_program = Programa.objects.create(nombre="Programa activo", estado=True)
    inactive_program = Programa.objects.create(nombre="Programa pausado", estado=False)
    active_category = InsumoCategoria.objects.create(
        programa=active_program, nombre="Manuales activos", activo=True, orden=2
    )
    inactive_category = InsumoCategoria.objects.create(
        programa=active_program, nombre="Manuales pausados", activo=False, orden=1
    )
    return active_program, inactive_program, active_category, inactive_category


def test_create_form_metadata_uses_the_actual_form_choices_without_view_permission(
    api_user, form_catalog
):
    active_program, inactive_program, active_category, inactive_category = form_catalog
    grant(api_user, "add_insumo")
    client = APIClient()
    client.force_login(api_user)

    response = client.get("/api/web/insumos/crear/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["initial"] == {
        "programa": "",
        "categoria": "",
        "titulo": "",
        "descripcion": "",
        "activo": True,
    }
    assert payload["options"]["programa"] == [
        {"value": "", "label": "---------"},
        {"value": str(active_program.pk), "label": "Programa activo"},
    ]
    assert payload["options"]["categoria"] == [
        {"value": "", "label": "Sin categoría"},
        {
            "value": str(active_category.pk),
            "label": "Manuales activos",
            "programa_id": str(active_program.pk),
        },
    ]
    assert payload["current_file"] is None
    assert inactive_program.pk not in [
        int(option["value"])
        for option in payload["options"]["programa"]
        if option["value"]
    ]
    assert inactive_category.pk not in [
        int(option["value"])
        for option in payload["options"]["categoria"]
        if option["value"]
    ]
    assert "usuario_creacion" not in payload["initial"]
    assert "archivo" not in payload["initial"]


def test_create_rejects_invalid_form_without_persisting(
    api_user, form_catalog, tmp_path
):
    grant(api_user, "add_insumo")
    client = APIClient()
    client.force_login(api_user)

    upload = SimpleUploadedFile(
        "manual.pdf", b"synthetic pdf", content_type="application/pdf"
    )
    with override_settings(MEDIA_ROOT=tmp_path):
        response = client.post(
            "/api/web/insumos/crear/", {"archivo": upload}, format="multipart"
        )

    assert response.status_code == 400
    assert set(response.json()["errors"]) >= {"programa", "titulo"}
    assert Insumo.objects.count() == 0
    assert list(tmp_path.iterdir()) == []


def test_create_persists_uploaded_file_and_omitted_active_checkbox_as_false(
    api_user, form_catalog, tmp_path
):
    active_program, _, active_category, _ = form_catalog
    grant(api_user, "add_insumo")
    client = APIClient()
    client.force_login(api_user)
    upload = SimpleUploadedFile(
        "manual.pdf", b"synthetic pdf", content_type="application/pdf"
    )

    with override_settings(MEDIA_ROOT=tmp_path):
        response = client.post(
            "/api/web/insumos/crear/",
            {
                "programa": str(active_program.pk),
                "categoria": str(active_category.pk),
                "titulo": "Manual sintético",
                "descripcion": "Contenido de prueba",
                "archivo": upload,
            },
            format="multipart",
        )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "message": "Insumo creado correctamente.",
        "redirect": "/insumos/",
    }
    item = Insumo.objects.get(titulo="Manual sintético")
    assert item.activo is False
    assert item.usuario_creacion_id == api_user.pk
    assert item.archivo.name.endswith(".pdf")


def test_edit_metadata_retains_inactive_current_choices_without_view_link(
    api_user, form_catalog
):
    _, inactive_program, _, _ = form_catalog
    inactive_category = InsumoCategoria.objects.create(
        programa=inactive_program, nombre="Manuales pausados", activo=False, orden=1
    )
    grant(api_user, "change_insumo")
    item = Insumo.objects.create(
        programa=inactive_program,
        categoria=inactive_category,
        titulo="Manual existente",
        descripcion="Descripción previa",
        archivo="insumos/manual.pdf",
        activo=True,
        usuario_creacion=api_user,
    )
    client = APIClient()
    client.force_login(api_user)

    response = client.get(f"/api/web/insumos/{item.pk}/editar/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["initial"]["programa"] == str(inactive_program.pk)
    assert payload["initial"]["categoria"] == str(inactive_category.pk)
    assert payload["initial"]["activo"] is True
    assert {
        "value": str(inactive_program.pk),
        "label": "Programa pausado",
    } in payload[
        "options"
    ]["programa"]
    assert {
        "value": str(inactive_category.pk),
        "label": "Manuales pausados",
        "programa_id": str(inactive_program.pk),
    } in payload["options"]["categoria"]
    assert payload["current_file"] == {"name": "manual.pdf", "download_url": None}


def test_edit_without_replacement_preserves_file_and_omitted_active_is_false(
    api_user, form_catalog, tmp_path
):
    active_program, _, active_category, _ = form_catalog
    grant(api_user, "change_insumo")
    item = Insumo.objects.create(
        programa=active_program,
        categoria=active_category,
        titulo="Manual previo",
        descripcion="Texto previo",
        archivo="insumos/manual-previo.pdf",
        activo=True,
        usuario_creacion=api_user,
    )
    existing_path = tmp_path / "insumos" / "manual-previo.pdf"
    existing_path.parent.mkdir(parents=True)
    existing_path.write_bytes(b"synthetic existing file")
    client = APIClient()
    client.force_login(api_user)

    with override_settings(MEDIA_ROOT=tmp_path):
        response = client.post(
            f"/api/web/insumos/{item.pk}/editar/",
            {
                "programa": str(active_program.pk),
                "categoria": str(active_category.pk),
                "titulo": "Manual actualizado",
                "descripcion": "Texto nuevo",
            },
            format="multipart",
        )

    assert response.status_code == 200
    item.refresh_from_db()
    assert item.titulo == "Manual actualizado"
    assert item.archivo.name == "insumos/manual-previo.pdf"
    assert item.activo is False


def test_edit_replaces_file_through_multipart_form(api_user, form_catalog, tmp_path):
    active_program, _, active_category, _ = form_catalog
    grant(api_user, "change_insumo")
    item = Insumo.objects.create(
        programa=active_program,
        categoria=active_category,
        titulo="Manual a reemplazar",
        descripcion="",
        archivo="insumos/antiguo.pdf",
        activo=True,
        usuario_creacion=api_user,
    )
    client = APIClient()
    client.force_login(api_user)
    replacement = SimpleUploadedFile(
        "nuevo.pdf", b"synthetic replacement", content_type="application/pdf"
    )

    with override_settings(MEDIA_ROOT=tmp_path):
        response = client.post(
            f"/api/web/insumos/{item.pk}/editar/",
            {
                "programa": str(active_program.pk),
                "categoria": str(active_category.pk),
                "titulo": "Manual reemplazado",
                "descripcion": "",
                "activo": "on",
                "archivo": replacement,
            },
            format="multipart",
        )

    assert response.status_code == 200
    item.refresh_from_db()
    assert item.titulo == "Manual reemplazado"
    assert item.activo is True
    assert item.archivo.name.endswith("nuevo.pdf")


def test_delete_confirmation_is_non_mutating_and_delete_permission_needs_no_view(
    api_user, form_catalog
):
    active_program, _, active_category, _ = form_catalog
    grant(api_user, "delete_insumo")
    item = Insumo.objects.create(
        programa=active_program,
        categoria=active_category,
        titulo="Manual a eliminar",
        descripcion="",
        archivo="insumos/eliminar.pdf",
        activo=True,
        usuario_creacion=api_user,
    )
    client = APIClient()
    client.force_login(api_user)

    confirmation = client.get(f"/api/web/insumos/{item.pk}/eliminar/")
    assert confirmation.status_code == 200
    assert confirmation.json() == {"id": item.pk, "titulo": "Manual a eliminar"}
    assert Insumo.objects.filter(pk=item.pk).exists()

    response = client.post(
        f"/api/web/insumos/{item.pk}/eliminar/", {}, format="multipart"
    )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "message": "Insumo eliminado correctamente.",
        "redirect": "/insumos/",
    }
    assert not Insumo.objects.filter(pk=item.pk).exists()


def test_view_permission_does_not_grant_create_and_session_post_requires_csrf(
    api_user, form_catalog
):
    grant(api_user, "view_insumo")
    client = APIClient()
    client.force_login(api_user)

    denied = client.get("/api/web/insumos/crear/")
    assert denied.status_code == 403

    grant(api_user, "add_insumo")
    csrf_client = APIClient(enforce_csrf_checks=True)
    csrf_client.force_login(api_user)
    rejected = csrf_client.post("/api/web/insumos/crear/", {}, format="multipart")

    assert rejected.status_code == 403
    assert Insumo.objects.count() == 0


@pytest.mark.parametrize(
    "path",
    [
        "/api/web/insumos/crear/",
        "/api/web/insumos/999/editar/",
        "/api/web/insumos/999/eliminar/",
    ],
)
def test_view_permission_does_not_grant_action_form_access(api_user, path):
    grant(api_user, "view_insumo")
    client = APIClient()
    client.force_login(api_user)

    response = client.get(path)

    assert response.status_code == 403


def test_anonymous_and_unready_sessions_cannot_read_form_metadata(api_user):
    assert APIClient().get("/api/web/insumos/crear/").status_code == 401
    grant(api_user, "add_insumo")
    api_user.profile.acceso_web = False
    api_user.profile.save(update_fields=["acceso_web"])
    client = APIClient()
    client.force_login(api_user)

    response = client.get("/api/web/insumos/crear/")

    assert response.status_code == 403
    assert response.json()["state"] == "web_access_denied"


def test_delete_storage_failure_is_not_reported_as_success(
    api_user, form_catalog, monkeypatch
):
    active_program, _, active_category, _ = form_catalog
    grant(api_user, "delete_insumo")
    item = Insumo.objects.create(
        programa=active_program,
        categoria=active_category,
        titulo="Manual con borrado parcial",
        descripcion="",
        archivo="insumos/borrado-parcial.pdf",
        activo=True,
        usuario_creacion=api_user,
    )
    client = APIClient()
    client.force_login(api_user)
    calls = []

    def partial_failure(instance):
        calls.append(instance.pk)
        instance.delete()
        raise OSError("synthetic storage failure")

    monkeypatch.setattr("insumos.web_api_views.delete_insumo", partial_failure)
    client.raise_request_exception = False

    response = client.post(
        f"/api/web/insumos/{item.pk}/eliminar/", {}, format="multipart"
    )

    assert response.status_code == 500
    assert response.json().get("ok") is not True
    assert calls == [item.pk]
    assert not Insumo.objects.filter(pk=item.pk).exists()


def test_head_reaches_all_mutation_routes_for_internal_staff(api_user, form_catalog):
    active_program, _, active_category, _ = form_catalog
    api_user.is_staff = True
    api_user.save(update_fields=["is_staff"])
    for codename in ("add_insumo", "change_insumo", "delete_insumo"):
        grant(api_user, codename)
    item = Insumo.objects.create(
        programa=active_program,
        categoria=active_category,
        titulo="Manual HEAD",
        descripcion="",
        archivo="insumos/head.pdf",
        activo=True,
        usuario_creacion=api_user,
    )
    client = APIClient()
    client.force_login(api_user)
    paths = (
        "/api/web/insumos/crear/",
        f"/api/web/insumos/{item.pk}/editar/",
        f"/api/web/insumos/{item.pk}/eliminar/",
    )

    with override_settings(INTERNAL_IPS=["127.0.0.1"]):
        responses = [client.head(path, REMOTE_ADDR="127.0.0.1") for path in paths]

    assert [response.status_code for response in responses] == [200, 200, 200]
    assert all(response.content == b"" for response in responses)
    assert all("X-View" not in response for response in responses)


def test_head_xview_exemption_preserves_anonymous_and_denied_api_auth(api_user):
    api_user.is_staff = True
    api_user.save(update_fields=["is_staff"])
    client = APIClient()
    denied_staff_client = APIClient()
    denied_staff_client.force_login(api_user)

    with override_settings(INTERNAL_IPS=["127.0.0.1"]):
        anonymous = client.head("/api/web/insumos/crear/", REMOTE_ADDR="127.0.0.1")
        denied_staff = denied_staff_client.head(
            "/api/web/insumos/crear/", REMOTE_ADDR="127.0.0.1"
        )

    assert anonymous.status_code == 401
    assert "X-View" not in anonymous
    assert denied_staff.status_code == 403
    assert "X-View" not in denied_staff


def test_openapi_documents_typed_mutation_multipart_success_and_form_errors():
    from django.urls import include, path
    from drf_spectacular.generators import SchemaGenerator

    schema = SchemaGenerator(
        patterns=[path("api/web/insumos/", include("insumos.web_api_urls"))]
    ).get_schema(request=None, public=True)

    for route in (
        "/api/web/insumos/crear/",
        "/api/web/insumos/{id}/editar/",
        "/api/web/insumos/{id}/eliminar/",
    ):
        operations = schema["paths"][route]
        assert operations["get"]["security"] == [{"cookieAuth": []}]
        assert operations["get"]["responses"]["200"]["content"]
        assert operations["post"]["security"] == [{"cookieAuth": []}]
        assert operations["post"]["responses"]["200"]["content"]

    for route in ("/api/web/insumos/crear/", "/api/web/insumos/{id}/editar/"):
        post = schema["paths"][route]["post"]
        assert "400" in post["responses"]
        assert post["responses"]["400"]["content"]["application/json"]["schema"][
            "$ref"
        ].endswith("/InsumoFormErrors")
        request = post["requestBody"]["content"]["multipart/form-data"]
        assert request["schema"]["$ref"]
        assert post["responses"]["200"]["content"]["application/json"]["schema"][
            "$ref"
        ].endswith("/InsumoMutationSuccess")

    create_request = schema["components"]["schemas"]["InsumoCreateRequest"]
    edit_request = schema["components"]["schemas"]["InsumoEditRequest"]
    assert create_request["properties"]["archivo"] == {
        "type": "string",
        "format": "binary",
    }
    assert "archivo" in create_request["required"]
    assert "activo" not in create_request["required"]
    assert "archivo" not in edit_request["required"]
    assert "activo" not in edit_request["required"]

    delete_get = schema["paths"]["/api/web/insumos/{id}/eliminar/"]["get"]
    assert delete_get["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/InsumoDeleteConfirmation")


def test_mutation_api_rejects_json_upload_transport(api_user):
    grant(api_user, "add_insumo")
    client = APIClient()
    client.force_login(api_user)

    response = client.post(
        "/api/web/insumos/crear/",
        {"programa": "1", "titulo": "No JSON upload", "archivo": "base64-data"},
        format="json",
    )

    assert response.status_code == 415
    assert Insumo.objects.count() == 0
