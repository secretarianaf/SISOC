"""Web API of the publish, archive and highlight transitions (CM02.03)."""

import pytest
from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.test import Client
from django.utils import timezone

from comunicados.models import Comunicado, EstadoComunicado, TipoComunicado

BASE = "/api/web/comedores/comunicados/{}/{}/"
GESTION = "/api/web/comedores/comunicados/gestion/"

pytestmark = pytest.mark.django_db


def _user(username, *codes):
    user = User.objects.create_user(username=username)
    for code in codes:
        app, codename = code.split(".")
        if app == "auth":
            permiso = Permission.objects.get_or_create(
                codename=codename,
                content_type=ContentType.objects.get_for_model(User),
                defaults={"name": codename},
            )[0]
        else:
            permiso = Permission.objects.get(
                content_type__app_label=app, codename=codename
            )
        user.user_permissions.add(permiso)
    return user


def _client(user, **kwargs):
    client = Client(**kwargs)
    client.force_login(user)
    return client


def _com(estado=EstadoComunicado.BORRADOR, **campos):
    autor = User.objects.get_or_create(username="autor_cm0203")[0]
    datos = {"cuerpo": "Texto", "tipo": TipoComunicado.INTERNO, **campos}
    if estado == EstadoComunicado.PUBLICADO:
        datos.setdefault("fecha_publicacion", timezone.now())
    return Comunicado.objects.create(
        titulo="Aviso", estado=estado, usuario_creador=autor, **datos
    )


def _post(user, pk, accion):
    return _client(user).post(BASE.format(pk, accion))


def _mensajes(client):
    return [(m["message"], m["level"]) for m in client.get(GESTION).json()["messages"]]


@pytest.fixture(name="gestor")
def gestor_fixture():
    return _user("gestor_cm0203", "comunicados.change_comunicado")


def test_publish_draft_sets_state_date_and_queues_the_native_message(gestor):
    com = _com()
    client = _client(gestor)

    respuesta = client.post(BASE.format(com.pk, "publicar"))

    assert respuesta.status_code == 200
    assert respuesta.json() == {"ok": True, "redirect": "/comunicados/gestion/"}
    com.refresh_from_db()
    assert com.estado == EstadoComunicado.PUBLICADO
    assert com.fecha_publicacion is not None
    assert com.usuario_ultima_modificacion == gestor
    assert _mensajes(client) == [("Comunicado publicado correctamente.", "success")]
    assert _mensajes(client) == []


def test_publish_repeated_warns_and_archived_errors_without_changes(gestor):
    publicado = _com(EstadoComunicado.PUBLICADO)
    archivado = _com(EstadoComunicado.ARCHIVADO)
    client = _client(gestor)

    assert client.post(BASE.format(publicado.pk, "publicar")).status_code == 200
    assert _mensajes(client) == [("El comunicado ya está publicado.", "warning")]
    assert client.post(BASE.format(archivado.pk, "publicar")).status_code == 200
    assert _mensajes(client) == [
        ("No se puede publicar un comunicado archivado.", "error")
    ]
    archivado.refresh_from_db()
    assert archivado.estado == EstadoComunicado.ARCHIVADO


@pytest.mark.parametrize(
    "estado", [EstadoComunicado.BORRADOR, EstadoComunicado.PUBLICADO]
)
def test_archive_draft_or_published_clears_highlight(gestor, estado):
    com = _com(estado, destacado=True)
    client = _client(gestor)

    assert client.post(BASE.format(com.pk, "archivar")).status_code == 200

    com.refresh_from_db()
    assert (com.estado, com.destacado) == (EstadoComunicado.ARCHIVADO, False)
    assert _mensajes(client) == [("Comunicado archivado correctamente.", "success")]


def test_archive_already_archived_warns(gestor):
    com = _com(EstadoComunicado.ARCHIVADO)
    client = _client(gestor)

    client.post(BASE.format(com.pk, "archivar"))

    assert _mensajes(client) == [("El comunicado ya está archivado.", "warning")]


def test_highlight_toggles_on_published_and_errors_on_draft(gestor):
    publicado = _com(EstadoComunicado.PUBLICADO)
    borrador = _com()
    client = _client(gestor)

    client.post(BASE.format(publicado.pk, "destacado"))
    publicado.refresh_from_db()
    assert publicado.destacado is True
    assert _mensajes(client) == [("Comunicado marcado como destacado.", "success")]
    client.post(BASE.format(publicado.pk, "destacado"))
    publicado.refresh_from_db()
    assert publicado.destacado is False
    assert _mensajes(client) == [("Comunicado desmarcado como destacado.", "success")]
    client.post(BASE.format(borrador.pk, "destacado"))
    borrador.refresh_from_db()
    assert borrador.destacado is False
    assert _mensajes(client) == [
        (
            "Solo se puede modificar el destacado de comunicados publicados.",
            "error",
        )
    ]


def test_highlight_accepts_external_like_the_native_view(gestor):
    com = _com(EstadoComunicado.PUBLICADO, tipo=TipoComunicado.EXTERNO)

    _client(gestor).post(BASE.format(com.pk, "destacado"))

    com.refresh_from_db()
    assert com.destacado is True


@pytest.mark.parametrize(
    "accion,mensaje",
    [
        ("publicar", "No tiene permisos para publicar comunicados."),
        ("archivar", "No tiene permisos para archivar comunicados."),
        ("destacado", "No tiene permisos para modificar el estado destacado."),
    ],
)
def test_without_permission_403_even_for_unknown_id(accion, mensaje):
    lector = _user("lector_cm0203")
    com = _com()

    for pk in (com.pk, 999999):
        respuesta = _post(lector, pk, accion)
        assert respuesta.status_code == 403
        assert respuesta.json() == {"detail": mensaje}
    com.refresh_from_db()
    assert com.estado == EstadoComunicado.BORRADOR


@pytest.mark.parametrize("accion", ["publicar", "archivar", "destacado"])
def test_unknown_id_404_anonymous_401_get_405_and_csrf_403(gestor, accion):
    com = _com()

    assert _post(gestor, 999999, accion).status_code == 404
    assert Client().post(BASE.format(com.pk, accion)).status_code == 401
    assert _client(gestor).get(BASE.format(com.pk, accion)).status_code == 405
    sin_csrf = _client(gestor, enforce_csrf_checks=True)
    assert sin_csrf.post(BASE.format(com.pk, accion)).status_code == 403
    com.refresh_from_db()
    assert com.estado == EstadoComunicado.BORRADOR


def test_native_posts_still_redirect_to_gestion(gestor):
    com = _com()

    respuesta = _client(gestor).post(f"/comunicados/publicar/{com.pk}/")

    assert respuesta.status_code == 302
    assert respuesta["Location"] == "/comunicados/gestion/"
