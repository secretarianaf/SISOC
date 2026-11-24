"""Public session contracts for the React user create/edit form (core fields)."""

import hashlib
import json
from urllib.parse import urlencode

import pytest
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse, StreamingHttpResponse
from django.test import Client

pytestmark = pytest.mark.django_db
CREATE = "/api/web/users/create/"
LIST = "/api/web/users/list/"


def edit(user_id):
    return f"/api/web/users/{user_id}/edit/"


def digest():
    return hashlib.sha256(
        repr(
            [
                list(User.objects.order_by("pk").values()),
                list(User.groups.through.objects.order_by("pk").values()),
                list(User.user_permissions.through.objects.order_by("pk").values()),
                list(
                    User.objects.order_by("pk").values_list(
                        "profile__must_change_password",
                        "profile__acceso_web",
                        "profile__es_usuario_provincial",
                        "profile__temporary_password_plaintext",
                    )
                ),
            ]
        ).encode()
    ).hexdigest()


def permission(codename):
    """Auth permissions (``role_*`` included) exist only once something creates them."""
    return Permission.objects.get_or_create(
        codename=codename,
        content_type=ContentType.objects.get_for_model(User),
        defaults={"name": codename},
    )[0]


def ready(user, perms=(), sections=()):
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.dni = "12345678"
    profile.cuil = "20123456786"
    profile.save()
    codes = list(perms) + [f"role_usuarios_seccion_{name}" for name in sections]
    user.user_permissions.set([permission(code) for code in codes])
    client = Client(enforce_csrf_checks=True, REMOTE_ADDR="203.0.113.42")
    client.force_login(user)
    client.get("/api/web/session/")
    return client


def make_actor(username, perms, delegated=(), sections=(), roles=()):
    user = User.objects.create_user(username=username)
    for group in delegated:
        user.profile.grupos_asignables.add(group)
    for codename in roles:
        user.profile.roles_asignables.add(permission(codename))
    return user, ready(user, perms, sections)


def post(client, path, data=None, csrf=True):
    headers = {"HTTP_X_CSRFTOKEN": client.cookies["csrftoken"].value} if csrf else {}
    return client.post(
        path,
        urlencode(data or {}, doseq=True),
        content_type="application/x-www-form-urlencoded",
        **headers,
    )


def payload(**extra):
    data = {
        "first_name": "Ada",
        "last_name": "Lovelace",
        "dni": "30111222",
        "cuil": "27301112224",
        "tipo_usuario": "interno",
        "username": "ada_synthetic",
        "email": "ada@example.com",
        "password": "ClaveSegura123!",
        "territorial_scopes": "[]",
        "rol": "Analista",
    }
    data.update(extra)
    return data


def fields_of(data):
    return {
        field["name"]: field
        for section in data["sections"]
        for field in section["fields"]
    }


@pytest.fixture
def owner_down(mocker):
    """The Comedores owner cannot be reached: a relayed write changes nothing."""
    down = HttpResponse(status=503)
    down.owner_missing = True
    return mocker.patch("usuarios.web_user_form.relay_to_owner", return_value=down)


@pytest.fixture
def group():
    return Group.objects.create(name="CDI - Trabajador")


@pytest.fixture
def manager(group):
    return make_actor(
        "manager_synthetic",
        ["view_user", "add_user", "change_user"],
        delegated=[group],
    )


@pytest.mark.parametrize("path", [CREATE, edit(999999)])
def test_anonymous_is_rejected_before_object_lookup(path):
    before = digest()
    assert Client().get(path).status_code == 401
    assert Client(enforce_csrf_checks=False).post(path, {}).status_code == 401
    assert digest() == before


def test_pending_prerequisite_blocks_get_and_post(manager):
    user, client = manager
    profile = user.profile
    profile.must_change_password = True
    profile.save()
    before = digest()
    response = client.get(CREATE)
    assert response.status_code == 403
    assert response.json()["required_action_url"] == "/password/first-change/"
    assert post(client, CREATE, payload()).status_code == 403
    assert digest() == before


def test_each_action_needs_its_own_permission(group):
    _, add_only = make_actor("add_only", ["add_user"], delegated=[group])
    _, change_only = make_actor("change_only", ["change_user"], delegated=[group])
    target = User.objects.create_user(username="permission_target")
    target.groups.add(group)
    before = digest()
    assert add_only.get(CREATE).status_code == 200
    assert add_only.get(edit(target.pk)).status_code == 403
    assert post(add_only, edit(target.pk), payload()).status_code == 403
    assert change_only.get(edit(target.pk)).status_code == 200
    assert change_only.get(CREATE).status_code == 403
    assert post(change_only, CREATE, payload()).status_code == 403
    assert digest() == before


def test_post_without_csrf_is_refused(manager):
    _, client = manager
    before = digest()
    assert post(client, CREATE, payload(), csrf=False).status_code == 403
    assert digest() == before


def test_non_form_encoded_body_is_refused(manager):
    _, client = manager
    token = client.cookies["csrftoken"].value
    response = client.post(
        CREATE, "{}", content_type="application/json", HTTP_X_CSRFTOKEN=token
    )
    assert response.status_code == 415


def test_create_projection_follows_the_native_cards(manager, group):
    _, client = manager
    response = client.get(CREATE)
    assert response.status_code == 200
    assert "no-store" in response["Cache-Control"]
    data = response.json()
    assert data["mode"] == "create"
    assert data["object"] is None
    assert [section["key"] for section in data["sections"]] == [
        "personal",
        "access",
        "permissions",
        "territorial",
    ]
    fields = fields_of(data)
    assert fields["password"]["required"] is True
    assert fields["password"]["value"] == ""
    assert fields["tipo_usuario"]["kind"] == "radio"
    assert {item["value"] for item in fields["tipo_usuario"]["choices"]} == {
        "interno",
        "provincial",
        "externo",
    }
    assert [item["label"] for item in fields["groups"]["choices"]] == [group.name]
    assert data["identity_present"] == ["groups", "es_usuario_provincial"]
    assert data["comedores"]["sections"] == []
    assert data["urls"]["cancel"] == "/usuarios/"
    assert data["credential"] is None


def test_sections_and_assignable_lists_depend_on_the_actor(group):
    other = Group.objects.create(name="CDF - Referente centro")
    _, restricted = make_actor("restricted", ["add_user"], delegated=[group])
    _, admin = make_actor(
        "section_admin",
        ["add_user"],
        delegated=[group],
        sections=["administracion", "datacalle", "inspecciones_escolares"],
    )
    narrow = restricted.get(CREATE).json()
    wide = admin.get(CREATE).json()
    assert "user_permissions" not in fields_of(narrow)
    assert "es_relevador_calle" not in fields_of(narrow)
    assert "es_inspector_escolar" not in fields_of(narrow)
    assert {"datacalle", "inspecciones", "delegation"} <= {
        section["key"] for section in wide["sections"]
    }
    assert {"user_permissions", "grupos_asignables", "acceso_siis"} <= set(
        fields_of(wide)
    )
    assert other.name not in [
        item["label"] for item in fields_of(narrow)["groups"]["choices"]
    ]
    assert other.name not in [
        item["label"] for item in fields_of(wide)["groups"]["choices"]
    ]
    assert {"user_permissions", "acceso_web"} <= set(wide["identity_present"])


def test_comedores_sections_fall_back_to_the_core_form_when_the_owner_is_down(
    owner_down,
):
    _, client = make_actor(
        "comedores_actor", ["add_user"], sections=["mobile_comedores"]
    )
    data = client.get(CREATE).json()
    assert data["comedores"] == {
        "sections": ["mobile_comedores"],
        "runtime_required": True,
    }
    assert "es_representante_pwa" not in fields_of(data)
    assert owner_down.called


def test_create_persists_through_the_native_form_and_queues_its_message(manager, group):
    _, client = manager
    response = post(client, CREATE, payload(groups=[str(group.pk)]))
    assert response.status_code == 200
    assert response.json() == {"ok": True, "redirect": "/usuarios/"}
    user = User.objects.get(username="ada_synthetic")
    assert user.check_password("ClaveSegura123!")
    assert user.password != "ClaveSegura123!"
    assert not user.is_staff and not user.is_superuser
    assert list(user.groups.all()) == [group]
    assert (user.first_name, user.last_name, user.email) == (
        "Ada",
        "Lovelace",
        "ada@example.com",
    )
    profile = user.profile
    assert profile.must_change_password is True
    assert (profile.dni, profile.cuil, profile.tipo_usuario) == (
        "30111222",
        "27301112224",
        "interno",
    )
    listing = client.get(LIST).json()
    assert [item["message"] for item in listing["messages"]] == [
        "Usuario creado correctamente."
    ]


def test_rejected_create_is_atomic_and_keeps_the_form_without_the_password(
    manager,
):
    _, client = manager
    User.objects.create_user(username="ada_synthetic")
    before = digest()
    response = post(client, CREATE, payload(password=""))
    assert response.status_code == 400
    data = response.json()
    assert "password" in data["errors"]
    assert fields_of(data)["password"]["value"] == ""
    assert fields_of(data)["first_name"]["value"] == "Ada"
    assert digest() == before
    response = post(client, CREATE, payload(password="OtraClave123!"))
    assert response.status_code == 400
    assert "username" in response.json()["errors"]
    assert "OtraClave123!" not in response.content.decode()
    assert digest() == before


def test_forged_groups_outside_the_delegation_are_refused_and_nothing_is_saved(
    manager,
):
    _, client = manager
    outside = Group.objects.create(name="CDF - Referente centro")
    before = digest()
    response = post(client, CREATE, payload(groups=[str(outside.pk)]))
    assert response.status_code == 400
    assert response.json()["errors"]["groups"][0]["message"] == (
        f"Seleccione una opción válida. {outside.pk} no es una de las "
        "opciones disponibles."
    )
    assert digest() == before


def test_forged_direct_permissions_and_flags_are_ignored_without_the_section(
    manager,
):
    _, client = manager
    delete = permission("delete_user")
    response = post(
        client,
        CREATE,
        payload(
            user_permissions=[str(delete.pk)],
            acceso_siis="on",
            is_superuser="on",
            is_staff="on",
            grupos_asignables=[
                str(Group.objects.create(name="CDF - Referente centro").pk)
            ],
        ),
    )
    assert response.status_code == 200
    user = User.objects.get(username="ada_synthetic")
    assert not user.is_superuser and not user.is_staff
    assert not user.user_permissions.exists()
    assert not user.profile.acceso_siis
    assert not user.profile.grupos_asignables.exists()


def test_a_role_outside_the_actor_roles_cannot_be_granted_as_a_direct_permission(
    group, owner_down
):
    _, client = make_actor(
        "role_admin",
        ["add_user"],
        delegated=[group],
        sections=["administracion"],
        roles=["role_exportar_a_csv"],
    )
    forbidden = permission("delete_user")
    allowed = permission("role_exportar_a_csv")
    before = digest()
    response = post(client, CREATE, payload(user_permissions=[str(forbidden.pk)]))
    assert response.status_code == 400
    assert response.json()["errors"]["user_permissions"][0]["message"] == (
        "Solo puede asignar roles habilitados para su usuario."
    )
    assert digest() == before
    # An operation that needs the Comedores owner is refused while it is down.
    response = post(client, CREATE, payload(user_permissions=[str(allowed.pk)]))
    assert response.status_code == 409
    assert response.json()["state"] == "comedores_runtime_required"
    assert digest() == before


def test_domain_group_changes_are_refused_without_mutation(manager, owner_down):
    user, client = manager
    domain = Group.objects.create(name="Grupo con rol de dominio")
    domain.permissions.add(permission("role_exportar_a_csv"))
    user.profile.grupos_asignables.add(domain)
    before = digest()
    response = post(client, CREATE, payload(groups=[str(domain.pk)]))
    assert response.status_code == 409
    assert response.json() == {
        "detail": (
            "La operación requiere validar Espacios comunitarios y no puede "
            "completarse desde esta pantalla."
        ),
        "state": "comedores_runtime_required",
    }
    assert digest() == before


def test_comedores_field_in_the_post_is_refused_without_mutation(manager, owner_down):
    _, client = manager
    before = digest()
    response = post(client, CREATE, payload(es_representante_pwa="on"))
    assert response.status_code == 409
    assert digest() == before


def edit_target(group, **extra):
    target = User.objects.create_user(
        username="edit_target", email="old@example.com", **extra
    )
    target.groups.add(group)
    target.set_password("ClaveVieja123!")
    target.save()
    return target


def test_edit_projects_the_current_values_and_no_secret(manager, group):
    _, client = manager
    target = edit_target(group, first_name="Grace")
    data = client.get(edit(target.pk)).json()
    fields = fields_of(data)
    assert data["mode"] == "edit"
    assert data["object"] == {"id": target.pk, "username": "edit_target"}
    assert fields["first_name"]["value"] == "Grace"
    assert fields["groups"]["value"] == [str(group.pk)]
    assert fields["password"]["required"] is False
    assert fields["password"]["value"] == ""
    assert data["credential"] is None
    assert target.password not in client.get(edit(target.pk)).content.decode()


def test_edit_outside_the_actor_scope_is_not_found_and_not_changed(group):
    _, client = make_actor("lonely_editor", ["change_user"])
    target = edit_target(group)
    before = digest()
    assert client.get(edit(target.pk)).status_code == 404
    assert post(client, edit(target.pk), payload()).status_code == 404
    assert digest() == before


def test_edit_with_an_empty_password_keeps_the_hash_and_the_unlisted_state(
    manager, group
):
    _, client = manager
    target = edit_target(group)
    old_hash = target.password
    response = post(
        client,
        edit(target.pk),
        {"first_name": "Grace", "password": "", "username": "edit_target"},
    )
    assert response.status_code == 200
    target.refresh_from_db()
    assert target.first_name == "Grace"
    assert target.password == old_hash
    assert list(target.groups.all()) == [group]
    assert target.profile.must_change_password is False


def test_edit_with_a_new_password_changes_it_and_requires_the_change(manager, group):
    _, client = manager
    target = edit_target(group)
    target.profile.temporary_password_plaintext = "Vieja-temporal-1"
    target.profile.save()
    response = post(
        client,
        edit(target.pk),
        {"username": "edit_target", "password": "NuevaClave123!"},
    )
    assert response.status_code == 200
    target.refresh_from_db()
    assert target.check_password("NuevaClave123!")
    assert target.profile.must_change_password is True
    assert target.profile.temporary_password_plaintext is None


def test_rejected_edit_keeps_everything(manager, group):
    _, client = manager
    target = edit_target(group)
    before = digest()
    response = post(client, edit(target.pk), {"username": ""})
    assert response.status_code == 400
    assert "username" in response.json()["errors"]
    assert digest() == before


def test_temporary_password_is_projected_only_to_the_edit_authority(manager, group):
    _, client = manager
    target = edit_target(group)
    target.profile.temporary_password_plaintext = "Temporal-sintetica-1"
    target.profile.save()
    body = client.get(edit(target.pk))
    assert body.json()["credential"] == {"temporary_password": "Temporal-sintetica-1"}
    assert "no-store" in body["Cache-Control"]
    assert "Cookie" in body["Vary"]
    assert "Temporal-sintetica-1" not in client.get(CREATE).content.decode()
    assert "Temporal-sintetica-1" not in client.get(LIST).content.decode()
    # An editor with no scope over the user never gets the credential.
    _, outsider = make_actor("outsider_editor", ["change_user"])
    assert outsider.get(edit(target.pk)).status_code == 404


def test_a_streamed_owner_answer_is_relayed_with_the_portal_frame(mocker):
    """The backend proxy returns a stream: its JSON gets the presentation and URLs."""
    _, client = make_actor(
        "streamed_actor", ["add_user"], sections=["mobile_comedores"]
    )
    owner = {
        "mode": "create",
        "object": None,
        "sections": [],
        "identity_present": [],
        "errors": {},
        "comedores": {"sections": ["mobile_comedores"], "runtime_required": False},
        "territorial": {"initial": []},
        "credential": None,
        "messages": [],
    }
    mocker.patch(
        "usuarios.web_user_form.relay_to_owner",
        return_value=StreamingHttpResponse(
            iter([json.dumps(owner).encode()]), content_type="application/json"
        ),
    )
    data = client.get(CREATE).json()
    assert data["comedores"]["runtime_required"] is False
    assert data["presentation"]["user"]["username"] == "streamed_actor"
    assert data["urls"] == {"cancel": "/usuarios/"}
    assert data["territorial"]["localidades_url"] == "/ajax/load-localidades/"
