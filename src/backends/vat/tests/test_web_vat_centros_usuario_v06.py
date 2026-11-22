"""V06.02: web API de «Generar usuario» de un centro (``/api/web/vat/centros-usuarios/<pk>/generar/``). Datos sintéticos."""

import itertools
import types

import pytest
from django.contrib.auth.models import Group, Permission, User
from django.core import mail
from django.test import Client, override_settings
from rest_framework.test import APIClient

from config.urls_all import urlpatterns as monolith_patterns
from users.models import Profile
from VAT.models import Centro
from VAT.services.access_scope import GRUPO_REFERENTE_CENTRO_VAT
from VAT.web_preview_vat_centros_lista import centros_preview_patterns

pytestmark = pytest.mark.django_db

ROOT = "/api/web/vat/centros-usuarios/"
_COUNTER = itertools.count()
INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)


@pytest.fixture(autouse=True)
def _grupo_cfp(settings):
    """Las data migrations no corren en tests (TEST MIGRATE=False)."""
    settings.DOMINIO = "http://testserver"
    Group.objects.get_or_create(name=GRUPO_REFERENTE_CENTRO_VAT)


def _client(*, delega=False, csrf=False):
    """A user with ``VAT.view_centro``; ``delega`` makes it a superuser allowed to hand out the CFP group."""
    numero = next(_COUNTER)
    if delega:
        user = User.objects.create_superuser(
            f"gu{numero}", email=f"gu{numero}@example.com", password="x"
        )
        perfil, _ = Profile.objects.get_or_create(user=user)
        perfil.grupos_asignables.add(Group.objects.get(name=GRUPO_REFERENTE_CENTRO_VAT))
    else:
        user = User.objects.create_user(f"gu{numero}", email=f"gu{numero}@example.com")
        user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="VAT", codename="view_centro"
            )
        )
    client = APIClient(enforce_csrf_checks=csrf)
    client.force_login(user)
    return client


def _centro(**extra):
    return Centro.objects.create(
        nombre="CFP 401",
        codigo=f"06{next(_COUNTER):07d}",
        nombre_referente="Lia",
        apellido_referente="Paz",
        correo_referente="lia@example.com",
        **extra,
    )


def _datos(**extra):
    return {
        "first_name": "Ana",
        "last_name": "Gomez",
        "email": "ana@example.com",
        **extra,
    }


def test_access_follows_the_route_rule_and_the_native_predicate():
    centro = _centro()
    url = f"{ROOT}{centro.pk}/generar/"
    assert APIClient().get(url).status_code == 401
    sin_permiso = User.objects.create_user("gu-sin", email="sin@example.com")
    cliente = APIClient()
    cliente.force_login(sin_permiso)
    assert cliente.get(url).status_code == 403
    # with the route permission only, the native predicate (edit the centro, delegate the CFP group) still refuses
    assert _client().get(url).status_code == 403
    assert _client().post(url, _datos()).status_code == 403
    assert not User.objects.filter(email="ana@example.com").exists()
    assert _client(delega=True).get(url).status_code == 200
    assert _client(delega=True).get(f"{ROOT}999999/generar/").status_code == 404


def test_get_projects_the_prefilled_form_and_the_quota():
    centro = _centro()
    data = _client(delega=True).get(f"{ROOT}{centro.pk}/generar/").json()
    assert data["centro"] == {
        "id": centro.pk,
        "nombre": "CFP 401",
        "url": f"/vat/centros/{centro.pk}/",
    }
    assert data["usuarios_restantes"] == 10
    campos = {f["name"]: f for f in data["fields"]}
    assert list(campos) == ["first_name", "last_name", "email"]
    assert [campos[n]["value"] for n in campos] == ["Lia", "Paz", "lia@example.com"]
    assert campos["first_name"]["attrs"]["maxlength"] == "150"
    assert (
        campos["email"]["help_text"]
        == "Se usará como usuario y para enviarle las credenciales."
    )
    assert data["urls"]["cancelar"] == f"/vat/centros/{centro.pk}/"
    assert data["non_field_errors"] == []
    # once the centro has a user, the next form starts blank
    centro.referentes.add(User.objects.create_user("ya", email="ya@example.com"))
    siguiente = _client(delega=True).get(f"{ROOT}{centro.pk}/generar/").json()
    assert [f["value"] for f in siguiente["fields"]] == ["", "", ""]
    assert siguiente["usuarios_restantes"] == 9


def test_valid_post_creates_the_user_and_answers_the_credentials_once():
    centro = _centro()
    client = _client(delega=True)
    url = f"{ROOT}{centro.pk}/generar/"
    respuesta = client.post(url, _datos())
    assert respuesta.status_code == 201
    assert "no-store" in respuesta["Cache-Control"]
    data = respuesta.json()
    nuevo = User.objects.get(email="ana@example.com")
    assert data["usuario"] == {"username": nuevo.username, "email": "ana@example.com"}
    assert data["password"] == nuevo.profile.temporary_password_plaintext
    assert data["email_enviado"] is True
    assert data["puede_generar_otro"] is True
    assert data["urls"] == {"generar": f"/vat/centros/{centro.pk}/generar-usuario/"}
    assert [m["message"] for m in data["messages"]] == [
        f"Usuario «{nuevo.username}» creado correctamente."
    ]
    assert nuevo.groups.filter(name=GRUPO_REFERENTE_CENTRO_VAT).exists()
    assert centro.referentes.filter(pk=nuevo.pk).exists()
    assert len(mail.outbox) == 1
    # the password is in no later response
    assert data["password"] not in client.get(url).content.decode()


def test_invalid_post_is_400_with_the_bound_form_and_writes_nothing():
    centro = _centro()
    url = f"{ROOT}{centro.pk}/generar/"
    respuesta = _client(delega=True).post(url, _datos(email="no-es-un-email"))
    assert respuesta.status_code == 400
    campos = {f["name"]: f for f in respuesta.json()["fields"]}
    assert campos["email"]["value"] == "no-es-un-email"
    assert campos["email"]["errors"] == [
        "Introduzca una dirección de correo electrónico válida."
    ]
    vacio = _client(delega=True).post(url, _datos(first_name=""))
    assert vacio.status_code == 400
    assert {f["name"]: f for f in vacio.json()["fields"]}["first_name"]["errors"] == [
        "Este campo es requerido."
    ]
    assert (
        User.objects.filter(email__in=["ana@example.com", "no-es-un-email"]).count()
        == 0
    )
    assert not centro.referentes.exists()


def test_post_without_csrf_is_403_and_a_full_quota_is_refused_by_the_native_predicate():
    centro = _centro()
    url = f"{ROOT}{centro.pk}/generar/"
    assert _client(delega=True, csrf=True).post(url, _datos()).status_code == 403
    assert not User.objects.filter(email="ana@example.com").exists()
    for numero in range(10):
        centro.referentes.add(
            User.objects.create_user(f"lleno{numero}", email=f"l{numero}@example.com")
        )
    assert _client(delega=True).get(url).status_code == 403
    assert _client(delega=True).post(url, _datos()).status_code == 403
    assert not User.objects.filter(email="ana@example.com").exists()


@pytest.fixture(name="preview")
def preview_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    (tmp_path / "assets" / "app-1.js").write_text("console.log(1);", encoding="utf-8")
    module = types.ModuleType("vat_centros_usuario_preview_test_urls")
    module.urlpatterns = centros_preview_patterns(tmp_path) + list(monolith_patterns)
    with override_settings(ROOT_URLCONF=module):
        yield


@pytest.mark.usefixtures("preview")
def test_preview_entry_serves_the_index_behind_the_native_guards():
    centro = _centro()
    url = f"/vat/centros/{centro.pk}/generar-usuario/"
    assert Client().get(url).status_code == 403
    assert _client().get(url).status_code == 403
    respuesta = _client(delega=True).get(url)
    assert respuesta.status_code == 200
    assert '/vat/react/assets/app-1.js"' in respuesta.content.decode()
    assert "no-store" in respuesta["Cache-Control"]
    assert (
        _client(delega=True).get("/vat/centros/999999/generar-usuario/").status_code
        == 404
    )
