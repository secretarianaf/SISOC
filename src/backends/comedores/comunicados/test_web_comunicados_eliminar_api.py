"""Web API of the comunicado delete confirmation and removal (CM02.02)."""

import pytest
from django.contrib.auth.models import Permission, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.utils import timezone

from comunicados.models import (
    Comunicado,
    ComunicadoAdjunto,
    EstadoComunicado,
    TipoComunicado,
)

URL = "/api/web/comedores/comunicados/{}/eliminar/"
GESTION = "/api/web/comedores/comunicados/gestion/"

pytestmark = pytest.mark.django_db


def _client(user, **kwargs):
    client = Client(**kwargs)
    client.force_login(user)
    return client


def _admin():
    return User.objects.create_user("admin_cm0202", is_superuser=True)


def _com(estado=EstadoComunicado.BORRADOR):
    autor = User.objects.get_or_create(
        username="autor_cm0202", first_name="Ana", last_name="Pérez"
    )[0]
    return Comunicado.objects.create(
        titulo="Aviso a borrar",
        cuerpo="Texto",
        estado=estado,
        tipo=TipoComunicado.INTERNO,
        usuario_creador=autor,
        fecha_publicacion=timezone.now() if estado == "publicado" else None,
    )


def test_confirmation_projects_what_the_native_template_prints():
    com = _com()
    ComunicadoAdjunto.objects.create(
        comunicado=com,
        archivo=SimpleUploadedFile("a.pdf", b"x"),
        nombre_original="a.pdf",
    )

    respuesta = _client(_admin()).get(URL.format(com.pk))

    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["titulo"] == "Aviso a borrar"
    assert datos["creador"] == "Ana Pérez"
    assert datos["adjuntos_count"] == 1
    assert datos["fecha_creacion"] == (
        timezone.localtime(com.fecha_creacion).strftime("%d/%m/%Y %H:%M")
    )
    assert datos["messages"] == []


def test_post_deletes_in_cascade_and_queues_the_native_message():
    com = _com()
    ComunicadoAdjunto.objects.create(
        comunicado=com,
        archivo=SimpleUploadedFile("b.pdf", b"x"),
        nombre_original="b.pdf",
    )
    client = _client(_admin())

    respuesta = client.post(URL.format(com.pk))

    assert respuesta.status_code == 200
    assert respuesta.json() == {"ok": True, "redirect": "/comunicados/gestion/"}
    assert not Comunicado.objects.filter(pk=com.pk).exists()
    assert not ComunicadoAdjunto.objects.filter(comunicado_id=com.pk).exists()
    mensajes = client.get(GESTION).json()["messages"]
    assert mensajes == [
        {"message": "Comunicado eliminado correctamente.", "level": "success"}
    ]


@pytest.mark.parametrize("metodo", ["get", "post"])
def test_published_or_non_admin_403_with_native_message_and_nothing_deleted(metodo):
    publicado = _com(EstadoComunicado.PUBLICADO)
    borrador = _com()
    gestor = User.objects.create_user("gestor_cm0202")

    gestor.user_permissions.add(Permission.objects.get(codename="change_comunicado"))
    mensaje = {"detail": "No tiene permisos para eliminar este comunicado."}

    for cliente, pk in (
        (_client(_admin()), publicado.pk),
        (_client(gestor), borrador.pk),
    ):
        respuesta = getattr(cliente, metodo)(URL.format(pk))
        assert respuesta.status_code == 403
        assert respuesta.json() == mensaje
    assert Comunicado.objects.count() == 2


@pytest.mark.parametrize("metodo", ["get", "post"])
def test_unknown_id_404_before_permission_and_anonymous_401(metodo):
    lector = User.objects.create_user("lector_cm0202")

    assert getattr(_client(lector), metodo)(URL.format(999999)).status_code == 404
    assert getattr(Client(), metodo)(URL.format(999999)).status_code == 401


def test_post_without_csrf_403_and_native_delete_still_redirects():
    com = _com()
    admin = _admin()

    sin_csrf = _client(admin, enforce_csrf_checks=True).post(URL.format(com.pk))
    assert sin_csrf.status_code == 403
    assert Comunicado.objects.filter(pk=com.pk).exists()
    nativo = _client(admin).post(f"/comunicados/eliminar/{com.pk}/")
    assert nativo.status_code == 302
    assert nativo["Location"] == "/comunicados/gestion/"
