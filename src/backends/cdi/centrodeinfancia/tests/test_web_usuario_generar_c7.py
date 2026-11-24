"""CDI01.01 "Generar usuario" and the RENAPER block lookup: web API (G1 v1).

The API inherits ``GenerarUsuarioCDIView``, so the form, the signed RENAPER
token, the cupo, the responsable rule and ``generar_usuario_delegado`` are the
native ones. The temporary password is returned once, by the POST that creates
the user, and never by a GET, a rejected POST or the log.
"""

import logging
from unittest import mock
from urllib.parse import urlencode

import pytest
from django.contrib.auth.models import Group, Permission, User
from django.core import mail
from django.test import Client
from django.test.client import MULTIPART_CONTENT as MULTIPART
from django.urls import reverse

from centrodeinfancia.models import AccesoCDI, CentroDeInfancia
from centrodeinfancia.services_renaper_bloques import crear_token
from core import web_gate
from core.constants import UserGroups
from core.models import Provincia
from users.models import Profile

API = "/api/web/cdi/"
CONSULTA_RENAPER = (
    "centrodeinfancia.services_renaper_bloques.obtener_datos_ciudadano_desde_renaper"
)
VETO = "El rol Auditoría tiene acceso de solo lectura."
VALORES = {
    "dni": 28456789,
    "last_name": "Pérez",
    "first_name": "Luis",
    "cuil": "20284567898",
}

pytestmark = pytest.mark.django_db


def _ready(user):
    profile = Profile.objects.get_or_create(user=user)[0]
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    return User.objects.get(pk=user.pk)


def _usuario(username, *, perms=("centrodeinfancia.view_centrodeinfancia",), **extra):
    user = User.objects.create_user(username=username, **extra)
    for code in perms:
        app, codename = code.split(".")
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label=app, codename=codename)
        )
    return _ready(user)


class WebClient(Client):
    """Posts to the web API URL-encoded, as the React page does."""

    def post(self, path, data=None, content_type=None, **extra):
        if content_type is None and str(path).startswith(API):
            return super().post(
                path,
                urlencode(data or {}),
                content_type="application/x-www-form-urlencoded",
                **extra,
            )
        return super().post(path, data, content_type=content_type or MULTIPART, **extra)


def _cliente(user, **kwargs):
    client = WebClient(**kwargs)
    client.force_login(user)
    return client


@pytest.fixture(autouse=True)
def _grupo_referente():
    Group.objects.get_or_create(name=UserGroups.CDI_REFERENTE_CENTRO)


@pytest.fixture(autouse=True)
def _correo(settings):
    settings.DOMINIO = "http://testserver"
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"


@pytest.fixture(name="centro")
def centro_fixture():
    return CentroDeInfancia.objects.create(
        nombre="CDI Sintético",
        provincia=Provincia.objects.create(nombre="Mendoza"),
        nombre_referente="Ana",
        apellido_referente="Gómez",
        email_referente="ana@example.com",
        dni_referente="30123456",
    )


@pytest.fixture(name="admin")
def admin_fixture():
    return _ready(User.objects.create_superuser("c7-admin", "", "test1234"))


def _url(pk):
    return f"{API}centros/{pk}/usuarios/generar/"


def _renaper(bloque="usuario_cdi"):
    return f"{API}renaper/{bloque}/"


def _estado():
    return (
        list(User.objects.order_by("pk").values_list("pk", "username")),
        list(AccesoCDI.objects.order_by("pk").values_list("pk", "user_id")),
        len(mail.outbox),
    )


def _datos(user, **extra):
    return {
        "first_name": "Alterado",
        "last_name": "Alterado",
        "email": "luis@example.com",
        "dni": "99999999",
        "cuil": "20284567898",
        "renaper_token_usuario_cdi": crear_token("usuario_cdi", user, VALORES),
        **extra,
    }


# --- Form ---------------------------------------------------------------------


def test_form_projects_the_native_fields_and_the_renaper_block(centro, admin):
    respuesta = _cliente(admin).get(_url(centro.pk))
    cuerpo = respuesta.json()

    assert respuesta.status_code == 200
    assert respuesta["Cache-Control"] == "private, no-store"
    assert cuerpo["centro"]["nombre"] == "CDI Sintético"
    assert cuerpo["usuarios_restantes"] > 0
    assert [campo["name"] for campo in cuerpo["fields"]] == [
        "dni",
        "first_name",
        "last_name",
        "cuil",
        "email",
    ]
    por_nombre = {campo["name"]: campo for campo in cuerpo["fields"]}
    # The first user is prefilled with the referente of the ficha.
    assert por_nombre["first_name"]["value"] == "Ana"
    assert por_nombre["dni"]["value"] == "30123456"
    assert por_nombre["email"]["value"] == "ana@example.com"
    assert por_nombre["email"]["help_text"].startswith("Se usará para enviarle")
    assert cuerpo["renaper"]["bloque"] == "usuario_cdi"
    assert cuerpo["renaper"]["campos"] == ["dni", "last_name", "first_name", "cuil"]
    assert cuerpo["renaper"]["token"] == ""
    assert "password" not in respuesta.content.decode()


def test_verified_identity_of_the_ficha_arrives_locked(centro, admin):
    centro.cuil_referente = "27301234568"
    centro.campos_verificados_renaper = [
        "nombre_referente",
        "apellido_referente",
        "dni_referente",
        "cuil_referente",
    ]
    centro.save()

    cuerpo = _cliente(admin).get(_url(centro.pk)).json()

    por_nombre = {campo["name"]: campo for campo in cuerpo["fields"]}
    assert cuerpo["renaper"]["modo"] == "verificado"
    assert cuerpo["renaper"]["verificado"] is True
    assert por_nombre["dni"]["disabled"] is True
    assert por_nombre["dni"]["renaper"] is True
    assert por_nombre["email"]["disabled"] is False


def test_unknown_centre_is_404_and_a_plain_viewer_is_403(centro):
    assert _cliente(_usuario("c7-ok")).get(_url(centro.pk + 999)).status_code == 404
    respuesta = _cliente(_usuario("c7-plano")).get(_url(centro.pk))
    assert respuesta.status_code == 403
    assert respuesta.json()["detail"]


def test_permission_less_user_is_rejected_before_the_view(centro):
    sin_permiso = _usuario("c7-sin-permiso", perms=())

    assert _cliente(sin_permiso).get(_url(centro.pk)).status_code == 403
    assert _cliente(sin_permiso).post(_url(centro.pk), {}).status_code == 403
    assert not User.objects.filter(email="luis@example.com").exists()


# --- Generate -----------------------------------------------------------------


def test_post_creates_the_user_and_returns_the_password_once(centro, admin, caplog):
    cliente = _cliente(admin)
    with caplog.at_level(logging.DEBUG):
        respuesta = cliente.post(_url(centro.pk), _datos(admin))

    cuerpo = respuesta.json()
    nuevo = User.objects.get(email="luis@example.com")
    acceso = AccesoCDI.objects.get(centro=centro)
    assert respuesta.status_code == 200
    assert respuesta["Cache-Control"] == "private, no-store"
    # RENAPER identity comes from the token, not from the POST.
    assert (nuevo.first_name, nuevo.last_name) == ("Luis", "Pérez")
    assert nuevo.profile.dni == "28456789"
    assert acceso.user_id == nuevo.pk and acceso.es_responsable is True
    assert cuerpo["ok"] is True
    assert cuerpo["usuario"] == {"username": nuevo.username, "email": nuevo.email}
    assert cuerpo["centro"]["id"] == centro.pk
    assert cuerpo["email_enviado"] is True
    assert cuerpo["password"]
    assert nuevo.check_password(cuerpo["password"])
    # Only what the native result page shows: no user record, hash or profile.
    assert set(cuerpo) == {
        "ok",
        "centro",
        "usuario",
        "password",
        "email_enviado",
        "puede_generar_otro",
        "urls",
        "messages",
    }
    assert cuerpo["messages"] == [
        {
            "message": f"Usuario «{nuevo.username}» creado correctamente.",
            "level": "success",
        }
    ]
    # The password is not in the log; a later GET never repeats it.
    assert cuerpo["password"] not in caplog.text
    nuevo_get = cliente.get(_url(centro.pk))
    assert cuerpo["password"] not in nuevo_get.content.decode()
    assert nuevo.password not in respuesta.content.decode()


def test_rejected_post_changes_nothing_and_has_no_password(centro, admin):
    antes = _estado()

    respuesta = _cliente(admin).post(
        _url(centro.pk),
        {"first_name": "", "last_name": "x", "email": "no", "dni": "1", "cuil": "2"},
    )

    cuerpo = respuesta.json()
    assert respuesta.status_code == 400
    assert cuerpo["fields"][0]["errors"][0]["message"] == (
        "Ingrese un DNI válido (solo números)."
    )
    assert "password" not in cuerpo
    assert _estado() == antes


def test_a_forged_token_of_another_user_is_ignored(centro, admin):
    otro = _usuario("c7-otro")
    antes = _estado()

    respuesta = _cliente(admin).post(
        _url(centro.pk),
        {
            "first_name": "",
            "last_name": "",
            "email": "luis@example.com",
            "dni": "28456789",
            "cuil": "20284567898",
            "renaper_token_usuario_cdi": crear_token("usuario_cdi", otro, VALORES),
        },
    )

    assert respuesta.status_code == 400
    assert _estado() == antes


def test_a_responsable_generates_for_the_own_centre_only(centro):
    responsable = _usuario("c7-resp")
    responsable.groups.add(Group.objects.get(name=UserGroups.CDI_REFERENTE_CENTRO))
    AccesoCDI.objects.create(user=responsable, centro=centro, es_responsable=True)
    ajeno = CentroDeInfancia.objects.create(nombre="Otro CDI")

    propio = _cliente(responsable).post(_url(centro.pk), _datos(responsable))
    otro = _cliente(responsable).post(_url(ajeno.pk), _datos(responsable))

    assert propio.status_code == 200
    assert otro.status_code == 403
    assert not AccesoCDI.objects.filter(centro=ajeno).exists()


def test_full_centre_has_no_cupo_and_is_403(centro, admin):
    with mock.patch("centrodeinfancia.access.usuarios_cdi_restantes", return_value=0):
        respuesta = _cliente(admin).post(_url(centro.pk), _datos(admin))

    assert respuesta.status_code == 403
    assert not User.objects.filter(email="luis@example.com").exists()


# --- Gate ---------------------------------------------------------------------


def test_anonymous_gets_401_json(centro):
    for respuesta in (
        Client().get(_url(centro.pk)),
        Client().post(_url(centro.pk), {}),
        Client().get(_renaper() + "?dni=28456789"),
    ):
        assert respuesta.status_code == 401
        assert respuesta.json() == {"detail": web_gate.DETAIL_UNAUTHENTICATED}
    assert AccesoCDI.objects.count() == 0


def test_post_without_csrf_token_is_403(centro, admin):
    cliente = _cliente(admin, enforce_csrf_checks=True)

    respuesta = cliente.post(_url(centro.pk), _datos(admin))

    assert respuesta.status_code == 403
    assert not User.objects.filter(email="luis@example.com").exists()


def test_other_methods_and_body_formats_are_refused(centro, admin):
    cliente = _cliente(admin)

    assert cliente.put(_url(centro.pk)).status_code == 405
    respuesta = cliente.post(_url(centro.pk), "{}", content_type="application/json")
    assert respuesta.status_code == 415
    assert not AccesoCDI.objects.exists()


# --- RENAPER block lookup -----------------------------------------------------


def _respuesta_renaper():
    return {
        "success": True,
        "message": "Datos obtenidos desde RENAPER.",
        "data": {
            "documento": 28456789,
            "apellido": "Pérez",
            "nombre": "Luis",
            "cuil_cuit": "20284567898",
        },
    }


def test_lookup_returns_values_and_a_token_bound_to_the_actor(admin):
    with mock.patch(CONSULTA_RENAPER, return_value=_respuesta_renaper()) as consulta:
        respuesta = _cliente(admin).get(_renaper() + "?dni=28456789")

    cuerpo = respuesta.json()
    assert respuesta.status_code == 200
    assert respuesta["Cache-Control"] == "private, no-store"
    assert consulta.call_args.args == ("28456789",)
    assert cuerpo["success"] is True
    assert cuerpo["valores"] == {
        "dni": 28456789,
        "last_name": "Pérez",
        "first_name": "Luis",
        "cuil": "20284567898",
    }
    assert cuerpo["token"]
    assert "datos_api" not in cuerpo


def test_lookup_failures_are_the_native_ones(admin):
    cliente = _cliente(admin)
    with mock.patch(
        CONSULTA_RENAPER, return_value={"success": False, "message": "No existe."}
    ):
        no_encontrado = cliente.get(_renaper() + "?dni=28456789")
    with mock.patch(CONSULTA_RENAPER, side_effect=RuntimeError("boom")):
        caido = cliente.get(_renaper() + "?dni=28456789")

    assert no_encontrado.status_code == 400
    assert no_encontrado.json() == {"success": False, "message": "No existe."}
    assert caido.status_code == 400
    assert caido.json()["message"] == "No se pudo consultar RENAPER."
    assert cliente.get(_renaper("inexistente") + "?dni=1").status_code == 404


def test_lookup_is_rate_limited_per_user(admin):
    cliente = _cliente(admin)
    with mock.patch(CONSULTA_RENAPER, return_value=_respuesta_renaper()):
        for _ in range(30):
            assert cliente.get(_renaper() + "?dni=28456789").status_code == 200
        respuesta = cliente.get(_renaper() + "?dni=28456789")

    assert respuesta.status_code == 429
    assert respuesta.json()["message"].startswith("Demasiadas consultas a RENAPER.")


def test_lookup_keeps_the_auditor_veto_and_the_url_permission():
    auditor = _usuario(
        "c7-auditor", perms=("centrodeinfancia.change_centrodeinfancia",)
    )
    auditor.groups.add(Group.objects.get_or_create(name=UserGroups.SIMEPI_AUDITORIA)[0])
    sin_permiso = _usuario("c7-solo-ver")

    with mock.patch(CONSULTA_RENAPER) as consulta:
        veto = _cliente(auditor).get(_renaper() + "?dni=28456789")
        denegado = _cliente(sin_permiso).get(_renaper() + "?dni=28456789")

    assert veto.status_code == 403
    assert veto.json() == {"detail": VETO}
    assert denegado.status_code == 403
    consulta.assert_not_called()


def test_lookup_only_answers_get(admin):
    respuesta = _cliente(admin).post(_renaper(), {})

    assert respuesta.status_code == 405
    assert respuesta["Allow"] == "GET, HEAD"


def test_lookup_url_is_published_under_the_cdi_prefix():
    assert (
        reverse("centrodeinfancia_web_renaper_bloque", args=["usuario_cdi"])
        == _renaper()
    )
