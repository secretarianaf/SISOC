"""Public session contracts for the React group-management transport."""

import hashlib
from urllib.parse import urlencode

import pytest
from django.contrib.auth.models import Group, Permission, User
from django.test import Client

pytestmark = pytest.mark.django_db
LIST = "/api/web/groups/"
CREATE = LIST + "create/"


def edit(group_id):
    return f"{LIST}{group_id}/edit/"


def digest():
    return hashlib.sha256(
        repr(
            [
                list(Group.objects.order_by("pk").values()),
                list(Group.permissions.through.objects.order_by("pk").values()),
                list(User.groups.through.objects.order_by("pk").values()),
            ]
        ).encode()
    ).hexdigest()


@pytest.fixture
def actor():
    user = User.objects.create_user(username="groups_synthetic")
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.dni = "12345678"
    profile.cuil = "20123456786"
    profile.save()
    user.user_permissions.set(
        Permission.objects.filter(
            content_type__app_label="auth",
            codename__in=["view_group", "add_group", "change_group"],
        )
    )
    client = Client(enforce_csrf_checks=True, REMOTE_ADDR="203.0.113.42")
    client.force_login(user)
    client.get("/api/web/session/")
    return user, client


def post(client, path, data, csrf=True):
    headers = {"HTTP_X_CSRFTOKEN": client.cookies["csrftoken"].value} if csrf else {}
    return client.post(
        path,
        urlencode(data, doseq=True),
        content_type="application/x-www-form-urlencoded",
        **headers,
    )


@pytest.mark.parametrize("path", [LIST, CREATE, edit(999999)])
def test_anonymous_is_rejected_before_object_lookup(path):
    before = digest()
    assert Client().get(path).status_code == 401
    assert digest() == before


def test_form_metadata_reuses_ordered_permission_choices_without_admin(actor):
    user, client = actor
    assert not user.is_staff and not user.is_superuser
    response = client.get(CREATE)
    assert response.status_code == 200
    data = response.json()
    assert set(data) == {
        "fields",
        "initial",
        "errors",
        "presentation",
        "title",
        "submit_text",
    }
    assert data["initial"] == {"name": "", "permissions": []}
    assert [field["name"] for field in data["fields"]] == ["name", "permissions"]
    choices = data["fields"][1]["choices"]
    expected = Permission.objects.select_related("content_type").order_by(
        "content_type__app_label", "name"
    )
    assert [choice["id"] for choice in choices] == list(
        expected.values_list("pk", flat=True)
    )
    assert [choice["label"] for choice in choices] == [
        str(permission) for permission in expected
    ]
    assert client.get("/admin/jsi18n/").status_code == 302
    assert "no-store" in response["Cache-Control"]
    assert "Cookie" in response["Vary"]
    head = client.head(CREATE)
    assert head.status_code == 200 and head.content == b""


def test_list_uses_native_search_columns_and_only_public_group_values(actor):
    _, client = actor
    Group.objects.create(name="Zulu")
    group = Group.objects.create(name="Alpha")
    response = client.get(LIST, {"busqueda": "  alp  "})
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "alp"
    assert data["items"] == [
        {
            "id": group.pk,
            "name": "Alpha",
            "permissions_count": group.permissions.count(),
        }
    ]
    assert data["columns"]["active"] == ["name", "permissions_count"]
    assert data["columns"]["endpoint"] == "/ajax/columnas-preferencias/"
    assert data["can_export"] is False


def test_create_strips_name_saves_permissions_and_consumes_notice_once(actor):
    _, client = actor
    permission = Permission.objects.get(
        content_type__app_label="auth", codename="view_group"
    )
    response = post(
        client, CREATE, {"name": "  New group  ", "permissions": [permission.pk]}
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True, "redirect": "/grupos/"}
    group = Group.objects.get(name="New group")
    assert list(group.permissions.values_list("pk", flat=True)) == [permission.pk]
    assert client.get(LIST).json()["messages"] == [
        {"message": "Grupo creado correctamente.", "level": "success"}
    ]
    assert client.get(LIST).json()["messages"] == []


@pytest.mark.parametrize(
    "data,field",
    [
        ({"name": "  "}, "name"),
        ({"name": "EXISTING"}, "name"),
        ({"name": "New", "permissions": [999999]}, "permissions"),
    ],
)
def test_rejected_form_preserves_all_group_state(actor, data, field):
    _, client = actor
    Group.objects.create(name="Existing")
    before = digest()
    response = post(client, CREATE, data)
    assert response.status_code == 400
    assert field in response.json()["errors"]
    assert digest() == before


def test_update_propagates_membership_permissions_and_can_clear_them(actor):
    _, client = actor
    member = User.objects.create_user(username="member_synthetic")
    group = Group.objects.create(name="Members")
    member.groups.add(group)
    permission = Permission.objects.get(
        content_type__app_label="auth", codename="view_group"
    )
    profile_before = (
        type(member.profile).objects.filter(pk=member.profile.pk).values().get()
    )
    assert not User.objects.get(pk=member.pk).has_perm("auth.view_group")
    assert (
        post(
            client, edit(group.pk), {"name": "Members", "permissions": [permission.pk]}
        ).status_code
        == 200
    )
    assert User.objects.get(pk=member.pk).has_perm("auth.view_group")
    assert client.get(edit(group.pk)).json()["initial"]["permissions"] == [
        str(permission.pk)
    ]
    assert (
        post(client, edit(group.pk), {"name": "Members", "permissions": []}).status_code
        == 200
    )
    assert not User.objects.get(pk=member.pk).has_perm("auth.view_group")
    member.profile.refresh_from_db()
    after = type(member.profile).objects.filter(pk=member.profile.pk).values().get()
    assert after == profile_before
    assert member.groups.filter(pk=group.pk).exists()


@pytest.mark.parametrize(
    "permission,path",
    [("view_group", LIST), ("add_group", CREATE), ("change_group", edit(999999))],
)
def test_action_permission_is_checked_before_object(actor, permission, path):
    user, client = actor
    user.user_permissions.remove(
        Permission.objects.get(content_type__app_label="auth", codename=permission)
    )
    before = digest()
    assert client.get(path).status_code == 403
    assert digest() == before


def test_add_permission_does_not_require_list_permission(actor):
    user, client = actor
    user.user_permissions.set(
        Permission.objects.filter(content_type__app_label="auth", codename="add_group")
    )
    assert client.get(CREATE).status_code == 200
    assert client.get(LIST).status_code == 403
    assert post(client, CREATE, {"name": "Create only"}).status_code == 200


def test_prerequisite_precedes_form_and_no_state_is_mutated(actor):
    user, client = actor
    user.profile.must_change_password = True
    user.profile.save(update_fields=["must_change_password"])
    before = digest()
    response = post(client, CREATE, {"name": "Blocked"})
    assert response.status_code == 403
    assert response.json()["state"] == "password_change_required"
    assert digest() == before


def test_csrf_methods_media_and_unknown_object_do_not_mutate(actor):
    _, client = actor
    before = digest()
    assert post(client, CREATE, {"name": "No csrf"}, csrf=False).status_code == 403
    assert (
        client.delete(
            CREATE, HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value
        ).status_code
        == 405
    )
    assert post(client, LIST, {"name": "Wrong route"}).status_code == 405
    assert (
        client.post(
            CREATE,
            '{"name":"JSON"}',
            content_type="application/json",
            HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value,
        ).status_code
        == 415
    )
    assert client.get(edit(999999)).status_code == 404
    assert digest() == before


def test_legacy_group_and_export_routes_remain_native(actor):
    _, client = actor
    assert client.get("/grupos/").status_code == 200
    assert b"text/html" in client.get("/grupos/")["Content-Type"].encode()
    assert client.get("/grupos/exportar/").status_code == 403


@pytest.mark.parametrize(
    "request_case",
    [
        (route, address, kind)
        for route in ("list", "create", "edit", "missing")
        for address in ("127.0.0.1", "203.0.113.42")
        for kind in ("anonymous", "denied", "pending", "allowed")
    ],
)
def test_group_head_enforces_action_guards_for_all_addresses(
    actor, request_case, settings
):
    user, _ = actor
    route, address, kind = request_case
    settings.INTERNAL_IPS = ["127.0.0.1"]
    group = Group.objects.create(name="HEAD target")
    path = {
        "list": LIST,
        "create": CREATE,
        "edit": edit(group.pk),
        "missing": edit(999999),
    }[route]
    if kind == "denied":
        user.user_permissions.clear()
    elif kind == "pending":
        profile = user.profile
        profile.must_change_password = True
        profile.save(update_fields=["must_change_password"])
    client = Client(enforce_csrf_checks=True, REMOTE_ADDR=address)
    if kind != "anonymous":
        client.force_login(user)
    expected = 401 if kind == "anonymous" else 403
    if kind == "allowed":
        expected = 404 if route == "missing" else 200
    before = digest()
    response = client.head(path)
    assert response.status_code == expected
    assert response.content == b""
    assert "X-View" not in response
    if expected != 404:
        assert response["Content-Type"].startswith("application/json")
        assert "private" in response["Cache-Control"]
        assert "no-store" in response["Cache-Control"]
        assert "Cookie" in response["Vary"]
        assert "csrftoken" in client.cookies
    if kind == "anonymous":
        assert "sessionid" not in client.cookies
    assert digest() == before
