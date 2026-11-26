"""Detalle de un evento de auditoría en JSON: proyección de la vista nativa y acceso."""

import pytest
from auditlog.models import LogEntry
from django.test import Client

from audittrail.test_historial_web import _cliente
from audittrail.web_auditoria import _valor_detalle
from ciudadanos.models import Ciudadano

pytestmark = pytest.mark.django_db

VER = "auditlog.view_logentry"


@pytest.fixture(name="eventos")
def eventos_fixture():
    ana = Ciudadano.objects.create(nombre="Ana", apellido="Uno", documento=30111222)
    ana.telefono = "1155550000"
    ana.observaciones = "<b>x</b>" + "y" * 200
    ana.save()
    entradas = LogEntry.objects.filter(object_pk=str(ana.pk)).order_by("pk")
    return ana, entradas[0], entradas[1]


def _url(entry, consulta=""):
    return f"/api/web/auditoria/evento/{entry.pk}/{consulta}"


def test_detalle_proyecta_la_plantilla_nativa(eventos):
    ana, creacion, actualizacion = eventos
    respuesta = _cliente("evt_get").get(_url(actualizacion))
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["id"] == actualizacion.pk
    assert datos["modelo_texto"] == "ciudadanos.ciudadano"
    assert datos["instancia_texto"] == f"#{ana.pk}"
    assert datos["evento_texto"] == "Actualización"
    assert datos["evento_clase"] == "bg-primary"
    assert datos["con_diffs"] is True
    assert datos["volver_url"] == "/auditoria/"
    assert datos["origen_texto"] and datos["ip_texto"] == "-"
    assert datos["fecha_texto"].count(":") == 2
    por_campo = {c["campo"]: c for c in datos["cambios"]}
    assert por_campo["telefono"]["old"] == {"empty": True, "text": "", "preview": None}
    assert por_campo["telefono"]["new"]["text"] == "1155550000"
    largo = por_campo["observaciones"]["new"]
    # El resolutor nativo ya acorta los textos largos: no llegan al umbral de 180.
    assert largo["text"].startswith("<b>x</b>y") and largo["preview"] is None
    assert "no-store" in respuesta["Cache-Control"]
    inicial = _cliente("evt_creacion").get(_url(creacion)).json()
    assert inicial["evento_texto"] == "Creación" and inicial["es_eliminacion"] is False


def test_volver_respeta_el_next_valido_y_descarta_el_externo(eventos):
    _, _, actualizacion = eventos
    cliente = _cliente("evt_next")
    interno = cliente.get(_url(actualizacion, "?next=/auditoria/x/y/1/%3Fpage%3D2"))
    assert interno.json()["volver_url"] == "/auditoria/x/y/1/?page=2"
    externo = cliente.get(_url(actualizacion, "?next=http://evil.example/"))
    assert externo.json()["volver_url"] == "/auditoria/"


def test_evento_sin_diffs_y_acceso_rechazado(eventos):
    _, creacion, _ = eventos
    sin_cambios = LogEntry.objects.create(
        content_type=creacion.content_type,
        object_pk=creacion.object_pk,
        object_repr="x",
        action=LogEntry.Action.DELETE,
        changes={},
    )
    datos = _cliente("evt_sin").get(_url(sin_cambios)).json()
    assert datos["con_diffs"] is False and datos["cambios"] == []
    assert datos["es_eliminacion"] is True and datos["evento_texto"] == "Eliminación"
    assert Client().get(_url(creacion)).status_code == 401
    assert _cliente("evt_sinperm", ()).get(_url(creacion)).status_code == 403
    assert _cliente("evt_post").post(_url(creacion)).status_code == 405
    assert _cliente("evt_404").get("/api/web/auditoria/evento/0/").status_code == 404
    lector = _cliente("evt_lee")
    antes = LogEntry.objects.count()
    lector.get(_url(creacion))
    assert LogEntry.objects.count() == antes


def test_resumen_de_valores_largos_como_details():
    largo = _valor_detalle("<b>x</b>" + "y" * 200)
    assert largo["text"].startswith("<b>x</b>y")
    assert len(largo["preview"]) == 180 and largo["preview"].endswith("…")
    assert largo["preview"].startswith("xyyy")
    assert _valor_detalle("y" * 180)["preview"] is None
