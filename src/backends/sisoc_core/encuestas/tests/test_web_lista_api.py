"""E04: session JSON transport of the survey list and its row actions over the native views."""

import json
import re
from urllib.parse import quote

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.utils.html import strip_tags

from encuestas.models import (
    EstadoEncuesta,
    Pregunta,
    RondaEncuesta,
    TipoPregunta,
    TipoSegmentacion,
)
from encuestas.services import (
    actualizar_segmentacion,
    crear_encuesta,
    solicitar_publicacion,
)
from encuestas.tests.helpers import publicar_para_test
from encuestas.tests.helpers_web_api import make_actor, send

pytestmark = pytest.mark.django_db
API = "/api/web/encuestas/"
LIST = "/api/web/encuestas/lista/"


@pytest.fixture
def manager():
    return make_actor(
        "gestora_lista",
        ["view_encuesta", "add_encuesta", "change_encuesta", "ver_resultados"],
    )


def draft(creator, title="Borrador"):
    survey = crear_encuesta(
        usuario=creator, titulo=title, es_obligatoria=True, duracion_ronda_dias=7
    )
    Pregunta.objects.create(
        encuesta=survey, texto="¿Conforme?", tipo=TipoPregunta.SI_NO, orden=1
    )
    # A published survey for everyone would block every web actor of the test with its mandatory survey.
    actualizar_segmentacion(
        survey,
        tipo=TipoSegmentacion.LISTADO_DOCUMENTOS,
        destinatarios=[{"tipo_documento": "dni", "numero_documento": "30999999"}],
    )
    return survey


def native_text(client, query=""):
    html = client.get(f"/encuestas/{query}").content.decode()
    body = html[html.index('<div class="list-container') :]
    return re.sub(r"\s+", " ", strip_tags(body)).strip()


# --- access -------------------------------------------------------------


def test_anonymous_is_401_and_head_does_not_leak_admindocs():
    assert Client().get(LIST).status_code == 401
    response = Client(REMOTE_ADDR="10.0.0.5").head(LIST)
    assert response.status_code == 401 and "X-View" not in response


def test_read_needs_view_or_results_permission(manager):
    _, nobody = make_actor("sin_nada", ["add_encuesta"])
    assert nobody.get(LIST).status_code == 403
    for name, codename in (
        ("solo_ver", "view_encuesta"),
        ("solo_res", "ver_resultados"),
    ):
        _, client = make_actor(name, [codename])
        body = client.get(LIST).json()
        assert body["puede_gestionar"] is False and body["puede_editar"] is False
    assert manager[1].get(LIST).json()["puede_gestionar"] is True


# --- read ----------------------------------------------------------------------


def test_projection_matches_the_native_page(manager):
    user, client = manager
    first = draft(user, "Primera encuesta")
    second = draft(user, "Segunda encuesta")
    second.motivo_rechazo = "Falta una pregunta"
    second.save(update_fields=["motivo_rechazo"])
    body = client.get(LIST).json()
    text = native_text(client)
    assert body["urls"] == {
        "list": "/encuestas/",
        "add": "/encuestas/crear/",
        "importar": "/encuestas/importar/",
    }
    assert body["filters_config"]["defaultField"] == "titulo"
    assert body["favorites"]["detail_url_template"].startswith("/")
    rows = {row["titulo"]: row for row in body["results"]}
    assert set(rows) == {"Primera encuesta", "Segunda encuesta"}
    row = rows["Segunda encuesta"]
    assert row["tiene_motivo_rechazo"] is True and row["estado"] == "borrador"
    assert (row["modalidad"], row["es_anonima"], row["version"]) == (
        "Obligatoria",
        False,
        1,
    )
    assert row["creador"] == str(user) and row["estado_label"] == "Borrador"
    for item in body["results"]:
        for key in ("titulo", "fecha_creacion", "modalidad", "creador"):
            assert item[key] in text
        assert f"Versión {item['version']} · {item['fecha_creacion']}" in text
    assert body["page"]["count"] == 2 and body["page"]["is_paginated"] is False
    assert f"Se encontraron {body['page']['count']} resultados" in text
    assert body["messages"] == [] and first.pk


def test_filters_and_legacy_links_follow_the_native_view(manager):
    user, client = manager
    draft(user, "Alpha")
    draft(user, "Beta")
    flt = json.dumps(
        {
            "logic": "AND",
            "items": [{"field": "titulo", "op": "contains", "value": "Alp"}],
        }
    )
    body = client.get(f"{LIST}?filters={quote(flt)}").json()
    assert [row["titulo"] for row in body["results"]] == ["Alpha"]
    legacy = client.get(f"{LIST}?busqueda=Beta").json()
    assert legacy["redirect"].startswith("/encuestas/?filters=")
    assert client.get(f"{LIST}?page=9").status_code == 404


def test_pagination_keeps_the_query_and_page_size(manager):
    user, client = manager
    for index in range(21):
        draft(user, f"Encuesta {index:02d}")
    flt = json.dumps(
        {
            "logic": "AND",
            "items": [{"field": "titulo", "op": "contains", "value": "Encuesta"}],
        }
    )
    body = client.get(f"{LIST}?filters={quote(flt)}&page=2").json()
    assert len(body["results"]) == 1 and body["page"]["number"] == 2
    assert body["page"]["previous"] == 1 and body["page"]["next"] is None
    assert body["page"]["query_without_page"].startswith("filters=")
    assert body["page"]["count"] == 21


def test_pending_count_and_link_for_approvers(manager):
    user, _ = manager
    _, approver = make_actor("aprobadora", ["view_encuesta", "aprobar_encuesta"])
    survey = draft(user)
    from encuestas.services import (
        solicitar_publicacion,
    )  # pylint: disable=import-outside-toplevel

    solicitar_publicacion(survey, usuario=user)
    body = approver.get(LIST).json()
    assert body["puede_aprobar"] is True and body["pendientes_aprobacion"] == 1
    assert body["pendientes_url"].startswith("/encuestas/?filters=")
    assert body["results"][0]["estado"] == EstadoEncuesta.PENDIENTE_APROBACION


# --- publish: persisted effect, unchanged on rejection -------------------------


def test_publish_request_persists_and_leaves_the_message_queued(manager):
    user, client = manager
    survey = draft(user)
    response = send(client, f"{API}{survey.pk}/publicar/")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True and body["redirect"] == "/encuestas/"
    survey.refresh_from_db()
    assert survey.estado == EstadoEncuesta.PENDIENTE_APROBACION
    # the message stays queued for the reloaded page, as after a native redirect
    messages = client.get(LIST).json()["messages"]
    assert messages == [
        {
            "message": "Publicación solicitada. La encuesta está pendiente de aprobación.",
            "level": "success",
        }
    ]
    assert client.get(LIST).json()["messages"] == []


def test_publish_request_rejected_keeps_state(manager):
    user, client = manager
    survey = crear_encuesta(
        usuario=user, titulo="Sin preguntas", es_obligatoria=True, duracion_ronda_dias=7
    )
    response = send(client, f"{API}{survey.pk}/publicar/")
    assert response.status_code == 200 and response.json()["ok"] is True
    survey.refresh_from_db()
    assert survey.estado == EstadoEncuesta.BORRADOR
    assert client.get(LIST).json()["messages"][0]["level"] == "error"


def test_publish_guards(manager):
    user, client = manager
    survey = draft(user)
    _, viewer = make_actor("lectora", ["view_encuesta"])
    assert send(viewer, f"{API}{survey.pk}/publicar/").status_code == 403
    assert send(client, f"{API}{survey.pk}/publicar/", csrf=False).status_code == 403
    assert send(client, f"{API}999999/publicar/").status_code == 404
    assert client.get(f"{API}{survey.pk}/publicar/").status_code == 405
    survey.refresh_from_db()
    assert survey.estado == EstadoEncuesta.BORRADOR


# --- close round ----------------------------------------------------------------


def test_close_round_persists_and_repeats_without_changes():
    user, client = make_actor(
        "cierra", ["view_encuesta", "change_rondaencuesta", "change_encuesta"]
    )
    survey = draft(user)
    ronda = publicar_para_test(survey, usuario=user)
    assert ronda.estado == "abierta"
    response = send(client, f"{API}rondas/{ronda.pk}/cerrar/")
    assert response.json()["redirect"] == "/encuestas/"
    ronda.refresh_from_db()
    assert ronda.estado == "cerrada"
    assert client.get(LIST).json()["messages"] == [
        {"message": "Ronda cerrada correctamente.", "level": "success"}
    ]
    closed_at = ronda.fecha_cierre_real
    assert closed_at is not None
    send(client, f"{API}rondas/{ronda.pk}/cerrar/")
    ronda.refresh_from_db()
    assert ronda.estado == "cerrada" and ronda.fecha_cierre_real == closed_at
    assert client.get(LIST).json()["messages"][0]["level"] == "error"
    assert RondaEncuesta.objects.count() == 1


def test_close_round_guards(manager):
    user, client = manager
    survey = draft(user)
    ronda = publicar_para_test(survey, usuario=user)
    assert send(client, f"{API}rondas/{ronda.pk}/cerrar/").status_code == 403
    _, closer = make_actor("cierra_2", ["change_rondaencuesta"])
    assert send(closer, f"{API}rondas/999999/cerrar/").status_code == 404
    assert (
        send(closer, f"{API}rondas/{ronda.pk}/cerrar/", csrf=False).status_code == 403
    )
    ronda.refresh_from_db()
    assert ronda.estado == "abierta"


def test_import_can_leave_its_message_queued_for_the_reloaded_list(manager):
    _, client = manager
    token = client.cookies["csrftoken"].value
    response = client.post(
        f"{API}importar/?mensajes=en-cola",
        {"archivo": SimpleUploadedFile("e.json", b"no es json")},
        HTTP_X_CSRFTOKEN=token,
    )
    assert response.json() == {"ok": True, "redirect": "/encuestas/", "messages": []}
    queued = client.get(LIST).json()["messages"]
    assert [item["level"] for item in queued] == ["error"]
    assert client.get(LIST).json()["messages"] == []
