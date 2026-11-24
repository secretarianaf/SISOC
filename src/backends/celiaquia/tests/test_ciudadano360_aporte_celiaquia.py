"""Aporte JSON de Celiaquia a Ciudadano 360 (C04.01)."""

from datetime import datetime, timezone

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from celiaquia import ciudadano_detail as celiaquia_detail
from celiaquia.models import (
    EstadoExpediente,
    EstadoLegajo,
    Expediente,
    ExpedienteCiudadano,
)
from ciudadanos import detail_contributions as dc
from ciudadanos.models import Ciudadano

pytestmark = pytest.mark.django_db


@pytest.fixture(name="ciudadano")
def ciudadano_fixture():
    return Ciudadano.objects.create(nombre="Ana", apellido="Celi", documento=30444555)


def _legajo(ciudadano, indice, estado_legajo, creado_en, **campos):
    usuario = get_user_model().objects.create_user(username=f"prov_c04_{indice}")
    expediente = Expediente.objects.create(
        usuario_provincia=usuario,
        estado=EstadoExpediente.objects.create(nombre=f"Expediente {indice}"),
    )
    legajo = ExpedienteCiudadano.objects.create(
        expediente=expediente,
        ciudadano=ciudadano,
        estado=EstadoLegajo.objects.create(nombre=estado_legajo),
        **campos,
    )
    ExpedienteCiudadano.objects.filter(pk=legajo.pk).update(creado_en=creado_en)
    return legajo


def test_proyeccion_con_historial_y_etiquetas_de_la_fuente(ciudadano):
    _legajo(ciudadano, 1, "Rechazado", datetime(2026, 1, 5, 15, tzinfo=timezone.utc))
    _legajo(
        ciudadano,
        2,
        "Aprobado",
        datetime(2026, 3, 2, 1, 30, tzinfo=timezone.utc),
        es_titular_activo=True,
    )

    seccion = celiaquia_detail.proyectar_aporte(ciudadano)["celiaquia"]

    actual = seccion["legajo_actual"]
    assert actual["estado_expediente"] == "Expediente 2"
    assert actual["estado_legajo"] == "Aprobado"
    assert actual["es_titular_activo"] is True
    assert set(actual) == {
        "estado_expediente",
        "estado_legajo",
        "resultado_cruce",
        "estado_cupo",
        "es_titular_activo",
        "revision_tecnica",
    }
    # Orden -creado_en, hora local con "d/m/Y H:i" (01:30 UTC = 22:30 del dia anterior).
    assert [
        (h["estado_legajo"], h["creado_en_texto"]) for h in seccion["historial"]
    ] == [
        ("Aprobado", "01/03/2026 22:30"),
        ("Rechazado", "05/01/2026 12:00"),
    ]


def test_sin_legajos_es_vacio(ciudadano):
    assert celiaquia_detail.proyectar_aporte(ciudadano) == {
        "celiaquia": {"legajo_actual": None, "historial": []}
    }


def test_consulta_propaga_la_excepcion_y_el_html_la_absorbe(ciudadano, monkeypatch):
    def roto(_pk):
        raise RuntimeError("base caida")

    monkeypatch.setattr(celiaquia_detail, "obtener_resumen_ciudadano", roto)
    with pytest.raises(RuntimeError):
        celiaquia_detail.proyectar_aporte(ciudadano)
    contexto = celiaquia_detail.obtener_contexto(ciudadano, dc.logger_modulo)
    assert contexto == {"celiaquia_resumen": None}


def test_endpoint_http_bajo_el_prefijo_de_celiaquia(ciudadano):
    cliente = Client()
    cliente.force_login(get_user_model().objects.create_superuser(username="c04_cel"))
    base = f"/api/web/celiaquia/ciudadanos/{ciudadano.pk}/aportes/"
    respuesta = cliente.get(base + "celiaquia/")
    assert respuesta.status_code == 200
    assert respuesta.json()["secciones"]["celiaquia"]["legajo_actual"] is None
    assert cliente.get(base + "comedores/").status_code == 404
