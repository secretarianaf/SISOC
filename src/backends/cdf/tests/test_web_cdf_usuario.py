"""Web API (G1 v1) of the CDF referente user generation (CDF04.03).

The endpoint runs ``GenerarUsuarioCDFView``; the tests pin the native check
order (``view_centro`` 403, missing centre 404, delegation/territory/quota 403),
the persisted effects through explicit fields, the CR1 projection of the 201
and the native texts verbatim. Email delivery is the local in-memory backend.
"""

import types

import pytest
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.contrib.messages import get_messages
from django.core import mail
from django.core.exceptions import ValidationError
from django.test import Client, override_settings

from centrodefamilia.models import AccesoCDF, Centro
from centrodefamilia.web_preview import cdf_preview_patterns
from config.urls_all import urlpatterns as monolith_patterns
from core.constants import UserGroups
from core.models import Provincia

GRUPO = UserGroups.CDF_REFERENTE_CENTRO
CR1_KEYS = {"usuario", "password", "email_enviado", "puede_generar_otro", "message"}
INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)

pytestmark = pytest.mark.django_db


def _url(pk):
    return f"/api/web/cdf/centros/{pk}/generar-usuario/"


@pytest.fixture(autouse=True)
def _grupo(db):
    Group.objects.get_or_create(name=GRUPO)


@pytest.fixture(name="provincia")
def provincia_fixture():
    return Provincia.objects.create(nombre="Provincia Usuario")


def _actor(username, provincia, *, view=True, delega=True, provincial=True):
    user = User.objects.create_user(username)
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.es_usuario_provincial = provincial
    profile.provincia = provincia
    profile.save()
    if delega:
        profile.grupos_asignables.add(Group.objects.get(name=GRUPO))
    if view:
        user.user_permissions.add(
            Permission.objects.get(
                content_type=ContentType.objects.get_for_model(Centro),
                codename="view_centro",
            )
        )
    return User.objects.get(pk=user.pk)


def _client(user, csrf=False):
    client = Client(enforce_csrf_checks=csrf)
    client.force_login(user)
    return client


def _centro(provincia, nombre="CDF Usuario"):
    return Centro.objects.create(
        nombre=nombre,
        tipo="faro",
        codigo=nombre[:20],
        provincia=provincia,
        domicilio_actividad="Domicilio",
        telefono="011",
        celular="15",
        correo="c@example.com",
        nombre_referente="Lia",
        apellido_referente="Paz",
        telefono_referente="012",
        correo_referente="lia@example.com",
    )


@pytest.fixture(name="centro")
def centro_fixture(provincia):
    return _centro(provincia)


@pytest.fixture(name="actor")
def actor_fixture(provincia):
    return _actor("prov_usuario", provincia)


DATOS = {"first_name": " Ana ", "last_name": "Gómez", "email": "ana.web@example.com"}


def test_get_first_user_preloads_the_centre_referente(actor, centro):
    respuesta = _client(actor).get(_url(centro.pk))

    assert respuesta.status_code == 200
    assert respuesta["Cache-Control"] == "private, no-store"
    assert "Cookie" in respuesta["Vary"]
    data = respuesta.json()
    assert data["centro"] == {"id": centro.pk, "nombre": "CDF Usuario"}
    assert data["grupo"] == "CDF - Referente centro"
    assert data["usuarios_restantes"] == 10
    assert data["initial"] == {
        "first_name": "Lia",
        "last_name": "Paz",
        "email": "lia@example.com",
    }
    campos = {f["name"]: f for f in data["fields"]}
    assert list(campos) == ["first_name", "last_name", "email"]
    assert campos["first_name"]["label"] == "Nombre"
    assert campos["first_name"]["value"] == "Lia"
    assert campos["first_name"]["attrs"] == {"maxlength": "150"}
    assert campos["email"]["widget"] == "email"
    assert (
        campos["email"]["help_text"]
        == "Se usará como usuario y para enviarle las credenciales."
    )
    assert data["errors"] == {} and data["non_field_errors"] == []


def test_get_second_user_starts_empty_even_with_an_inactive_access(
    actor, centro, provincia
):
    previo = _actor("previo", provincia, view=False)
    AccesoCDF.objects.create(user=previo, centro=centro, activo=False)

    data = _client(actor).get(_url(centro.pk)).json()

    assert data["initial"] == {}
    assert [f["value"] for f in data["fields"]] == ["", "", ""]
    assert data["usuarios_restantes"] == 10


def test_post_creates_the_user_and_returns_only_the_cr1_projection(actor, centro):
    client = _client(actor)

    respuesta = client.post(_url(centro.pk), DATOS)

    assert respuesta.status_code == 201
    assert respuesta["Cache-Control"] == "private, no-store"
    data = respuesta.json()
    assert set(data) == CR1_KEYS
    nuevo = User.objects.get(email__iexact="ana.web@example.com")
    assert (nuevo.first_name, nuevo.last_name) == ("Ana", "Gómez")
    assert nuevo.groups.filter(name=GRUPO).exists()
    acceso = AccesoCDF.objects.get(user=nuevo)
    assert (acceso.centro_id, acceso.creado_por_id, acceso.activo) == (
        centro.pk,
        actor.pk,
        True,
    )
    assert data["usuario"] == {"username": nuevo.username, "email": nuevo.email}
    assert data["password"] == nuevo.profile.temporary_password_plaintext
    assert nuevo.profile.must_change_password is True
    assert data["email_enviado"] is True
    assert data["puede_generar_otro"] is True
    assert data["message"] == f"Usuario «{nuevo.username}» creado correctamente."
    assert len(mail.outbox) == 1 and mail.outbox[0].to == ["ana.web@example.com"]
    # The native success message is consumed: it never reaches a later page.
    siguiente = client.get(f"/centrodefamilia/centros/{centro.pk}/")
    assert not list(get_messages(siguiente.wsgi_request))


def test_post_with_failed_email_still_creates_the_user(actor, centro, monkeypatch):
    def falla(**_kwargs):
        raise OSError("smtp caído")

    monkeypatch.setattr("users.services_generate_user.send_mail", falla)

    respuesta = _client(actor).post(_url(centro.pk), DATOS)

    assert respuesta.status_code == 201
    assert respuesta.json()["email_enviado"] is False
    assert User.objects.filter(email__iexact="ana.web@example.com").exists()


def test_post_last_slot_reports_no_other_generation(actor, centro, provincia):
    for n in range(9):
        AccesoCDF.objects.create(
            user=_actor(f"ocupado{n}", provincia, view=False), centro=centro
        )

    data = _client(actor).post(_url(centro.pk), DATOS).json()

    assert data["puede_generar_otro"] is False
    assert _client(actor).get(_url(centro.pk)).status_code == 403


def test_invalid_form_answers_400_without_creating(actor, centro):
    antes = User.objects.count()

    respuesta = _client(actor).post(
        _url(centro.pk), {"first_name": "", "last_name": "X", "email": "no-mail"}
    )

    assert respuesta.status_code == 400
    data = respuesta.json()
    assert data["errors"]["first_name"][0]["message"] == "Este campo es requerido."
    assert data["errors"]["email"][0]["code"] == "invalid"
    assert {f["name"]: f["value"] for f in data["fields"]}["email"] == "no-mail"
    assert User.objects.count() == antes
    assert not AccesoCDF.objects.exists()


def test_service_validation_error_is_a_non_field_error(actor, centro, monkeypatch):
    def rechaza(**_kwargs):
        raise ValidationError("Se alcanzó el máximo de usuarios para este CDF.")

    monkeypatch.setattr(
        "centrodefamilia.views.generar_usuario.generar_usuario_delegado", rechaza
    )

    respuesta = _client(actor).post(_url(centro.pk), DATOS)

    assert respuesta.status_code == 400
    assert respuesta.json()["non_field_errors"] == [
        "Se alcanzó el máximo de usuarios para este CDF."
    ]


def test_access_order_matches_the_native_view(actor, centro, provincia):
    otra = Provincia.objects.create(nombre="Otra Provincia")
    sin_view = _actor("sin_view", provincia, view=False)
    sin_delegar = _actor("sin_delegar", provincia, delega=False)
    fuera = _actor("fuera", otra)
    lleno = _centro(provincia, "CDF Lleno")
    for n in range(10):
        AccesoCDF.objects.create(
            user=_actor(f"lleno{n}", provincia, view=False), centro=lleno
        )
    casos = [
        (sin_view, centro.pk, 403),
        (sin_view, 999999, 403),
        (actor, 999999, 404),
        (sin_delegar, centro.pk, 403),
        (fuera, centro.pk, 403),
        (actor, lleno.pk, 403),
    ]
    for user, pk, esperado in casos:
        client = _client(user)
        native = client.get(f"/centrodefamilia/centros/{pk}/generar-usuario/")
        assert native.status_code == esperado, (user.username, pk)
        assert client.get(_url(pk)).status_code == esperado, (user.username, pk)
        assert client.post(_url(pk), DATOS).status_code == esperado
    assert not User.objects.filter(email__iexact="ana.web@example.com").exists()
    centro.delete()
    assert _client(actor).get(_url(centro.pk)).status_code == 404


def test_session_and_csrf_are_required(actor, centro):
    assert Client().get(_url(centro.pk)).status_code == 401
    assert Client().post(_url(centro.pk), DATOS).status_code == 401
    respuesta = _client(actor, csrf=True).post(_url(centro.pk), DATOS)
    assert respuesta.status_code == 403
    assert not User.objects.filter(email__iexact="ana.web@example.com").exists()
    assert _client(actor).put(_url(centro.pk), DATOS).status_code == 405


def test_preview_entry_keeps_the_native_guards(tmp_path, actor, centro, provincia):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    module = types.ModuleType("cdf_usuario_preview_urls")
    module.urlpatterns = cdf_preview_patterns(tmp_path) + list(monolith_patterns)
    url = f"/centrodefamilia/centros/{centro.pk}/generar-usuario/"

    with override_settings(ROOT_URLCONF=module):
        entrada = _client(actor).get(url)
    assert entrada.status_code == 200
    assert '/centrodefamilia/react/assets/app-1.js"' in entrada.content.decode()
    assert "no-store" in entrada["Cache-Control"]
    assert "csrftoken" in entrada.cookies

    fuera = _actor("fuera_preview", Provincia.objects.create(nombre="Lejana"))
    for client, path in (
        (Client(), url),
        (_client(_actor("sin_view_preview", provincia, view=False)), url),
        (_client(fuera), url),
        (_client(actor), "/centrodefamilia/centros/999999/generar-usuario/"),
    ):
        native = client.get(path)
        with override_settings(ROOT_URLCONF=module):
            preview = client.get(path)
        assert (preview.status_code, preview.get("Location")) == (
            native.status_code,
            native.get("Location"),
        ), path
        assert native.status_code in (302, 403, 404)
