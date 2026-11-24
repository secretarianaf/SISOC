"""Aporte JSON de Centro de Familia a Ciudadano 360 (C04.01)."""

from datetime import datetime, time, timezone

import pytest
from django.contrib.auth.models import User
from django.template.loader import render_to_string
from django.test import Client
from django.utils import translation

from centrodefamilia import ciudadano_detail as cdf_detail
from centrodefamilia.models import (
    Actividad,
    ActividadCentro,
    Categoria,
    Centro,
    ParticipanteActividad,
)
from ciudadanos import detail_contributions as dc
from ciudadanos.models import Ciudadano

pytestmark = pytest.mark.django_db


@pytest.fixture(name="ciudadano")
def ciudadano_fixture():
    return Ciudadano.objects.create(nombre="Ana", apellido="Cdf", documento=30333444)


def _participacion(ciudadano, centro, actividad, precio, estado, fecha):
    categoria, _ = Categoria.objects.get_or_create(nombre="Deporte")
    actividad_obj, _ = Actividad.objects.get_or_create(
        nombre=actividad, defaults={"categoria": categoria}
    )
    actividad_centro = ActividadCentro.objects.create(
        centro=centro,
        actividad=actividad_obj,
        cantidad_personas=10,
        horariosdesde=time(9, 0),
        precio=precio,
    )
    participante = ParticipanteActividad.objects.create(
        ciudadano=ciudadano, actividad_centro=actividad_centro, estado=estado
    )
    ParticipanteActividad.objects.filter(pk=participante.pk).update(
        fecha_registro=fecha
    )
    return participante


@pytest.fixture(name="centro")
def centro_fixture():
    return Centro.objects.create(nombre="Centro Uno", tipo="faro", codigo="C-1")


def _monto_nativo(total):
    return render_to_string(
        "centrodefamilia/ciudadano_detalle_monto.html", {"costo_total_cdf": total}
    ).strip()


def test_proyeccion_de_participaciones_y_monto(ciudadano, centro):
    _participacion(
        ciudadano,
        centro,
        "Futbol",
        1500,
        "inscrito",
        datetime(2026, 2, 3, 12, tzinfo=timezone.utc),
    )
    _participacion(
        ciudadano,
        centro,
        "Yoga",
        2500,
        "inscrito",
        datetime(2026, 3, 4, 12, tzinfo=timezone.utc),
    )
    _participacion(
        ciudadano,
        centro,
        "Ajedrez",
        900,
        "lista_espera",
        datetime(2026, 1, 1, 12, tzinfo=timezone.utc),
    )
    _participacion(
        ciudadano,
        centro,
        "Danza",
        700,
        "baja",
        datetime(2025, 12, 31, 12, tzinfo=timezone.utc),
    )

    with translation.override("es-ar"):
        secciones = cdf_detail.proyectar_aporte(ciudadano)

    filas = secciones["centrodefamilia"]
    # Todos los estados, orden -fecha_registro.
    assert [
        (f["actividad_nombre"], f["estado"], f["fecha_registro_texto"]) for f in filas
    ] == [
        ("Yoga", "inscrito", "04/03/2026"),
        ("Futbol", "inscrito", "03/02/2026"),
        ("Ajedrez", "lista_espera", "01/01/2026"),
        ("Danza", "baja", "31/12/2025"),
    ]
    assert filas[0]["centro_nombre"] == "Centro Uno"
    # Solo suman los inscritos.
    assert secciones["centrodefamilia_monto"]["total"] == "4000"
    with translation.override("es-ar"):
        assert secciones["centrodefamilia_monto"]["total_texto"] == _monto_nativo(4000)


@pytest.mark.parametrize("total", [0, 1500, 1234567])
def test_total_texto_es_el_del_template_nativo(ciudadano, centro, total):
    if total:
        _participacion(
            ciudadano,
            centro,
            "Futbol",
            total,
            "inscrito",
            datetime(2026, 2, 3, tzinfo=timezone.utc),
        )
    with translation.override("es-ar"):
        monto = cdf_detail.proyectar_aporte(ciudadano)["centrodefamilia_monto"]
        assert monto["total_texto"] == _monto_nativo(total)
    assert monto["total_texto"].startswith("$")


def test_cero_exitoso_es_un_dato_valido(ciudadano):
    secciones = cdf_detail.proyectar_aporte(ciudadano)
    assert secciones["centrodefamilia"] == []
    assert secciones["centrodefamilia_monto"]["total"] == "0"


def test_consulta_propaga_la_excepcion_y_el_html_la_absorbe(ciudadano, monkeypatch):
    monkeypatch.setattr(cdf_detail, "ParticipanteActividad", None)
    with pytest.raises(AttributeError):
        cdf_detail.proyectar_aporte(ciudadano)
    contexto = cdf_detail.obtener_contexto(ciudadano, dc.logger_modulo)
    assert contexto == {"participaciones_cdf": [], "costo_total_cdf": 0}


def test_el_queryset_se_evalua_dentro_de_la_consulta(ciudadano, centro):
    _participacion(
        ciudadano,
        centro,
        "Futbol",
        100,
        "inscrito",
        datetime(2026, 2, 3, tzinfo=timezone.utc),
    )
    contexto = cdf_detail.consultar_contexto(ciudadano)
    assert isinstance(contexto["participaciones_cdf"], list)


def test_endpoint_http_y_aporte_de_otro_backend(ciudadano):
    client = Client()
    client.force_login(User.objects.create_superuser(username="c04_cdf"))
    base = f"/api/web/cdf/ciudadanos/{ciudadano.pk}/aportes/"
    respuesta = client.get(base + "centrodefamilia/")
    assert respuesta.status_code == 200
    assert respuesta.json()["secciones"]["centrodefamilia"] == []
    assert client.get(base + "vat/").status_code == 404
