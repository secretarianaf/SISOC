"""Web API (G1 v1) of the comedor baja: ``/api/web/comedores/comedores/<pk>/baja/`` (CO07.01)."""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client

from comedores.models import Comedor
from core import web_gate

pytestmark = pytest.mark.django_db
LISTA = "/api/web/comedores/comedores/"


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


@pytest.fixture(name="gestor")
def gestor_fixture():
    return _client("gestor_baja_comedor", "delete_comedor", "view_comedor")


@pytest.fixture(name="comedor")
def comedor_fixture():
    return Comedor.objects.create(nombre="Comedor a dar de baja")


def _url(comedor):
    return f"{LISTA}{comedor.pk}/baja/"


def test_get_shows_the_native_confirmation_without_writing(gestor, comedor):
    datos = gestor.get(_url(comedor)).json()

    assert datos["id"] == comedor.pk
    assert datos["nombre"] == "Comedor a dar de baja"
    assert datos["urls"] == {
        "cancel": f"/comedores/{comedor.pk}",
        "list": "/comedores/listar",
    }
    assert datos["cascade_preview"]["total_afectados"] >= 1
    assert datos["messages"] == []
    assert Comedor.objects.filter(pk=comedor.pk).exists()


def test_post_does_the_logical_baja_and_keeps_the_native_message_for_the_list(
    gestor, comedor
):
    respuesta = gestor.post(_url(comedor))

    assert respuesta.status_code == 200
    assert respuesta.json() == {"redirect": "/comedores/listar"}
    assert not Comedor.objects.filter(pk=comedor.pk).exists()
    fila = Comedor.all_objects.get(pk=comedor.pk)
    assert fila.deleted_at is not None
    assert fila.deleted_by.username == "gestor_baja_comedor"
    # The list the redirect lands on consumes the native message.
    assert gestor.get(LISTA).json()["messages"] == [
        {"message": "Comedor dado de baja correctamente.", "level": "success"}
    ]


def test_a_rejected_baja_leaves_the_comedor_unchanged(comedor):
    sin_permiso = _client("sin_permiso_baja", "view_comedor")

    assert sin_permiso.get(_url(comedor)).status_code == 403
    assert sin_permiso.post(_url(comedor)).status_code == 403
    assert Comedor.objects.get(pk=comedor.pk).deleted_at is None


def test_unknown_comedor_is_404_and_post_is_not_destructive(gestor, comedor):
    assert gestor.get(f"{LISTA}999999/baja/").status_code == 404
    assert gestor.post(f"{LISTA}999999/baja/").status_code == 404
    assert Comedor.objects.filter(pk=comedor.pk).exists()


def test_other_methods_are_not_served(gestor, comedor):
    for metodo in ("put", "delete"):
        assert getattr(gestor, metodo)(_url(comedor)).status_code == 405, metodo
    assert Comedor.objects.filter(pk=comedor.pk).exists()


def test_post_requires_the_csrf_token(comedor):
    usuario = _ready(get_user_model().objects.create_user("csrf_baja", password="x"))
    usuario.user_permissions.add(Permission.objects.get(codename="delete_comedor"))
    client = Client(enforce_csrf_checks=True)
    client.force_login(usuario)

    assert client.post(_url(comedor)).status_code == 403
    assert Comedor.objects.filter(pk=comedor.pk).exists()


def test_anonymous_gets_401_json(client, comedor):
    respuesta = client.get(_url(comedor))

    assert respuesta.status_code == 401
    assert respuesta.json() == {"detail": web_gate.DETAIL_UNAUTHENTICATED}
    assert client.post(_url(comedor)).status_code == 401
    assert Comedor.objects.filter(pk=comedor.pk).exists()


def test_pending_web_requirement_is_reported_and_a_forged_header_is_ignored(comedor):
    usuario = get_user_model().objects.create_superuser("pendiente_baja", password="x")
    usuario.profile.acceso_web = True
    usuario.profile.must_change_password = True
    usuario.profile.save()
    client = Client()
    client.force_login(usuario)
    falso = web_gate.sign(
        audience="comedores",
        user_pk=usuario.pk,
        session_key=client.cookies["sessionid"].value,
        method="POST",
        target=_url(comedor),
    )

    respuesta = client.post(
        _url(comedor), HTTP_X_SISOC_WEB_GATE=falso, RAW_URI=_url(comedor)
    )

    assert respuesta.status_code == 403
    assert respuesta.json()["state"] == "password_change_required"
    assert Comedor.objects.filter(pk=comedor.pk).exists()
