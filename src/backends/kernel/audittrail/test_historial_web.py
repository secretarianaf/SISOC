"""Historial de auditoría de una instancia en JSON: proyección de la vista nativa y acceso."""

import pytest
from auditlog.models import LogEntry
from django.contrib.auth.models import Permission, User
from django.test import Client

from ciudadanos.models import Ciudadano

pytestmark = pytest.mark.django_db

VER = "auditlog.view_logentry"
EXPORTAR = "audittrail.export_auditlog"


def _cliente(username, permisos=(VER,)):
    user = User.objects.create_user(username=username, password="x")
    for codigo in permisos:
        app, codename = codigo.split(".")
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label=app, codename=codename)
        )
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture(name="ciudadano")
def ciudadano_fixture():
    ana = Ciudadano.objects.create(nombre="Ana", apellido="Uno", documento=30111222)
    ana.telefono = "1155550000"
    ana.save()
    return ana


def _url(ciudadano, consulta=""):
    return f"/api/web/auditoria/ciudadanos/ciudadano/{ciudadano.pk}/{consulta}"


def _filas(datos):
    return [(f["evento_texto"], f["con_diffs"]) for f in datos["filas"]]


def test_historial_proyecta_el_listado_nativo(ciudadano):
    respuesta = _cliente("hist_get", (VER, EXPORTAR)).get(_url(ciudadano))
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["title"] == "Historial de la instancia"
    assert datos["puede_exportar"] is True and datos["has_errors"] is False
    assert [f["name"] for f in datos["fields"]] == [
        "keyword",
        "field_name",
        "batch_key",
        "model",
        "object_pk",
        "actor",
        "action",
        "origin",
        "start_date",
        "end_date",
    ]
    por_nombre = {f["name"]: f for f in datos["fields"]}
    assert por_nombre["keyword"]["label"] == "Texto en cambios"
    assert por_nombre["keyword"]["attrs"]["placeholder"] == "campo, valor o fragmento"
    assert (por_nombre["model"]["hidden"], por_nombre["model"]["value"]) == (
        True,
        "ciudadanos.ciudadano",
    )
    assert por_nombre["object_pk"]["value"] == str(ciudadano.pk)
    assert [c["label"] for c in por_nombre["action"]["choices"]] == [
        "Todos los eventos",
        "Creación",
        "Actualización",
        "Eliminación",
    ]
    assert por_nombre["start_date"]["widget"] == "date"
    assert _filas(datos) == [("Actualización", True), ("Creación", True)]
    actualizacion = datos["filas"][0]
    assert actualizacion["cambios"] == [
        {
            "campo": "telefono",
            "old": {"empty": True, "text": ""},
            "new": {"empty": False, "text": "1155550000"},
        }
    ]
    assert actualizacion["cambios_total"] == 1
    assert actualizacion["fecha_texto"].count("-") == 2
    assert actualizacion["detalle_url"].startswith("/auditoria/evento/")
    assert actualizacion["detalle_url"].endswith(
        f"?next=/auditoria/ciudadanos/ciudadano/{ciudadano.pk}/"
    )
    creacion = datos["filas"][1]
    # Como la plantilla nativa: ``slice`` no corta ``dict_items``, así que se listan todos.
    assert len(creacion["cambios"]) == creacion["cambios_total"] > 2
    assert datos["paginacion"]["is_paginated"] is False
    assert "no-store" in respuesta["Cache-Control"]


def test_filtros_aplicados_y_errores_de_formulario(ciudadano):
    client = _cliente("hist_filtro")
    filtrado = client.get(_url(ciudadano, "?action=0")).json()
    assert _filas(filtrado) == [("Creación", True)]
    # El chip nativo busca la opción por el valor ya convertido y muestra el código.
    assert filtrado["filtros_activos"] == [{"label": "Evento", "value": "0"}]
    # Con filtros en la URL, los ocultos solo traen lo que el formulario recibió (nativo).
    assert {f["name"]: f["value"] for f in filtrado["fields"]}["action"] == "0"
    invalido = client.get(_url(ciudadano, "?keyword=telefono")).json()
    assert invalido["has_errors"] is True
    assert invalido["non_field_errors"] == [
        "Para buscar por texto o campo en cambios, indicá un rango de fechas (Desde y Hasta)."
    ]
    assert invalido["paginacion"]["querystring"] == "keyword=telefono"


def test_la_exportacion_no_pasa_por_la_api(ciudadano):
    cliente = _cliente("hist_export", (VER, EXPORTAR))
    respuesta = cliente.get(_url(ciudadano, "?export=csv"))
    assert respuesta.status_code == 200
    assert respuesta["Content-Type"].startswith("application/json")
    assert "filas" in respuesta.json()


def test_sin_permiso_de_exportar_no_hay_botones(ciudadano):
    assert _cliente("hist_noexp").get(_url(ciudadano)).json()["puede_exportar"] is False


def test_pagina_fuera_de_rango_es_404_y_otra_instancia_viene_vacia(ciudadano):
    client = _cliente("hist_pag")
    assert client.get(_url(ciudadano, "?page=9")).status_code == 404
    otra = Ciudadano.objects.create(nombre="Zoe", apellido="Zeta", documento=2)
    LogEntry.objects.filter(object_pk=str(otra.pk)).delete()
    assert client.get(_url(otra)).json()["filas"] == []


def test_acceso_rechazado(ciudadano):
    assert Client().get(_url(ciudadano)).status_code == 401
    sin_permiso = _cliente("hist_sin", ())
    assert sin_permiso.get(_url(ciudadano)).status_code == 403
    assert _cliente("hist_ok").post(_url(ciudadano)).status_code == 405
    # Solo lectura: nada se escribe al mirar el historial.
    lector = _cliente("hist_lee")
    antes = LogEntry.objects.count()
    lector.get(_url(ciudadano))
    assert LogEntry.objects.count() == antes
