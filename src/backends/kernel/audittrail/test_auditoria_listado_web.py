"""Listado global de auditoría en JSON: proyección de la vista nativa y acceso."""

import pytest
from auditlog.models import LogEntry
from django.test import Client

from audittrail.test_historial_web import _cliente
from ciudadanos.models import Ciudadano

pytestmark = pytest.mark.django_db

VER = "auditlog.view_logentry"
EXPORTAR = "audittrail.export_auditlog"
URL = "/api/web/auditoria/listado/"


@pytest.fixture(name="ciudadano")
def ciudadano_fixture():
    ana = Ciudadano.objects.create(nombre="Ana", apellido="Uno", documento=30111222)
    ana.telefono = "1155550000"
    ana.save()
    return ana


def test_listado_proyecta_la_plantilla_nativa(ciudadano):
    respuesta = _cliente("lst_get", (VER, EXPORTAR)).get(URL)
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["title"] == "Auditoría de cambios"
    assert datos["puede_exportar"] is True and datos["has_errors"] is False
    assert [(f["name"], f["hidden"]) for f in datos["fields"]] == [
        ("keyword", False),
        ("field_name", False),
        ("batch_key", False),
        ("model", False),
        ("object_pk", False),
        ("actor", False),
        ("action", False),
        ("origin", False),
        ("start_date", False),
        ("end_date", False),
    ]
    por_nombre = {f["name"]: f for f in datos["fields"]}
    assert por_nombre["model"]["label"] == "Modelo"
    assert por_nombre["model"]["attrs"]["placeholder"] == "app o modelo"
    assert por_nombre["object_pk"]["label"] == "ID de instancia"
    fila = next(
        f for f in datos["filas"] if f["modelo_texto"] == "ciudadanos.ciudadano"
    )
    assert fila["modelo_texto"] == "ciudadanos.ciudadano"
    assert fila["instancia_texto"] == f"#{ciudadano.pk}"
    assert fila["detalle_url"].startswith("/auditoria/evento/")
    assert fila["detalle_url"].endswith("?next=/auditoria/")
    assert "no-store" in respuesta["Cache-Control"]


def test_filtros_aplicados_ruta_de_vuelta_y_errores(ciudadano):
    client = _cliente("lst_filtro")
    filtrado = client.get(f"{URL}?action=0&model=ciudadanos.ciudadano").json()
    assert [f["evento_texto"] for f in filtrado["filas"]] == ["Creación"]
    assert {"label": "Evento", "value": "0"} in filtrado["filtros_activos"]
    assert filtrado["filas"][0]["detalle_url"].endswith(
        "?next=/auditoria/%3Faction%3D0%26model%3Dciudadanos.ciudadano"
    )
    invalido = client.get(f"{URL}?keyword=telefono").json()
    assert invalido["has_errors"] is True
    assert invalido["paginacion"]["querystring"] == "keyword=telefono"
    nada = client.get(f"{URL}?object_pk={ciudadano.pk + 9999}").json()
    assert nada["filas"] == []


def test_la_exportacion_no_pasa_por_la_api_y_pagina_fuera_de_rango(ciudadano):
    cliente = _cliente("lst_export", (VER, EXPORTAR))
    respuesta = cliente.get(f"{URL}?export=csv")
    assert respuesta.status_code == 200
    assert respuesta["Content-Type"].startswith("application/json")
    assert "filas" in respuesta.json()
    assert cliente.get(f"{URL}?page=999").status_code == 404
    assert _cliente("lst_noexp").get(URL).json()["puede_exportar"] is False


def test_paginacion_de_25_y_acceso_rechazado(ciudadano):
    for numero in range(30):
        ciudadano.telefono = f"11555500{numero:02d}"
        ciudadano.save()
    datos = _cliente("lst_pag").get(URL).json()
    assert len(datos["filas"]) == 25
    assert datos["paginacion"]["is_paginated"] is True
    assert datos["paginacion"]["num_pages"] >= 2
    assert Client().get(URL).status_code == 401
    assert _cliente("lst_sin", ()).get(URL).status_code == 403
    assert _cliente("lst_post").post(URL).status_code == 405
    lector = _cliente("lst_lee")
    antes = LogEntry.objects.count()
    lector.get(URL)
    assert LogEntry.objects.count() == antes
