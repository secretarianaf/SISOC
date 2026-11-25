"""Web API (G1 v1) of «Comenzar Admisión»: ``/api/web/comedores/comedores/<pk>/admision/`` (CO07.01).

The endpoint runs the native ``ComedorService.crear_admision_desde_comedor``: these
tests check the persisted effect of each outcome (created or refused with the native
message) and that a refused or rejected request leaves the admissions unchanged.
"""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client

from admisiones.models.admisiones import Admision
from comedores.models import Comedor, Programas
from core import web_gate

pytestmark = pytest.mark.django_db
ROOT = "/api/web/comedores/comedores/"


@pytest.fixture(name="comedor_fixture", autouse=True)
def sin_dobles_del_conftest():
    """Same name as the folder's autouse double: the ficha runs the real services."""


def _ready(user):
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    return user


def _client(username, *codenames):
    usuario = _ready(get_user_model().objects.create_user(username, password="x"))
    for codename in codenames:
        usuario.user_permissions.add(Permission.objects.get(codename=codename))
    client = Client()
    client.force_login(usuario)
    return client


@pytest.fixture(name="lector")
def lector_fixture():
    return _client("lector_admision", "view_comedor")


@pytest.fixture(name="comedor")
def comedor_fixture():
    return Comedor.objects.create(nombre="Comedor Norte")


def _url(comedor):
    return f"{ROOT}{comedor.pk}/admision/"


def _mensajes(client, comedor):
    """What the ficha the redirect lands on shows (it consumes the queued messages)."""
    return client.get(f"{ROOT}{comedor.pk}/").json()["messages"]


def test_incorporacion_creates_the_admission_and_keeps_the_message_for_the_ficha(
    lector, comedor
):
    respuesta = lector.post(_url(comedor), {"admision": "incorporacion"})

    assert respuesta.status_code == 201
    datos = respuesta.json()
    assert datos["created"] is True
    assert datos["redirect"] == f"/comedores/{comedor.pk}"
    assert datos["message"]["level"] == "success"
    admision = Admision.objects.get(comedor=comedor)
    assert admision.tipo == "incorporacion"
    texto = f"Se creó una nueva admisión de tipo '{admision.get_tipo_display()}' correctamente."
    assert datos["message"]["text"] == texto
    assert _mensajes(lector, comedor) == [{"message": texto, "level": "success"}]


def test_renovacion_needs_a_previous_incorporacion_of_any_state(lector, comedor):
    respuesta = lector.post(_url(comedor), {"admision": "renovacion"})

    assert respuesta.status_code == 200
    assert respuesta.json()["created"] is False
    assert respuesta.json()["message"]["level"] == "error"
    assert Admision.objects.filter(comedor=comedor).count() == 0

    Admision.objects.create(comedor=comedor, tipo="incorporacion", activa=False)
    creada = lector.post(_url(comedor), {"admision": "renovacion"})

    assert creada.status_code == 201
    assert Admision.objects.filter(comedor=comedor, tipo="renovacion").count() == 1


def test_a_second_active_incorporacion_is_refused_with_the_native_warning(
    lector, comedor
):
    Admision.objects.create(comedor=comedor, tipo="incorporacion", activa=True)

    respuesta = lector.post(_url(comedor), {"admision": "incorporacion"})

    assert respuesta.status_code == 200
    assert respuesta.json()["created"] is False
    assert respuesta.json()["message"] == {
        "level": "warning",
        "text": "Ya existe una admision de Incorporacion activa para este comedor.",
    }
    assert Admision.objects.filter(comedor=comedor).count() == 1


def test_a_fifth_active_renovacion_is_refused(lector, comedor):
    Admision.objects.create(comedor=comedor, tipo="incorporacion", activa=False)
    for _ in range(4):
        Admision.objects.create(comedor=comedor, tipo="renovacion", activa=True)

    respuesta = lector.post(_url(comedor), {"admision": "renovacion"})

    assert respuesta.status_code == 200
    assert respuesta.json()["created"] is False
    assert respuesta.json()["message"]["text"] == (
        "Ya existen 4 admisiones de Renovacion activas para este comedor."
    )
    assert respuesta.json()["redirect"] == f"/comedores/{comedor.pk}"
    assert Admision.objects.filter(comedor=comedor, tipo="renovacion").count() == 4


def test_a_missing_or_empty_type_is_refused_without_writing(lector, comedor):
    for datos in ({}, {"admision": ""}):
        respuesta = lector.post(_url(comedor), datos)

        assert respuesta.status_code == 200
        assert respuesta.json()["created"] is False
        assert (
            respuesta.json()["message"]["text"]
            == "Debe seleccionar un tipo de admisión."
        )
    assert Admision.objects.filter(comedor=comedor).count() == 0


def test_a_program_with_direct_nomina_does_not_admit_admissions(lector):
    programa = Programas.objects.create(
        nombre="Directo", usa_admision_para_nomina=False
    )
    comedor = Comedor.objects.create(nombre="Nomina directa", programa=programa)

    respuesta = lector.post(_url(comedor), {"admision": "incorporacion"})

    assert respuesta.json()["message"]["text"] == (
        "Este comedor usa nómina directa y no admite admisiones."
    )
    assert Admision.objects.filter(comedor=comedor).count() == 0


def test_only_the_admission_action_is_reachable(lector, comedor):
    """The native ficha POST also discards expedientes: that action is not served here."""
    admision = Admision.objects.create(
        comedor=comedor, tipo="incorporacion", activa=True
    )

    respuesta = lector.post(
        _url(comedor),
        {
            "action": "descartar_expediente",
            "admision_id": admision.pk,
            "motivo_descarte": "x",
        },
    )

    assert respuesta.json()["created"] is False
    admision.refresh_from_db()
    assert admision.enviada_a_archivo is False
    assert admision.estado_legales != "Descartado"


def test_unknown_comedor_is_404_and_writes_nothing(lector, comedor):
    assert (
        lector.post(
            f"{ROOT}999999/admision/", {"admision": "incorporacion"}
        ).status_code
        == 404
    )
    assert Admision.objects.count() == 0


def test_methods_csrf_and_access(comedor):
    sin_permiso = _client("sin_permiso_admision")
    lector = _client("lector_metodos_admision", "view_comedor")

    assert lector.get(_url(comedor)).status_code == 405
    assert lector.put(_url(comedor)).status_code == 405
    assert (
        sin_permiso.post(_url(comedor), {"admision": "incorporacion"}).status_code
        == 403
    )
    anonimo = Client()
    assert anonimo.post(_url(comedor), {"admision": "incorporacion"}).status_code == 401
    usuario = _ready(
        get_user_model().objects.create_user("csrf_admision", password="x")
    )
    usuario.user_permissions.add(Permission.objects.get(codename="view_comedor"))
    csrf = Client(enforce_csrf_checks=True)
    csrf.force_login(usuario)
    assert csrf.post(_url(comedor), {"admision": "incorporacion"}).status_code == 403
    assert Admision.objects.count() == 0


def test_pending_web_requirement_is_reported_and_a_forged_header_is_ignored(comedor):
    usuario = get_user_model().objects.create_superuser(
        "pendiente_admision", password="x"
    )
    usuario.profile.acceso_web = True
    usuario.profile.must_change_password = True
    usuario.profile.save()
    client = Client()
    client.force_login(usuario)
    url = _url(comedor)
    falso = web_gate.sign(
        audience="comedores",
        user_pk=usuario.pk,
        session_key=client.cookies["sessionid"].value,
        method="POST",
        target=url,
    )

    respuesta = client.post(
        url, {"admision": "incorporacion"}, HTTP_X_SISOC_WEB_GATE=falso, RAW_URI=url
    )

    assert respuesta.status_code == 403
    assert respuesta.json()["state"] == "password_change_required"
    assert Admision.objects.count() == 0
