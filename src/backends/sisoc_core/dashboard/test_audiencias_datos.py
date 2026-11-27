"""Administración de audiencias de tableros, sin roles globales."""

import pytest
from auditlog.models import LogEntry
from django.contrib.auth.models import Group, User
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.test import Client
from django.urls import reverse

from dashboard.models import (
    AudienciaTableros,
    ConcesionTablero,
    MiembroAudienciaTableros,
    Tablero,
)

pytestmark = pytest.mark.django_db


def test_audiencias_requieren_rol():
    actor = User.objects.create_user(username="actor")
    client = Client()
    client.force_login(actor)
    assert client.get(reverse("dashboard_audiencias_datos")).status_code == 403
    assert (
        client.post(
            reverse("dashboard_audiencias_datos"), {"nombre": "Prueba"}
        ).status_code
        == 403
    )


@pytest.mark.parametrize("staff", [True, False])
def test_head_audiencias_exige_rol(staff):
    audiencia = AudienciaTableros.objects.create(nombre="Audiencia")
    client = Client(REMOTE_ADDR="203.0.113.42" if staff else "127.0.0.1")
    if staff:
        actor = User.objects.create_user(username="staff", is_staff=True)
        client.force_login(actor)
    for url in (
        reverse("dashboard_audiencias_datos"),
        reverse("dashboard_audiencia_detalle", args=[audiencia.pk]),
    ):
        assert client.get(url).status_code == 403
        response = client.head(url, HTTP_X_VIEW="1")
        assert response.status_code == 403
        assert "X-View" not in response


def test_gestion_audiencia_y_membresia_sin_modificar_roles():
    call_command("create_groups", verbosity=0)
    actor = User.objects.create_user(username="datos")
    actor.groups.add(Group.objects.get(name="Equipo de Datos"))
    usuario = User.objects.create_user(username="receptor")
    tablero = Tablero.objects.create(nombre="Tablero", slug="uno")
    client = Client()
    client.force_login(actor)
    response = client.post(
        reverse("dashboard_audiencias_datos"), {"nombre": "Equipo A"}
    )
    assert response.status_code == 302
    audiencia = AudienciaTableros.objects.get(nombre="Equipo A")
    url = reverse("dashboard_audiencia_detalle", args=[audiencia.pk])
    assert (
        client.post(
            url, {"accion": "agregar_miembro", "username": "receptor"}
        ).status_code
        == 302
    )
    assert audiencia.membresias.filter(usuario=usuario).exists()
    miembro = audiencia.membresias.get(usuario=usuario)
    assert (
        client.post(
            url,
            {"accion": "agregar_concesion", "tablero": tablero.pk, "tipo": "nacional"},
        ).status_code
        == 302
    )
    concesion = ConcesionTablero.objects.get(audiencia=audiencia)
    assert (
        client.post(
            url, {"accion": "quitar_miembro", "usuario": usuario.pk}
        ).status_code
        == 302
    )
    assert not audiencia.membresias.filter(usuario=usuario).exists()
    assert ConcesionTablero.objects.filter(pk=concesion.pk).exists()
    assert not usuario.groups.exists()
    assert not usuario.user_permissions.exists()
    content_type = ContentType.objects.get_for_model(MiembroAudienciaTableros)
    for accion in (LogEntry.Action.CREATE, LogEntry.Action.DELETE):
        assert LogEntry.objects.filter(
            content_type=content_type,
            object_pk=str(miembro.pk),
            actor=actor,
            action=accion,
        ).exists()


def test_renombrar_y_rechazar_operaciones_invalidas():
    call_command("create_groups", verbosity=0)
    actor = User.objects.create_user(username="datos")
    actor.groups.add(Group.objects.get(name="Equipo de Datos"))
    audiencia = AudienciaTableros.objects.create(nombre="Original")
    tablero = Tablero.objects.create(nombre="Tablero", slug="uno")
    client = Client()
    client.force_login(actor)
    lista = reverse("dashboard_audiencias_datos")
    url = reverse("dashboard_audiencia_detalle", args=[audiencia.pk])
    assert client.get(lista).status_code == 200
    assert client.get(url).status_code == 200
    assert client.post(lista, {"nombre": ""}).status_code == 400
    assert client.post(url, {"accion": "ninguna"}).status_code == 400
    assert (
        client.post(
            url, {"accion": "agregar_miembro", "username": "ausente"}
        ).status_code
        == 400
    )
    assert (
        client.post(
            url, {"accion": "agregar_concesion", "tablero": tablero.pk, "tipo": "cdi"}
        ).status_code
        == 400
    )
    assert (
        client.post(url, {"accion": "renombrar", "nombre": "Actualizada"}).status_code
        == 302
    )
    audiencia.refresh_from_db()
    assert audiencia.nombre == "Actualizada"
    assert not audiencia.membresias.exists()
    assert not audiencia.concesiones.exists()
