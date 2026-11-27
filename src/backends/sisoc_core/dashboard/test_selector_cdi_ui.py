"""Selección múltiple CDI en el administrador de Datos."""

from unittest.mock import patch

import pytest
from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import Client
from django.urls import reverse

from dashboard.models import ConcesionTablero, Tablero

pytestmark = pytest.mark.django_db


def test_selector_guarda_lote_validado_y_falla_cerrado():
    call_command("create_groups", verbosity=0)
    actor = User.objects.create_user(username="datos")
    actor.groups.add(Group.objects.get(name="Equipo de Datos"))
    usuario = User.objects.create_user(username="destino")
    tablero = Tablero.objects.create(nombre="Uno", slug="uno")
    url = reverse("dashboard_seleccionar_cdis", args=["usuario", usuario.pk])
    client = Client()
    client.force_login(actor)
    with patch(
        "dashboard.services.gestion_concesiones.validar_centros",
        side_effect=ValidationError("CDI no disponible"),
    ):
        assert (
            client.post(url, {"tablero": tablero.pk, "cdis": ["1", "2"]}).status_code
            == 400
        )
    assert not ConcesionTablero.objects.exists()
    with patch(
        "dashboard.services.gestion_concesiones.validar_centros",
        return_value=frozenset({1, 2}),
    ):
        assert (
            client.post(url, {"tablero": tablero.pk, "cdis": ["1", "2"]}).status_code
            == 302
        )
    assert set(
        ConcesionTablero.objects.filter(usuario=usuario).values_list(
            "cdi_id", flat=True
        )
    ) == {1, 2}


def test_selector_no_expone_datos_a_usuario_sin_rol():
    actor = User.objects.create_user(username="sinrol", is_staff=True)
    destino = User.objects.create_user(username="destino")
    client = Client()
    client.force_login(actor)
    url = reverse("dashboard_seleccionar_cdis", args=["usuario", destino.pk])
    assert client.get(url).status_code == 403
    respuesta = client.head(url, HTTP_X_VIEW="1")
    assert respuesta.status_code == 403
    assert "X-View" not in respuesta
    assert client.post(url, {}).status_code == 403
    invalida = reverse("dashboard_seleccionar_cdis", args=["desconocido", destino.pk])
    assert client.get(invalida).status_code == 403
    respuesta = client.head(invalida, HTTP_X_VIEW="1")
    assert respuesta.status_code == 403
    assert "X-View" not in respuesta


def test_flujo_local_solo_admite_centros_activos():
    from centrodeinfancia.models import CentroDeInfancia

    call_command("create_groups", verbosity=0)
    actor = User.objects.create_user(username="datos")
    actor.groups.add(Group.objects.get(name="Equipo de Datos"))
    usuario = User.objects.create_user(username="destino")
    tablero = Tablero.objects.create(nombre="Uno", slug="uno")
    activo = CentroDeInfancia.objects.create(nombre="CDI activo", estado="activo")
    baja = CentroDeInfancia.objects.create(nombre="CDI baja", estado="baja")
    url = reverse("dashboard_seleccionar_cdis", args=["usuario", usuario.pk])
    client = Client()
    client.force_login(actor)
    with patch("core.internal_services.backend_de_app", return_value=None):
        response = client.get(url)
        assert response.status_code == 200
        assert "CDI activo" in response.content.decode()
        assert "CDI baja" not in response.content.decode()
        assert (
            client.post(
                url, {"tablero": tablero.pk, "cdis": [str(activo.pk), str(baja.pk)]}
            ).status_code
            == 400
        )
        assert not ConcesionTablero.objects.exists()
        assert (
            client.post(
                url, {"tablero": tablero.pk, "cdis": [str(activo.pk)]}
            ).status_code
            == 302
        )
    assert ConcesionTablero.objects.filter(usuario=usuario, cdi_id=activo.pk).exists()


def test_lote_cdi_duplicado_revierte_datos_y_auditoria():
    from auditlog.context import set_actor
    from auditlog.models import LogEntry
    from centrodeinfancia.models import CentroDeInfancia
    from django.test import RequestFactory
    from dashboard.services.gestion_concesiones import agregar_cdis_usuario

    call_command("create_groups", verbosity=0)
    actor = User.objects.create_user(username="datos")
    actor.groups.add(Group.objects.get(name="Equipo de Datos"))
    receptor = User.objects.create_user(username="receptor")
    tablero = Tablero.objects.create(nombre="Tablero", slug="tablero")
    primero = CentroDeInfancia.objects.create(nombre="Primero", estado="activo")
    segundo = CentroDeInfancia.objects.create(nombre="Segundo", estado="activo")
    request = RequestFactory().get("/")
    request.user = actor
    with (
        patch("core.internal_services.backend_de_app", return_value=None),
        set_actor(actor),
    ):
        agregar_cdis_usuario(request, receptor, tablero, [segundo.pk])
        antes = LogEntry.objects.count()
        with pytest.raises(ValidationError):
            agregar_cdis_usuario(request, receptor, tablero, [primero.pk, segundo.pk])
    assert list(
        ConcesionTablero.objects.filter(usuario=receptor).values_list(
            "cdi_id", flat=True
        )
    ) == [segundo.pk]
    assert LogEntry.objects.count() == antes
