"""Public session contracts for the React user list and its (de)activation steps."""

import hashlib
import json
from urllib.parse import urlencode

import pytest
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.test import Client

pytestmark = pytest.mark.django_db
LIST = "/api/web/users/list/"


def deactivate(user_id):
    return f"/api/web/users/{user_id}/deactivate/"


def activate(user_id):
    return f"/api/web/users/{user_id}/activate/"


def digest():
    return hashlib.sha256(
        repr(
            [
                list(User.objects.order_by("pk").values()),
                list(User.groups.through.objects.order_by("pk").values()),
                list(User.user_permissions.through.objects.order_by("pk").values()),
            ]
        ).encode()
    ).hexdigest()


def ready(user, perms):
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.dni = "12345678"
    profile.cuil = "20123456786"
    profile.save()
    user.user_permissions.set(
        Permission.objects.filter(content_type__app_label="auth", codename__in=perms)
    )
    client = Client(enforce_csrf_checks=True, REMOTE_ADDR="203.0.113.42")
    client.force_login(user)
    client.get("/api/web/session/")
    return client


def make_actor(username, perms, delegated=()):
    user = User.objects.create_user(username=username)
    for group in delegated:
        user.profile.grupos_asignables.add(group)
    return user, ready(user, perms)


@pytest.fixture
def manager():
    """May list, change state, and manage the members of the delegated group."""
    group = Group.objects.create(name="Delegado sintetico")
    user, client = make_actor(
        "manager_synthetic", ["view_user", "delete_user"], delegated=[group]
    )
    return user, client, group


def post(client, path, data=None, csrf=True):
    headers = {"HTTP_X_CSRFTOKEN": client.cookies["csrftoken"].value} if csrf else {}
    return client.post(
        path,
        urlencode(data or {}, doseq=True),
        content_type="application/x-www-form-urlencoded",
        **headers,
    )


def member(username, group, **extra):
    user = User.objects.create_user(username=username, **extra)
    user.groups.add(group)
    return user


@pytest.mark.parametrize("path", [LIST, deactivate(999999), activate(999999)])
def test_anonymous_is_rejected_before_object_lookup(path):
    before = digest()
    assert Client().get(path).status_code == 401
    assert digest() == before


def test_pending_prerequisite_blocks_every_endpoint(manager):
    user, client, group = manager
    target = member("pending_target", group)
    profile = user.profile
    profile.must_change_password = True
    profile.save()
    before = digest()
    for path in (LIST, deactivate(target.pk), activate(target.pk)):
        response = client.get(path)
        assert response.status_code == 403
        assert response.json()["required_action_url"] == "/password/first-change/"
    assert post(client, deactivate(target.pk)).status_code == 403
    assert digest() == before


def test_view_permission_alone_cannot_change_state():
    group = Group.objects.create(name="Delegado sintetico")
    user, client = make_actor("viewer_only", ["view_user"], delegated=[group])
    target = member("viewer_target", group)
    before = digest()
    assert client.get(LIST).status_code == 200
    for path in (deactivate(target.pk), activate(target.pk)):
        assert client.get(path).status_code == 403
        assert post(client, path).status_code == 403
    assert digest() == before
    assert user.pk != target.pk


def test_state_permission_alone_cannot_list():
    _, client = make_actor("state_only", ["delete_user"])
    before = digest()
    assert client.get(LIST).status_code == 403
    assert digest() == before


def test_list_without_delegation_shows_only_the_actor(manager):
    user, _, group = manager
    member("scoped_member", group)
    User.objects.create_user(username="outsider_synthetic")
    _, client = make_actor("lonely_viewer", ["view_user"])
    data = client.get(LIST).json()
    assert [row["id"] for row in data["results"]] == [
        User.objects.get(username="lonely_viewer").pk
    ]
    assert user.pk not in [row["id"] for row in data["results"]]


def test_list_projects_native_cells_actions_and_columns(manager):
    user, client, group = manager
    target = member("scoped_target", group, first_name="Ana", last_name="Pérez")
    target.profile.rol = "Rol sintetico"
    target.profile.save()
    inactive = member("scoped_inactive", group)
    inactive.is_active = False
    inactive.save()
    response = client.get(LIST)
    assert response.status_code == 200
    assert "no-store" in response["Cache-Control"]
    assert "Cookie" in response["Vary"]
    data = response.json()
    assert set(data) == {
        "filters_config",
        "favorites",
        "urls",
        "show_add_button",
        "additional_buttons",
        "can_export",
        "columns",
        "headers",
        "results",
        "page",
        "messages",
        "presentation",
    }
    assert data["columns"]["list_key"] == "usuarios_list"
    assert data["columns"]["active"] == [
        "first_name",
        "last_name",
        "username",
        "email",
        "rol",
    ]
    assert [header["title"] for header in data["headers"]] == [
        "Nombre",
        "Apellido",
        "Username",
        "Email",
        "Rol",
    ]
    rows = {row["id"]: row for row in data["results"]}
    assert set(rows) == {user.pk, target.pk, inactive.pk}
    assert rows[target.pk]["cells"] == [
        "Ana",
        "Pérez",
        "scoped_target",
        target.email,
        "Rol sintetico",
    ]
    edit = {
        "label": "Editar",
        "url": f"/usuarios/editar/{target.pk}/",
        "type": "primary",
        "icon": "edit",
    }
    assert rows[target.pk]["actions"] == [
        edit,
        {
            "label": "Desactivar",
            "url": f"/usuarios/borrar/{target.pk}/",
            "type": "danger",
            "icon": "trash-alt",
        },
    ]
    assert rows[inactive.pk]["actions"][1] == {
        "label": "Activar",
        "url": f"/usuarios/activar/{inactive.pk}/",
        "type": "success",
        "icon": "check-circle",
    }
    assert data["urls"] == {
        "list": "/usuarios/",
        "reset": "/usuarios/",
        "add": "/usuarios/crear/",
        "export": "/usuarios/exportar/",
    }
    assert data["show_add_button"] is True
    assert data["can_export"] is False
    assert data["additional_buttons"] == []
    assert data["page"]["number"] == 1 and data["page"]["count"] == 3
    assert data["presentation"]["user"]["username"] == "manager_synthetic"


def test_list_filters_use_the_native_advanced_filter(manager):
    _, client, group = manager
    member("needle_user", group)
    member("other_user", group)
    filters = json.dumps(
        {
            "logic": "AND",
            "items": [{"field": "username", "op": "contains", "value": "needle"}],
        }
    )
    data = client.get(LIST, {"filters": filters}).json()
    assert [row["cells"][2] for row in data["results"]] == ["needle_user"]
    assert data["page"]["query_without_page"] == f"filters={_quoted(filters)}&"


def _quoted(value):
    from urllib.parse import quote

    return quote(value, safe="/")


def test_list_is_paginated_by_the_native_page_size(manager):
    _, client, group = manager
    for index in range(26):
        member(f"paged_{index:02d}", group)
    first = client.get(LIST).json()
    assert len(first["results"]) == 25
    assert first["page"]["is_paginated"] is True
    assert first["page"]["next"] == 2 and first["page"]["previous"] is None
    second = client.get(LIST, {"page": 2}).json()
    assert len(second["results"]) == 2
    assert second["page"]["previous"] == 1 and second["page"]["next"] is None
    assert client.get(LIST, {"page": 9}).status_code == 404


def test_export_button_follows_the_native_role():
    user, client = make_actor("exporter", ["view_user"])
    assert client.get(LIST).json()["can_export"] is False
    permission, _ = Permission.objects.get_or_create(
        content_type=ContentType.objects.get_for_model(Group),
        codename="role_exportar_a_csv",
        defaults={"name": "Exportar a csv"},
    )
    user.user_permissions.add(permission)
    assert client.get(LIST).json()["can_export"] is True


def test_confirm_step_names_the_user_without_changing_anything(manager):
    _, client, group = manager
    target = member("confirm_target", group)
    before = digest()
    data = client.get(deactivate(target.pk)).json()
    assert data["title"] == "Desactivar Usuario"
    assert data["object_name"] == "CONFIRM_TARGET"
    assert data["confirm_text"] == "Desactivar"
    assert data["cancel_url"] == "/usuarios/"
    assert client.get(activate(target.pk)).json()["title"] == "Activar Usuario"
    assert digest() == before


def test_deactivate_changes_only_is_active_and_queues_the_native_message(manager):
    _, client, group = manager
    target = member("to_deactivate", group)
    other = member("untouched", group)
    other_before = User.objects.filter(pk=other.pk).values().get()
    response = post(client, deactivate(target.pk))
    assert response.status_code == 200
    assert response.json() == {"ok": True, "redirect": "/usuarios/"}
    target.refresh_from_db()
    assert target.is_active is False
    assert list(target.groups.all()) == [group]
    assert User.objects.filter(pk=other.pk).values().get() == other_before
    messages = client.get(LIST).json()["messages"]
    assert messages == [
        {"message": "Usuario desactivado correctamente.", "level": "success"}
    ]
    assert client.get(LIST).json()["messages"] == []


def test_activate_changes_only_is_active_and_queues_the_native_message(manager):
    _, client, group = manager
    target = member("to_activate", group)
    target.is_active = False
    target.save()
    response = post(client, activate(target.pk))
    assert response.json() == {"ok": True, "redirect": "/usuarios/"}
    target.refresh_from_db()
    assert target.is_active is True
    assert client.get(LIST).json()["messages"] == [
        {"message": "Usuario activado correctamente.", "level": "success"}
    ]


def test_out_of_scope_users_cannot_be_reached_by_url(manager):
    _, client, _ = manager
    outsider = member("outside_scope", Group.objects.create(name="Otro grupo"))
    superuser = User.objects.create_superuser(username="root_synthetic")
    before = digest()
    for target in (outsider, superuser):
        for path in (deactivate(target.pk), activate(target.pk)):
            assert client.get(path).status_code == 404
            assert post(client, path).status_code == 404
    assert digest() == before
    ids = [row["id"] for row in client.get(LIST).json()["results"]]
    assert outsider.pk not in ids and superuser.pk not in ids


def test_state_post_requires_csrf_and_form_content_type(manager):
    _, client, group = manager
    target = member("csrf_target", group)
    before = digest()
    assert post(client, deactivate(target.pk), csrf=False).status_code == 403
    headers = {"HTTP_X_CSRFTOKEN": client.cookies["csrftoken"].value}
    assert (
        client.post(
            deactivate(target.pk), "{}", content_type="application/json", **headers
        ).status_code
        == 415
    )
    assert digest() == before


def test_state_endpoints_reject_unlisted_methods(manager):
    _, client, group = manager
    target = member("method_target", group)
    before = digest()
    assert client.put(deactivate(target.pk)).status_code in (403, 405)
    assert client.delete(activate(target.pk)).status_code in (403, 405)
    assert digest() == before


def test_forged_gate_header_does_not_open_the_list():
    user = User.objects.create_user(username="forged_header")
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    client = Client(enforce_csrf_checks=True, REMOTE_ADDR="203.0.113.43")
    client.force_login(user)
    response = client.get(LIST, HTTP_X_SISOC_WEB_GATE="forged")
    assert response.status_code == 403
    assert response.json()["detail"] == "No tiene permisos para esta acción."
