"""Contrato SIIS y separación de habilitaciones."""

from unittest.mock import patch

import pytest
from django.contrib.auth.models import Permission, User
from django.core import signing
from django.core.cache import cache
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient
from rest_framework_api_key.models import APIKey

from usuarios.services_siis import TOKEN_SALT

PASSWORD = "UnaClaveSegura568!"
LOGIN = "/api/users/login/"
ADMIN_TOKEN = "/api/users/siis/admin-token/"
CREATE = "/api/users/siis/"


@pytest.fixture
def integration(db):
    cache.clear()
    key, raw_key = APIKey.objects.create_key(name="Integración compartida")
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Api-Key {raw_key}")
    return client, key


@pytest.fixture
def administrator(db):
    user = User.objects.create_user(username="admin_siis", password=PASSWORD)
    user.profile.acceso_siis = True
    user.profile.save()
    user.user_permissions.add(
        Permission.objects.get(content_type__app_label="auth", codename="add_user")
    )
    return user


def _admin_token(client, user):
    response = client.post(
        ADMIN_TOKEN, {"username": user.username, "password": PASSWORD}, format="json"
    )
    assert response.status_code == 200
    assert response.data["expires_in"] == 3600
    return response.data["admin_token"]


def _payload(**overrides):
    return {
        "username": "nuevo_siis",
        "password": PASSWORD,
        "first_name": "Ana",
        "last_name": "Pérez",
        "email": "ana@example.com",
        "dni": "12.345 678",
        **overrides,
    }


def _create(client, token, **overrides):
    return client.post(
        CREATE, _payload(**overrides), format="json", HTTP_X_SIIS_ADMIN_TOKEN=token
    )


def test_login_siis_exact_fields_without_legacy_token(integration, administrator):
    client, _ = integration
    profile = administrator.profile
    profile.must_change_password = True
    profile.initial_password_expires_at = timezone.now()
    profile.save()
    response = client.post(
        LOGIN,
        {"app": "siis", "username": administrator.username, "password": PASSWORD},
        format="json",
    )
    assert response.status_code == 200
    assert set(response.data) == {
        "id",
        "username",
        "first_name",
        "last_name",
        "email",
        "dni",
        "acceso_siis",
    }
    assert not Token.objects.filter(user=administrator).exists()
    assert _admin_token(client, administrator)
    profile.refresh_from_db()
    assert profile.must_change_password
    assert profile.initial_password_expires_at is not None


@pytest.mark.parametrize(
    "condition,status",
    [("wrong_password", 401), ("inactive", 401), ("no_access", 403), ("no_key", 403)],
)
def test_login_denials_disclose_no_user(integration, administrator, condition, status):
    client, _ = integration
    password = PASSWORD
    if condition == "wrong_password":
        password = "incorrecta"
    if condition == "inactive":
        administrator.is_active = False
        administrator.save()
    if condition == "no_access":
        administrator.profile.acceso_siis = False
        administrator.profile.save()
    if condition == "no_key":
        client.credentials()
    response = client.post(
        LOGIN,
        {"app": "siis", "username": administrator.username, "password": password},
        format="json",
    )
    assert response.status_code == status
    assert set(response.data) == {"detail"}
    assert not Token.objects.filter(user=administrator).exists()


def test_create_account_has_only_siis_and_hashed_password(integration, administrator):
    client, _ = integration
    response = _create(client, _admin_token(client, administrator))
    assert response.status_code == 201
    user = User.objects.get(pk=response.data["id"])
    assert user.check_password(PASSWORD)
    assert user.password != PASSWORD
    assert user.profile.dni == "12345678"
    assert user.profile.acceso_siis and not user.profile.acceso_web
    assert not user.is_staff and not user.is_superuser
    assert not user.groups.exists() and not user.user_permissions.exists()
    assert (
        not user.profile.es_territorial_comedor and not user.profile.es_relevador_calle
    )
    assert not user.profile.must_change_password
    assert user.profile.temporary_password_plaintext is None


@pytest.mark.parametrize(
    "condition,status",
    [
        ("missing", 401),
        ("tampered", 401),
        ("expired", 401),
        ("wrong_purpose", 401),
        ("inactive", 403),
        ("no_access", 403),
        ("no_permission", 403),
        ("revoked_key", 403),
    ],
)
def test_create_rechecks_all_credentials(integration, administrator, condition, status):
    client, key = integration
    token = _admin_token(client, administrator)
    if condition == "missing":
        token = ""
    elif condition == "tampered":
        token += "x"
    elif condition == "expired":
        with patch(
            "django.core.signing.time.time",
            return_value=timezone.now().timestamp() - 3601,
        ):
            token = signing.dumps({"user_id": administrator.pk}, salt=TOKEN_SALT)
    elif condition == "wrong_purpose":
        token = signing.dumps({"user_id": administrator.pk}, salt="otra-integracion")
    elif condition == "inactive":
        administrator.is_active = False
        administrator.save()
    elif condition == "no_access":
        administrator.profile.acceso_siis = False
        administrator.profile.save()
    elif condition == "no_permission":
        administrator.user_permissions.clear()
    elif condition == "revoked_key":
        key.revoked = True
        key.save()
    response = _create(client, token)
    assert response.status_code == status
    assert not User.objects.filter(username="nuevo_siis").exists()


@pytest.mark.parametrize(
    "field,value",
    [
        ("username", " ADMIN_SIIS "),
        ("email", " ADMIN@EXAMPLE.COM "),
        ("dni", "12.345 678"),
    ],
)
def test_duplicate_rejected_without_modifying_existing(
    integration, administrator, field, value
):
    client, _ = integration
    administrator.email = " admin@example.com "
    administrator.save()
    administrator.profile.dni = "12 345.678" if field == "dni" else "87654321"
    administrator.profile.save()
    token = _admin_token(client, administrator)
    response = _create(client, token, **{field: value})
    assert response.status_code == 409
    assert set(response.data) == {"error", "message"}
    assert response.data["error"] == "account_exists"
    administrator.refresh_from_db()
    assert administrator.email == " admin@example.com "


@pytest.mark.parametrize(
    "extra",
    [{"is_staff": True}, {"acceso_web": True}, {"groups": [1]}, {"source": "siis"}],
)
def test_privilege_payload_rejected(integration, administrator, extra):
    client, _ = integration
    response = _create(client, _admin_token(client, administrator), **extra)
    assert response.status_code == 400
    assert not User.objects.filter(username="nuevo_siis").exists()


@pytest.mark.parametrize(
    "field,value",
    [
        ("dni", "123"),
        ("dni", "123456789"),
        ("dni", "1234A678"),
        ("email", "invalido"),
        ("password", "   "),
        ("password", "123"),
        ("first_name", ""),
        ("last_name", ""),
        ("username", ""),
    ],
)
def test_invalid_required_data_creates_nothing(
    integration, administrator, field, value
):
    client, _ = integration
    response = _create(client, _admin_token(client, administrator), **{field: value})
    assert response.status_code == 400
    assert not User.objects.filter(username="nuevo_siis").exists()


@pytest.mark.parametrize("path", ["/", "/admin/"])
def test_existing_web_session_blocked_on_next_request(client, administrator, path):
    administrator.is_staff = True
    administrator.profile.must_change_password = False
    administrator.profile.save()
    administrator.save()
    client.force_login(administrator)
    administrator.profile.acceso_web = False
    administrator.profile.save()
    assert client.get(path).status_code == 403


def test_admin_and_backoffice_login_use_flag(client, administrator):
    administrator.is_staff = True
    administrator.save()
    administrator.profile.acceso_web = False
    administrator.profile.save()
    for path in ("/login/", "/admin/login/"):
        response = client.post(
            path, {"username": administrator.username, "password": PASSWORD}
        )
        assert response.status_code == 200
        assert "_auth_user_id" not in client.session


def test_web_access_does_not_depend_on_datacalle_role(integration, administrator):
    from usuarios.forms import BackofficeAuthenticationForm

    administrator.profile.datacalle_rol = "entrevistador"
    administrator.profile.acceso_web = True
    administrator.profile.save()
    form = BackofficeAuthenticationForm(
        data={"username": administrator.username, "password": PASSWORD}
    )
    assert form.is_valid(), form.errors


def test_siis_and_web_flags_cannot_be_changed_without_administration_section(
    administrator,
):
    from usuarios.forms import CustomUserChangeForm

    actor = User.objects.create_user(username="sin_seccion_admin")
    form = CustomUserChangeForm(instance=administrator, actor=actor)
    assert form.fields["acceso_web"].disabled
    assert form.fields["acceso_siis"].disabled


def test_initial_web_access_defaults_true():
    from usuarios.forms import UserCreationForm

    assert UserCreationForm.base_fields["acceso_web"].initial is True


@pytest.mark.django_db
def test_initialization_preserves_legacy_web_access():
    from importlib import import_module
    from types import SimpleNamespace

    from django.apps import apps
    from django.db import connection
    from comedores.models import Comedor
    from organizaciones.models import Organizacion
    from pwa.models import AccesoComedorPWA, AccesoOrganizacionPWA

    users = [
        User.objects.create_user(username=f"initial_{index}") for index in range(7)
    ]
    for user, role in zip(
        users[1:4], ("entrevistador", "coordinador", "administrador")
    ):
        user.profile.datacalle_rol = role
        user.profile.save()
    users[4].profile.configuracion_mobile = {"es_coordinador_equipo_tecnico_pwa": True}
    users[4].profile.save()
    organization = Organizacion.objects.create(nombre="Organización actual")
    other = Organizacion.objects.create(nombre="Organización desalineada")
    comedor = Comedor.objects.create(nombre="Espacio", organizacion=organization)
    AccesoComedorPWA.objects.create(
        user=users[5], comedor=comedor, activo=True, tipo_asociacion="espacio"
    )
    AccesoOrganizacionPWA.objects.create(user=users[6], organizacion=other, activo=True)
    AccesoComedorPWA.objects.create(
        user=users[6],
        comedor=comedor,
        organizacion=other,
        activo=True,
        tipo_asociacion="organizacion",
    )
    migration = import_module("pwa.migrations.0026_inicializar_acceso_web")
    migration.initialize_web_access(apps, SimpleNamespace(connection=connection))
    for user, expected in zip(users, (True, False, True, True, False, False, True)):
        user.profile.refresh_from_db()
        assert user.profile.acceso_web is expected
