"""Composite user form through the portal's web API: Comedores owner projection."""

import hashlib
from urllib.parse import urlencode

import pytest
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse
from django.test import Client

from comedores.models import Comedor
from pwa.models import AccesoComedorPWA
from users.secciones_usuario import SECCIONES_COMEDORES, permiso_de_seccion

pytestmark = pytest.mark.django_db
CREATE = "/api/web/users/create/"
LIST = "/api/web/users/list/"
SECRET_MARK = "Contraseña inicial generada"


def edit(user_id):
    return f"/api/web/users/{user_id}/edit/"


def permission(code):
    app_label, codename = code.split(".", 1)
    assert app_label == "auth"
    return Permission.objects.get_or_create(
        codename=codename,
        content_type=ContentType.objects.get_for_model(Group),
        defaults={"name": codename},
    )[0]


def digest():
    return hashlib.sha256(
        repr(
            [
                list(User.objects.order_by("pk").values()),
                list(User.groups.through.objects.order_by("pk").values()),
                list(User.user_permissions.through.objects.order_by("pk").values()),
                list(AccesoComedorPWA.objects.order_by("pk").values_list("pk")),
            ]
        ).encode()
    ).hexdigest()


def actor(username, abm=("add_user", "change_user"), sections=(), delegated=()):
    user = User.objects.create_user(username=username)
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.dni, profile.cuil = "12345678", "20123456786"
    profile.save()
    for group in delegated:
        profile.grupos_asignables.add(group)
    user.user_permissions.add(
        *Permission.objects.filter(content_type__app_label="auth", codename__in=abm),
        *(permission(permiso_de_seccion(clave)) for clave in sections),
    )
    client = Client(enforce_csrf_checks=True, REMOTE_ADDR="203.0.113.42")
    client.force_login(user)
    client.get("/api/web/session/")
    return user, client


def post(client, path, data=None):
    return client.post(
        path,
        urlencode(data or {}, doseq=True),
        content_type="application/x-www-form-urlencoded",
        HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value,
    )


def payload(**extra):
    data = {
        "first_name": "Rita",
        "last_name": "Representante",
        "dni": "30111222",
        "cuil": "27301112224",
        "tipo_usuario": "externo",
        "username": "rita_synthetic",
        "email": "rita@example.com",
        "territorial_scopes": "[]",
        "rol": "Representante",
    }
    data.update(extra)
    return data


def fields_of(data):
    return {f["name"]: f for s in data["sections"] for f in s["fields"]}


@pytest.fixture
def comedor():
    return Comedor.objects.create(nombre="Espacio sintetico")


def test_owner_projection_adds_the_comedores_cards_in_native_order():
    _, client = actor("gestor", sections=SECCIONES_COMEDORES)
    response = client.get(CREATE)
    assert response.status_code == 200
    assert "no-store" in response["Cache-Control"]
    data = response.json()
    assert [s["key"] for s in data["sections"]] == [
        "personal",
        "access",
        "mobile",
        "territorial_comedor",
        "permissions",
        "territorial",
        "teams",
    ]
    assert data["comedores"]["runtime_required"] is False
    assert data["comedores"]["sections"] == sorted(SECCIONES_COMEDORES)
    assert data["presentation"]["user"]["username"] == "gestor"
    assert data["urls"] == {"cancel": "/usuarios/"}
    assert data["territorial"]["municipios_url"] == "/ajax/load-municipios/"
    assert fields_of(data)["password"]["value"] == ""
    assert fields_of(data)["es_representante_pwa"]["kind"] == "boolean"


def test_comedor_options_carry_their_organization_for_the_native_script(comedor):
    _, client = actor("gestor_opciones", sections=SECCIONES_COMEDORES)
    choices = fields_of(client.get(CREATE).json())["comedores_pwa"]["choices"]
    assert any(c["label"] == comedor.nombre for c in choices)
    assert all("organizacion_id" in c for c in choices)


def test_owner_guards_hold_before_and_after_the_relay():
    assert Client().get(CREATE).status_code == 401
    _, no_perm = actor("sin_permiso", abm=(), sections=SECCIONES_COMEDORES)
    assert no_perm.get(CREATE).status_code == 403
    _, add_only = actor("solo_alta", abm=("add_user",), sections=SECCIONES_COMEDORES)
    target = User.objects.create_user(username="objetivo")
    before = digest()
    assert add_only.get(edit(target.pk)).status_code == 403
    assert post(add_only, edit(target.pk), payload()).status_code == 403
    assert digest() == before


def test_create_representative_persists_and_returns_the_secret_once(comedor):
    _, client = actor("gestor_alta", sections=SECCIONES_COMEDORES)
    response = post(
        client,
        CREATE,
        payload(
            es_representante_pwa="on",
            tipo_asociacion_pwa=AccesoComedorPWA.TIPO_ASOCIACION_ESPACIO,
            comedores_pwa=[str(comedor.pk)],
        ),
    )
    assert response.status_code == 200
    body = response.json()
    user = User.objects.get(username="rita_synthetic")
    assert body["ok"] is True
    assert body["redirect"] == f"/usuarios/editar/{user.pk}/"
    secret = body["credential"]["temporary_password"]
    assert user.check_password(secret) and len(secret) == 12
    assert not user.is_staff and not user.profile.acceso_web
    assert AccesoComedorPWA.objects.filter(user=user, comedor=comedor).exists()
    assert "no-store" in response["Cache-Control"]
    # The secret is not in any flash message the list (or the next form) consumes.
    assert secret not in client.get(LIST).content.decode()
    assert secret not in client.get(CREATE).content.decode()


def test_add_only_actor_gets_the_secret_in_the_result_but_never_a_read_path(comedor):
    _, client = actor(
        "solo_alta_mobile", abm=("add_user",), sections=SECCIONES_COMEDORES
    )
    response = post(
        client,
        CREATE,
        payload(
            es_representante_pwa="on",
            tipo_asociacion_pwa=AccesoComedorPWA.TIPO_ASOCIACION_ESPACIO,
            comedores_pwa=[str(comedor.pk)],
        ),
    )
    assert response.status_code == 200
    user = User.objects.get(username="rita_synthetic")
    assert response.json()["credential"]["temporary_password"]
    assert client.get(edit(user.pk)).status_code == 403


def test_edit_projects_the_temporary_password_only_to_the_edit_authority(comedor):
    group = Group.objects.create(name="CDI - Trabajador")
    _, client = actor("gestor_edicion", sections=SECCIONES_COMEDORES, delegated=[group])
    target = User.objects.create_user(username="con_temporal")
    target.groups.add(group)
    target.profile.temporary_password_plaintext = "Temporal-sintetica-2"
    target.profile.save()
    assert client.get(edit(target.pk)).json()["credential"] == {
        "temporary_password": "Temporal-sintetica-2"
    }
    assert "Temporal-sintetica-2" not in client.get(CREATE).content.decode()
    _, scoped = actor("sin_alcance", sections=SECCIONES_COMEDORES)
    assert scoped.get(edit(target.pk)).status_code == 404


def test_rejected_operation_changes_nothing_and_keeps_native_errors(comedor):
    _, client = actor("gestor_rechazo", sections=SECCIONES_COMEDORES)
    before = digest()
    response = post(client, CREATE, payload(es_representante_pwa="on", username=""))
    assert response.status_code == 400
    data = response.json()
    assert "username" in data["errors"]
    assert fields_of(data)["first_name"]["value"] == "Rita"
    assert fields_of(data)["password"]["value"] == ""
    assert digest() == before


def test_a_forged_comedores_field_without_the_section_grants_nothing(comedor):
    _, client = actor("sin_seccion_mobile")
    response = post(
        client,
        CREATE,
        payload(
            password="Clave-segura-123",
            es_representante_pwa="on",
            tipo_asociacion_pwa=AccesoComedorPWA.TIPO_ASOCIACION_ESPACIO,
            comedores_pwa=[str(comedor.pk)],
            puede_gestionar_usuarios_pwa="on",
        ),
    )
    assert response.status_code == 200
    user = User.objects.get(username="rita_synthetic")
    assert not AccesoComedorPWA.objects.filter(user=user).exists()
    assert not user.user_permissions.exists()
    assert response.json()["credential"] is None


def test_a_domain_group_is_applied_through_the_owner_not_refused():
    group = Group.objects.create(name="Grupo con rol de dominio")
    group.permissions.add(permission("auth.role_exportar_a_csv"))
    user, client = actor("gestor_grupo", delegated=[group])
    response = post(
        client, CREATE, payload(password="Clave-segura-123", groups=[str(group.pk)])
    )
    assert response.status_code == 200, response.content
    assert list(User.objects.get(username="rita_synthetic").groups.all()) == [group]


def test_edit_through_the_owner_persists_and_preserves_the_password(comedor):
    group = Group.objects.create(name="CDF - Referente centro")
    _, client = actor("gestor_edita", sections=SECCIONES_COMEDORES, delegated=[group])
    target = User.objects.create_user(username="editable", password="ClaveVieja-123")
    target.groups.add(group)
    old_hash = target.password
    response = post(
        client,
        edit(target.pk),
        payload(username="editable", first_name="Nuevo", password=""),
    )
    assert response.status_code == 200, response.content
    target.refresh_from_db()
    assert target.first_name == "Nuevo"
    assert target.password == old_hash


def test_owner_unavailable_falls_back_on_read_and_refuses_the_write(mocker):
    _, client = actor("gestor_caido", sections=SECCIONES_COMEDORES)
    down = HttpResponse(status=503)
    down.owner_missing = True
    mocker.patch("usuarios.web_user_form.relay_to_owner", return_value=down)
    data = client.get(CREATE).json()
    assert data["comedores"]["runtime_required"] is True
    assert "es_representante_pwa" not in fields_of(data)
    assert [m["message"] for m in data["messages"]] == [
        "Espacios comunitarios no está disponible. "
        "Podés realizar las operaciones independientes; sus accesos se conservan."
    ]
    before = digest()
    response = post(client, CREATE, payload(es_representante_pwa="on"))
    assert response.status_code == 409
    assert digest() == before


def test_anonymous_and_rejected_owner_calls_are_never_ok_and_persist_nothing():
    _, no_perm = actor("sin_permiso_dueno", abm=(), sections=SECCIONES_COMEDORES)
    before = digest()
    anonymous = Client()
    for method in (anonymous.get, anonymous.post):
        response = method("/interno/usuarios/operacion-web/")
        assert response.status_code == 401
        assert response.json().get("ok") is not True
    assert digest() == before
    # An authenticated actor without permission is refused, not redirected.
    response = no_perm.get("/interno/usuarios/operacion-web/")
    assert response.status_code == 403
    assert digest() == before


def test_the_core_relay_never_turns_an_owner_redirect_into_a_save(mocker):
    _, client = actor("gestor_redirige", sections=SECCIONES_COMEDORES)
    login = HttpResponse(status=302)
    login["Location"] = "/login/?next=/interno/usuarios/operacion-web/"
    mocker.patch("usuarios.web_user_form.relay_to_owner", return_value=login)
    before = digest()
    response = post(client, CREATE, payload(es_representante_pwa="on"))
    assert response.status_code == 401
    assert response.json().get("ok") is not True
    assert client.get(CREATE).status_code == 401
    assert digest() == before
