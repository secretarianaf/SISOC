"""Contratos HTTP de asignación compartida."""

from auditlog.models import LogEntry
from centrodeinfancia.models import CentroDeInfancia
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.test import Client
from django.urls import reverse
import pytest

from core.models import Provincia
from dashboard.models import AudienciaTableros, ConcesionTablero, Tablero

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("audiencia", [False, True])
def test_lote_provincial_auditado_y_atomico(audiencia):
    actor = User.objects.create_superuser(username="datos", password=None)
    cliente = Client()
    cliente.force_login(actor)
    if audiencia:
        sujeto = AudienciaTableros.objects.create(nombre="Audiencia")
        url = reverse("dashboard_audiencia_detalle", args=[sujeto.pk])
        filtro = {"audiencia": sujeto}
    else:
        sujeto = User.objects.create_user(username="destino")
        url = reverse("dashboard_asignaciones_usuario", args=[sujeto.pk])
        filtro = {"usuario": sujeto}
    uno = Tablero.objects.create(nombre="Uno", slug="uno")
    dos = Tablero.objects.create(nombre="Dos", slug="dos")
    salta = Provincia.objects.create(nombre="Salta")
    jujuy = Provincia.objects.create(nombre="Jujuy")
    existente = ConcesionTablero.objects.create(
        tablero=dos, tipo="provincia", provincia=jujuy, **filtro
    )
    datos = {
        "accion": "agregar_lote",
        "tableros": [uno.pk, dos.pk],
        "tipo": "provincia",
        "provincias": [salta.pk, jujuy.pk],
    }
    auditoria = LogEntry.objects.filter(
        content_type=ContentType.objects.get_for_model(ConcesionTablero), actor=actor
    )
    assert cliente.post(url, datos).status_code == 400
    assert list(ConcesionTablero.objects.values_list("pk", flat=True)) == [existente.pk]
    assert not auditoria.exists()
    datos["provincias"] = [salta.pk, 999999]
    assert cliente.post(url, datos).status_code == 400
    assert ConcesionTablero.objects.count() == 1
    tucuman = Provincia.objects.create(nombre="Tucumán")
    datos["provincias"] = [salta.pk, tucuman.pk]
    assert cliente.post(url, datos).status_code == 302
    assert set(
        ConcesionTablero.objects.filter(
            provincia__in=(salta, tucuman), **filtro
        ).values_list("tablero_id", "provincia_id")
    ) == {
        (tablero.pk, provincia.pk)
        for tablero in (uno, dos)
        for provincia in (salta, tucuman)
    }
    assert auditoria.filter(action=LogEntry.Action.CREATE).count() == 4
    assert ConcesionTablero.objects.filter(pk=existente.pk).exists()


def test_cdi_inline_exige_permiso_y_solo_ofrece_y_guarda_activos(monkeypatch):
    monkeypatch.setattr("core.internal_services.backend_de_app", lambda app: None)
    actor = User.objects.create_superuser(username="datos", password=None)
    destino = User.objects.create_user(username="destino")
    tablero = Tablero.objects.create(nombre="Uno", slug="uno")
    activo = CentroDeInfancia.objects.create(nombre="CDI activo", estado="activo")
    baja = CentroDeInfancia.objects.create(nombre="CDI baja", estado="baja")
    cliente = Client()
    selector = reverse("dashboard_buscar_cdis")
    url = reverse("dashboard_asignaciones_usuario", args=[destino.pk])
    datos = {
        "accion": "agregar_lote",
        "tableros": [tablero.pk],
        "tipo": "cdi",
        "cdis": [activo.pk, baja.pk],
    }
    cliente.force_login(destino)
    assert cliente.get(selector).status_code == 403
    assert cliente.post(url, datos).status_code == 403
    cliente.force_login(actor)
    respuesta = cliente.get(selector, {"q": "CDI"})
    assert respuesta.status_code == 200
    assert "no-store" in respuesta["Cache-Control"]
    assert respuesta.json() == {
        "results": [{"id": str(activo.pk), "text": activo.nombre}],
        "pagination": {"more": False},
    }
    assert cliente.post(url, datos).status_code == 400
    assert not ConcesionTablero.objects.exists()
    datos["cdis"] = [activo.pk]
    assert cliente.post(url, datos).status_code == 302
    assert ConcesionTablero.objects.get(usuario=destino).cdi_id == activo.pk


@pytest.mark.parametrize("autorizado", [False, True])
def test_head_del_selector_cdi_respeta_la_autorizacion(autorizado, monkeypatch):
    monkeypatch.setattr("core.internal_services.backend_de_app", lambda app: None)
    actor = User.objects.create_user(
        username="staff", is_staff=True, is_superuser=autorizado
    )
    cliente = Client(REMOTE_ADDR="203.0.113.42")
    cliente.force_login(actor)
    respuesta = cliente.head(reverse("dashboard_buscar_cdis"), HTTP_X_VIEW="1")
    assert respuesta.status_code == (200 if autorizado else 403)
    assert "X-View" not in respuesta
    if autorizado:
        assert "no-store" in respuesta["Cache-Control"]


def test_lote_nacional_exige_permiso_y_csrf_y_agrega_ambos_tableros():
    actor = User.objects.create_superuser(username="datos", password=None)
    destino = User.objects.create_user(username="destino")
    uno = Tablero.objects.create(nombre="Uno", slug="uno")
    dos = Tablero.objects.create(nombre="Dos", slug="dos")
    url = reverse("dashboard_asignaciones_usuario", args=[destino.pk])
    datos = {"accion": "agregar_lote", "tableros": [uno.pk, dos.pk], "tipo": "nacional"}
    cliente = Client(enforce_csrf_checks=True)
    cliente.force_login(actor)
    assert cliente.get(url).status_code == 200
    assert cliente.post(url, datos).status_code == 403
    assert not ConcesionTablero.objects.exists()
    cliente.force_login(destino)
    token = cliente.cookies["csrftoken"].value
    assert cliente.post(url, datos, HTTP_X_CSRFTOKEN=token).status_code == 403
    assert not ConcesionTablero.objects.exists()
    cliente.force_login(actor)
    assert cliente.post(url, datos, HTTP_X_CSRFTOKEN=token).status_code == 302
    assert set(
        ConcesionTablero.objects.filter(usuario=destino).values_list(
            "tablero_id", "tipo"
        )
    ) == {(uno.pk, "nacional"), (dos.pk, "nacional")}


def test_lote_rechaza_mas_de_cien_combinaciones_sin_escribir():
    actor = User.objects.create_superuser(username="datos", password=None)
    audiencia = AudienciaTableros.objects.create(nombre="Audiencia")
    tableros = [
        Tablero.objects.create(nombre=f"Tablero {i}", slug=f"tablero-{i}").pk
        for i in range(11)
    ]
    provincias = [
        Provincia.objects.create(nombre=f"Provincia {i}").pk for i in range(10)
    ]
    cliente = Client()
    cliente.force_login(actor)
    respuesta = cliente.post(
        reverse("dashboard_audiencia_detalle", args=[audiencia.pk]),
        {
            "accion": "agregar_lote",
            "tableros": tableros,
            "tipo": "provincia",
            "provincias": provincias,
        },
    )
    assert respuesta.status_code == 400
    assert "más de 100 asignaciones" in respuesta.content.decode()
    assert not ConcesionTablero.objects.exists()
