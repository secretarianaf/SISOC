"""Aportes JSON de Comedores y PWA a Ciudadano 360 (C04.01)."""

from datetime import date, datetime, timezone

import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from admisiones.models.admisiones import Admision
from ciudadanos import detail_contributions as dc
from ciudadanos.models import Ciudadano
from comedores import ciudadano_detail as comedores_detail
from comedores.models import (
    ActividadColaboradorEspacio,
    ColaboradorEspacio,
    Comedor,
    Nomina,
    TipoDeComedor,
)
from core.models import Municipio, Provincia
from pwa import ciudadano_detail as pwa_detail
from pwa.models import NominaEspacioPWA

pytestmark = pytest.mark.django_db


@pytest.fixture(name="ciudadano")
def ciudadano_fixture():
    return Ciudadano.objects.create(nombre="Ana", apellido="Nomina", documento=30222333)


def _comedor(nombre="Comedor Uno"):
    provincia = Provincia.objects.create(nombre=f"Prov {nombre}")
    return Comedor.objects.create(
        nombre=nombre,
        tipocomedor=TipoDeComedor.objects.create(nombre=f"Tipo {nombre}"),
        provincia=provincia,
        municipio=Municipio.objects.create(
            nombre=f"Muni {nombre}", provincia=provincia
        ),
    )


def _nomina(ciudadano, comedor, estado, fecha):
    nomina = Nomina.objects.create(
        ciudadano=ciudadano,
        admision=Admision.objects.create(comedor=comedor),
        estado=estado,
    )
    Nomina.objects.filter(pk=nomina.pk).update(fecha=fecha)
    return nomina


def test_proyeccion_de_comedores_igual_a_los_datos_del_template(ciudadano):
    uno, dos = _comedor("Comedor Uno"), _comedor("Comedor Dos")
    _nomina(ciudadano, uno, "baja", datetime(2026, 1, 5, 15, tzinfo=timezone.utc))
    _nomina(ciudadano, dos, "activo", datetime(2026, 3, 2, 1, 30, tzinfo=timezone.utc))
    colaboracion = ColaboradorEspacio.objects.create(
        comedor=uno, ciudadano=ciudadano, fecha_alta=date(2026, 2, 3)
    )
    colaboracion.actividades.add(
        ActividadColaboradorEspacio.objects.create(nombre="Cocina"),
        ActividadColaboradorEspacio.objects.create(nombre="Limpieza"),
    )
    ColaboradorEspacio.objects.create(
        comedor=dos,
        ciudadano=ciudadano,
        fecha_alta=date(2026, 4, 1),
        fecha_baja=date(2026, 5, 1),
    )

    secciones = comedores_detail.proyectar_aporte(ciudadano)

    assert secciones["comedores"]["nomina_actual"] == {
        "estado": "activo",
        "comedor": {
            "id": dos.id,
            "nombre": "Comedor Dos",
            "url": reverse("comedor_detalle", args=[dos.id]),
            "tipo_texto": "Tipo Comedor Dos",
            "provincia_texto": "Prov Comedor Dos",
            "municipio_texto": "Muni Comedor Dos",
        },
        # 01:30 UTC del 2/3 es 22:30 del 1/3 en Buenos Aires.
        "fecha_texto": "01/03/2026",
    }
    assert [
        (n["estado"], n["comedor"]["nombre"], n["fecha_texto"])
        for n in secciones["comedores"]["historial"]
    ] == [
        ("activo", "Comedor Dos", "01/03/2026"),
        ("baja", "Comedor Uno", "05/01/2026"),
    ]
    colaboraciones = secciones["comedores_colaboraciones"]
    # Orden -fecha_alta: primero la del 1/4.
    assert [c["fecha_alta_texto"] for c in colaboraciones] == [
        "01/04/2026",
        "03/02/2026",
    ]
    assert colaboraciones[0]["fecha_baja_texto"] == "01/05/2026"
    assert colaboraciones[0]["actividades"] == []
    assert colaboraciones[1]["fecha_baja_texto"] == "-"
    assert sorted(colaboraciones[1]["actividades"]) == ["Cocina", "Limpieza"]


def test_comedor_sin_nominas_ni_colaboraciones_es_vacio(ciudadano):
    secciones = comedores_detail.proyectar_aporte(ciudadano)
    assert secciones == {
        "comedores": {"nomina_actual": None, "historial": []},
        "comedores_colaboraciones": [],
    }


def test_nomina_sin_comedor_proyecta_comedor_nulo(ciudadano):
    nomina = Nomina.objects.create(ciudadano=ciudadano, estado="espera")
    secciones = comedores_detail.proyectar_aporte(ciudadano)
    actual = secciones["comedores"]["nomina_actual"]
    assert actual["estado"] == "espera"
    assert actual["comedor"] is None
    assert nomina.admision is None


def test_consulta_de_comedores_propaga_la_excepcion_y_el_html_la_absorbe(
    ciudadano, monkeypatch
):
    # Un proveedor roto: ``Nomina.objects`` falla al consultar.
    monkeypatch.setattr(comedores_detail, "Nomina", type("N", (), {"objects": None}))
    with pytest.raises(AttributeError):
        comedores_detail.proyectar_aporte(ciudadano)
    # El contexto del HTML conserva su salida de siempre ante el mismo fallo.
    contexto = comedores_detail.obtener_contexto(ciudadano, dc.logger_modulo)
    assert contexto == {"nominas_comedor": [], "colaboraciones_comedor": []}


def test_pwa_proyecta_los_tres_valores(ciudadano):
    assert pwa_detail.proyectar_aporte(ciudadano) == {
        "pwa": {
            "pertenece_comunidad_indigena": False,
            "situacion_calle": False,
            "persona_con_celiaquia": False,
        }
    }
    nomina = Nomina.objects.create(ciudadano=ciudadano, estado="activo")
    NominaEspacioPWA.objects.create(
        nomina=nomina, situacion_calle=True, persona_con_celiaquia=True
    )
    assert pwa_detail.proyectar_aporte(ciudadano)["pwa"] == {
        "pertenece_comunidad_indigena": False,
        "situacion_calle": True,
        "persona_con_celiaquia": True,
    }


def test_pwa_ignora_perfiles_inactivos(ciudadano):
    nomina = Nomina.objects.create(ciudadano=ciudadano, estado="activo")
    NominaEspacioPWA.objects.create(nomina=nomina, situacion_calle=True, activo=False)
    assert pwa_detail.proyectar_aporte(ciudadano)["pwa"]["situacion_calle"] is False


def test_endpoint_comedores_y_pwa_por_http(ciudadano):
    user = User.objects.create_superuser(username="c04_comedores")
    client = Client()
    client.force_login(user)
    base = f"/api/web/comedores/ciudadanos/{ciudadano.pk}/aportes/"
    comedores = client.get(base + "comedores/")
    assert comedores.status_code == 200
    assert set(comedores.json()["secciones"]) == {
        "comedores",
        "comedores_colaboraciones",
    }
    pwa = client.get(base + "pwa/")
    assert pwa.status_code == 200
    assert set(pwa.json()["secciones"]) == {"pwa"}
    # El aporte de otro backend no se sirve bajo este prefijo.
    assert client.get(base + "vat/").status_code == 404


def test_fragmento_html_del_aporte_sigue_igual(ciudadano):
    user = User.objects.create_superuser(username="c04_fragmento")
    client = Client()
    client.force_login(user)
    nomina = Nomina.objects.create(ciudadano=ciudadano, estado="activo")
    NominaEspacioPWA.objects.create(nomina=nomina, situacion_calle=True)
    url = f"/ciudadanos/{ciudadano.pk}/contribucion/pwa_badges/"
    html = client.get(url).content.decode()
    assert "Situación de calle" in html
    assert "Persona con Celiaquía" not in html
