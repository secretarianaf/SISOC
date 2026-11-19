"""Public session seams for the complete INS-B category circuit."""

from urllib.parse import urlencode

import pytest
from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APIClient

from core.models import Programa
from insumos.models import Insumo, InsumoCategoria

pytestmark = pytest.mark.django_db
ROOT = "/api/web/insumos/categorias/"


@pytest.fixture
def category_user():
    user = User.objects.create_user(username="category_session_user")
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    return user


@pytest.fixture
def catalog():
    active = Programa.objects.create(nombre="Programa activo", estado=True)
    inactive = Programa.objects.create(nombre="Programa inactivo", estado=False)
    category = InsumoCategoria.objects.create(
        programa=active, nombre="Manuales", descripcion="Orientaciones", orden=2
    )
    return active, inactive, category


def category_client(user, *actions, csrf=False):
    content_type = ContentType.objects.get_for_model(InsumoCategoria)
    user.user_permissions.add(
        *Permission.objects.filter(
            content_type=content_type,
            codename__in=[f"{action}_insumocategoria" for action in actions],
        )
    )
    client = APIClient(enforce_csrf_checks=csrf, REMOTE_ADDR="203.0.113.42")
    client.force_login(user)
    return client


def post_form(client, url, data):
    return client.post(
        url, urlencode(data), content_type="application/x-www-form-urlencoded"
    )


def test_category_list_uses_own_permission_order_and_pagination(category_user, catalog):
    active, _, _ = catalog
    for number in range(22):
        InsumoCategoria.objects.create(
            programa=active, nombre=f"Categoría {number:02}", orden=number + 3
        )
    client = category_client(category_user, "view", "add", "delete")

    response = client.get(ROOT)

    assert response.status_code == 200
    data = response.json()
    assert (data["count"], data["page"], data["page_size"], data["pages"]) == (
        23,
        1,
        20,
        2,
    )
    assert data["results"][0]["nombre"] == "Manuales"
    assert data["results"][0]["programa"] == "Programa activo"
    assert data["capabilities"] == {
        "can_add": True,
        "can_change": False,
        "can_delete": True,
    }
    assert len(client.get(ROOT, {"page": "last"}).json()["results"]) == 3
    assert client.get(ROOT, {"page": "invalid"}).status_code == 404
    assert "no-store" in response["Cache-Control"]
    assert "Cookie" in response["Vary"]


@pytest.mark.parametrize("action,suffix", [("add", "crear/"), ("change", "editar/")])
def test_category_form_choices_follow_form_without_view_permission(
    category_user, catalog, action, suffix
):
    active, inactive, category = catalog
    if action == "change":
        category.programa = inactive
        category.save()
    client = category_client(category_user, action)
    url = ROOT + (suffix if action == "add" else f"{category.pk}/{suffix}")

    response = client.get(url)

    assert response.status_code == 200
    data = response.json()
    assert set(data["initial"]) == {
        "programa",
        "nombre",
        "descripcion",
        "orden",
        "activo",
    }
    assert data["initial"]["programa"] == ("" if action == "add" else str(inactive.pk))
    assert data["initial"]["orden"] == ("0" if action == "add" else "2")
    values = [option["value"] for option in data["options"]["programa"]]
    assert str(active.pk) in values
    assert (str(inactive.pk) in values) is (action == "change")
    assert "usuario" not in data["initial"]
    assert client.get(ROOT).status_code == 403


def test_category_create_edit_and_form_errors_preserve_domain_rules(
    category_user, catalog
):
    active, _, category = catalog
    client = category_client(category_user, "add", "change")
    before = list(InsumoCategoria.objects.values())
    invalid = post_form(
        client,
        ROOT + "crear/",
        {"programa": active.pk, "nombre": "MANUALES", "orden": -1},
    )
    assert invalid.status_code == 400
    assert {"nombre", "orden"} <= set(invalid.json()["errors"])
    assert list(InsumoCategoria.objects.values()) == before

    created = post_form(
        client, ROOT + "crear/", {"programa": active.pk, "nombre": "Nueva", "orden": 0}
    )
    assert created.status_code == 200
    assert created.json() == {
        "ok": True,
        "message": "Categoría creada correctamente.",
        "redirect": "/insumos/categorias/",
    }
    new = InsumoCategoria.objects.get(nombre="Nueva")
    assert new.activo is False
    edited = post_form(
        client,
        ROOT + f"{category.pk}/editar/",
        {
            "programa": active.pk,
            "nombre": "Actualizada",
            "descripcion": "Cambio",
            "orden": 4,
            "activo": "on",
            "usuario_creacion": "999",
        },
    )
    assert edited.status_code == 200
    assert edited.json()["message"] == "Categoría actualizada correctamente."
    assert edited.json()["redirect"] == "/insumos/categorias/"
    category.refresh_from_db()
    assert (category.nombre, category.orden, category.activo) == (
        "Actualizada",
        4,
        True,
    )


def test_category_delete_sets_null_and_preserves_insumo_and_protected_file(
    category_user, catalog, tmp_path
):
    active, _, category = catalog
    client = category_client(category_user, "delete")
    with override_settings(MEDIA_ROOT=tmp_path):
        insumo = Insumo.objects.create(
            programa=active,
            categoria=category,
            titulo="Conservar",
            archivo=SimpleUploadedFile("manual.pdf", b"synthetic protected PDF"),
        )
        storage_name = insumo.archivo.name
        before = insumo.archivo.read()
        insumo.archivo.close()
        url = ROOT + f"{category.pk}/eliminar/"
        confirmation = client.get(url)
        assert confirmation.status_code == 200
        assert confirmation.json() == {"id": category.pk, "nombre": "Manuales"}
        assert InsumoCategoria.objects.filter(pk=category.pk).exists()
        deleted = post_form(client, url, {})
        assert deleted.status_code == 200
        assert deleted.json() == {
            "ok": True,
            "message": "Categoría eliminada correctamente.",
            "redirect": "/insumos/categorias/",
        }
        insumo.refresh_from_db()
        assert insumo.categoria_id is None
        assert insumo.archivo.name == storage_name
        assert insumo.archivo.read() == before
        insumo.archivo.close()


@pytest.mark.parametrize("suffix", ["", "crear/", "999/editar/", "999/eliminar/"])
def test_category_anonymous_permission_and_prerequisite_precede_objects(
    category_user, suffix
):
    url = ROOT + suffix
    anonymous = APIClient(REMOTE_ADDR="203.0.113.42")
    assert anonymous.get(url).status_code == 401
    assert anonymous.head(url).status_code == 401
    denied = category_client(category_user)
    assert denied.get(url).status_code == 403
    profile = category_user.profile
    profile.must_change_password = True
    profile.save()
    prerequisite = denied.get(url)
    assert prerequisite.status_code == 403
    assert prerequisite.json()["state"] == "password_change_required"


@pytest.mark.parametrize("method", ["put", "patch", "delete"])
def test_category_unsupported_methods_do_not_mutate(category_user, catalog, method):
    _, _, category = catalog
    client = category_client(category_user, "view", "add", "change", "delete")
    before = list(InsumoCategoria.objects.values())
    for url in [
        ROOT,
        ROOT + "crear/",
        ROOT + f"{category.pk}/editar/",
        ROOT + f"{category.pk}/eliminar/",
    ]:
        assert getattr(client, method)(url, {}).status_code == 405
    assert list(InsumoCategoria.objects.values()) == before


def test_category_csrf_missing_blocks_all_mutations(category_user, catalog):
    _, _, category = catalog
    client = category_client(category_user, "add", "change", "delete", csrf=True)
    before = list(InsumoCategoria.objects.values())
    for url in [
        ROOT + "crear/",
        ROOT + f"{category.pk}/editar/",
        ROOT + f"{category.pk}/eliminar/",
    ]:
        assert post_form(client, url, {}).status_code == 403
    assert list(InsumoCategoria.objects.values()) == before


def test_category_public_head_and_json_rejection(category_user, catalog):
    _, _, category = catalog
    client = category_client(category_user, "view", "add", "change", "delete")
    for url in [
        ROOT,
        ROOT + "crear/",
        ROOT + f"{category.pk}/editar/",
        ROOT + f"{category.pk}/eliminar/",
    ]:
        assert client.head(url).status_code == 200
        assert client.head(url).content == b""
    assert client.get(ROOT + "999/editar/").status_code == 404
    assert (
        client.post(ROOT + "crear/", {"nombre": "JSON"}, format="json").status_code
        == 415
    )


@pytest.mark.parametrize("action", ["crear", "editar", "eliminar"])
def test_category_json_transport_cannot_mutate(category_user, catalog, action):
    _, _, category = catalog
    client = category_client(category_user, "add", "change", "delete")
    url = ROOT + ("crear/" if action == "crear" else f"{category.pk}/{action}/")
    before = list(InsumoCategoria.objects.values())
    response = client.post(url, {"nombre": "Unexpected JSON"}, format="json")
    assert response.status_code == 415
    assert list(InsumoCategoria.objects.values()) == before


@pytest.mark.parametrize(
    "request_case",
    [
        (address, suffix, actor, expected)
        for address in ("127.0.0.1", "203.0.113.42")
        for suffix in ("", "crear/", "999/editar/", "999/eliminar/")
        for actor, expected in (("anonymous", 401), ("denied", 403))
    ],
)
def test_category_head_preserves_session_contract_for_all_addresses(
    category_user, catalog, request_case, settings
):
    remote_addr, suffix, actor, expected = request_case
    settings.INTERNAL_IPS = ["127.0.0.1"]
    client = APIClient(REMOTE_ADDR=remote_addr)
    if actor == "denied":
        client.force_login(category_user)
    before = list(InsumoCategoria.objects.values())
    assert any(row["id"] == catalog[2].pk for row in before)
    response = client.head(ROOT + suffix)
    assert response.status_code == expected
    assert response.content == b""
    assert "X-View" not in response
    assert "private" in response["Cache-Control"]
    assert "no-store" in response["Cache-Control"]
    if actor == "anonymous":
        assert response["WWW-Authenticate"] == "Session"
    assert list(InsumoCategoria.objects.values()) == before
