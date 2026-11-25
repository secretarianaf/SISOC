"""E04.C: session JSON transport of the survey create/edit form over the native views."""

import json
import re

import pytest
from django.test import Client

from encuestas.models import (
    Encuesta,
    EstadoEncuesta,
    OpcionPregunta,
    Pregunta,
    TipoPregunta,
)
from encuestas.services import (
    actualizar_segmentacion,
    crear_encuesta,
    publicar,
    rechazar_publicacion,
    solicitar_publicacion,
)
from encuestas.tests.helpers_web_api import make_actor, send

pytestmark = pytest.mark.django_db
API = "/api/web/encuestas/"
LIST = "/api/web/encuestas/lista/"
VALID = {
    "titulo": "Satisfacción",
    "descripcion": "Para conocer la opinión",
    "modalidad": "obligatoria",
    "duracion_ronda_dias": "7",
}


def preguntas(*extra):
    return [
        {
            "orden": 1,
            "texto": "¿Volverías?",
            "bloque": "",
            "max_caracteres": None,
            "tipo": "si_no",
            "obligatoria": True,
            "opciones": [],
            "pondera": True,
            "puntaje_si": 3,
            "puntaje_no": 1,
            "condicion": None,
        },
        {
            "orden": 2,
            "texto": "¿Por qué?",
            "bloque": "Cierre",
            "max_caracteres": 200,
            "tipo": "texto_corto",
            "obligatoria": False,
            "opciones": [],
            "pondera": False,
            "puntaje_si": 0,
            "puntaje_no": 0,
            "condicion": {"orden": 1, "operador": "igual", "valor": "no"},
        },
        *extra,
    ]


def body(**cambios):
    datos = {**VALID, "preguntas_json": json.dumps(preguntas())}
    datos.update(cambios)
    return datos


@pytest.fixture
def gestor():
    return make_actor(
        "gestora_form", ["view_encuesta", "add_encuesta", "change_encuesta"]
    )


def survey(creator, **extra):
    encuesta = crear_encuesta(
        usuario=creator,
        titulo="Existente",
        descripcion="Texto",
        es_obligatoria=True,
        duracion_ronda_dias=5,
        **extra,
    )
    unica = Pregunta.objects.create(
        encuesta=encuesta,
        texto="¿Cómo calificás?",
        tipo=TipoPregunta.OPCION_UNICA,
        orden=1,
        pondera=True,
    )
    for orden, (texto, puntaje) in enumerate((("Bueno", 5), ("Malo", 1)), 1):
        OpcionPregunta.objects.create(
            pregunta=unica, texto=texto, valor=texto, orden=orden, puntaje=puntaje
        )
    Pregunta.objects.create(
        encuesta=encuesta,
        texto="Comentarios",
        tipo=TipoPregunta.TEXTO_LARGO,
        orden=2,
        obligatoria=False,
        pregunta_condicion=unica,
        operador_condicion="distinto",
        valor_condicion="Bueno",
    )
    return encuesta


def aprobador():
    return make_actor("aprobador_form", ["aprobar_encuesta"])[0]


def snapshot():
    return (
        Encuesta.objects.count(),
        Pregunta.objects.count(),
        list(Encuesta.objects.values_list("pk", "titulo", "version")),
    )


# --- access --------------------------------------------------------------------


def test_anonymous_is_401_and_head_does_not_leak_admindocs(gestor):
    for url in (f"{API}crear/", f"{API}{survey(gestor[0]).pk}/editar/"):
        assert Client().get(url).status_code == 401
        response = Client(REMOTE_ADDR="10.0.0.5").head(url)
        assert response.status_code == 401 and "X-View" not in response


def test_each_screen_needs_its_native_permission(gestor):
    user, _ = gestor
    existente = survey(user)
    _, solo_alta = make_actor("solo_alta_form", ["add_encuesta"])
    _, solo_cambio = make_actor("solo_cambio_form", ["change_encuesta"])
    _, solo_ver = make_actor("solo_ver_form", ["view_encuesta"])
    assert solo_alta.get(f"{API}crear/").status_code == 200
    assert solo_alta.get(f"{API}{existente.pk}/editar/").status_code == 403
    assert solo_cambio.get(f"{API}crear/").status_code == 403
    assert solo_cambio.get(f"{API}{existente.pk}/editar/").status_code == 200
    assert solo_ver.get(f"{API}crear/").status_code == 403
    assert solo_ver.get(f"{API}{existente.pk}/editar/").status_code == 403


def test_writes_without_permission_change_nothing(gestor):
    user, _ = gestor
    existente = survey(user)
    _, solo_alta = make_actor("solo_alta_form2", ["add_encuesta"])
    _, solo_cambio = make_actor("solo_cambio_form2", ["change_encuesta"])
    antes = snapshot()
    assert send(solo_cambio, f"{API}crear/", body()).status_code == 403
    assert send(solo_alta, f"{API}{existente.pk}/editar/", body()).status_code == 403
    assert snapshot() == antes


def test_guards_csrf_content_type_method_and_unknown(gestor):
    user, client = gestor
    existente = survey(user)
    antes = snapshot()
    assert send(client, f"{API}crear/", body(), csrf=False).status_code == 403
    assert (
        send(client, f"{API}{existente.pk}/editar/", body(), csrf=False).status_code
        == 403
    )
    token = client.cookies["csrftoken"].value
    assert (
        client.post(
            f"{API}crear/",
            json.dumps(body()),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        ).status_code
        == 415
    )
    assert client.delete(f"{API}crear/", HTTP_X_CSRFTOKEN=token).status_code == 405
    assert client.get(f"{API}999999/editar/").status_code == 404
    assert send(client, f"{API}999999/editar/", body()).status_code == 404
    assert snapshot() == antes


# --- read ----------------------------------------------------------------------


def test_create_projection_matches_the_native_defaults(gestor):
    _, client = gestor
    data = client.get(f"{API}crear/").json()
    assert (
        data["id"] is None and data["urls"] is None and data["motivo_rechazo"] is None
    )
    assert data["preguntas"] == [] and data["non_field_errors"] == []
    assert data["fields"]["modalidad"]["value"] == "postergable"
    assert data["fields"]["es_anonima"]["value"] is False
    assert data["fields"]["titulo"] == {
        "value": "",
        "errors": [],
        "invalid": False,
        "describedby": "",
    }
    assert data["fields"]["intervalo_recordatorio_dias"]["describedby"] == (
        "id_intervalo_recordatorio_dias_helptext"
    )
    html = client.get("/encuestas/crear/").content.decode()
    for valor, label in data["tipos_pregunta"] + data["operadores_condicion"]:
        assert f'<option value="{valor}">{label}</option>' in html
    assert data["tipos_con_opciones"] in html and data["tipos_ponderables"] in html
    assert "Generar encuesta" in html


def test_edit_projection_carries_values_questions_and_export_url(gestor):
    user, client = gestor
    existente = survey(user, es_anonima=True)
    data = client.get(f"{API}{existente.pk}/editar/").json()
    assert data["id"] == existente.pk
    assert data["urls"] == {"exportar": f"/encuestas/{existente.pk}/exportar/"}
    assert data["fields"]["titulo"]["value"] == "Existente"
    assert data["fields"]["es_anonima"]["value"] is True
    assert data["fields"]["modalidad"]["value"] == "obligatoria"
    assert data["fields"]["duracion_ronda_dias"]["value"] == "5"
    assert [p["texto"] for p in data["preguntas"]] == [
        "¿Cómo calificás?",
        "Comentarios",
    ]
    assert data["preguntas"][0]["opciones"] == [
        {"texto": "Bueno", "puntaje": 5},
        {"texto": "Malo", "puntaje": 1},
    ]
    assert data["preguntas"][1]["condicion"] == {
        "orden": 1,
        "operador": "distinto",
        "valor": "Bueno",
    }
    html = client.get(f"/encuestas/{existente.pk}/editar/").content.decode()
    assert "Editar encuesta" in html and "Solo encuesta" in html
    assert re.search(r'value="Existente"', html)


def test_returned_draft_projects_the_rejection_reason(gestor):
    user, client = gestor
    existente = survey(user)
    actualizar_segmentacion(
        existente,
        tipo="listado_documentos",
        destinatarios=[{"tipo_documento": "dni", "numero_documento": "30999999"}],
    )
    solicitar_publicacion(existente, usuario=user)
    rechazar_publicacion(existente, usuario=aprobador(), motivo="Falta contexto.")
    data = client.get(f"{API}{existente.pk}/editar/").json()
    assert data["motivo_rechazo"]["texto"] == "Falta contexto."
    assert data["motivo_rechazo"]["estado"] == "borrador"
    assert data["motivo_rechazo"]["usuario"] == "aprobador_form"
    assert (
        "Falta contexto."
        in client.get(f"/encuestas/{existente.pk}/editar/").content.decode()
    )


def test_pending_survey_answers_the_native_redirect_to_its_review(gestor):
    user, client = gestor
    existente = survey(user)
    actualizar_segmentacion(
        existente,
        tipo="listado_documentos",
        destinatarios=[{"tipo_documento": "dni", "numero_documento": "30999999"}],
    )
    solicitar_publicacion(existente, usuario=user)
    assert client.get(f"{API}{existente.pk}/editar/").json() == {
        "redirect": f"/encuestas/{existente.pk}/revision/"
    }
    antes = snapshot()
    response = send(client, f"{API}{existente.pk}/editar/", body())
    assert response.status_code == 400
    assert response.json()["non_field_errors"] == [
        "La encuesta está pendiente de aprobación y no se puede modificar."
    ]
    assert snapshot() == antes


# --- write: persisted effects, unchanged on rejection ----------------------------


def test_create_persists_survey_and_questions_and_queues_the_message(gestor):
    _, client = gestor
    response = send(client, f"{API}crear/", body(es_anonima="on"))
    assert response.status_code == 200
    assert response.json() == {"ok": True, "redirect": "/encuestas/", "messages": []}
    encuesta = Encuesta.objects.get(titulo="Satisfacción")
    assert (
        encuesta.es_anonima
        and encuesta.es_obligatoria
        and encuesta.estado == "borrador"
    )
    filas = list(encuesta.preguntas.order_by("orden"))
    assert [p.texto for p in filas] == ["¿Volverías?", "¿Por qué?"]
    assert filas[0].puntaje_si == 3 and filas[1].pregunta_condicion_id == filas[0].pk
    assert filas[1].valor_condicion == "no" and filas[1].max_caracteres == 200
    assert client.get(LIST).json()["messages"] == [
        {"message": "Encuesta creada correctamente.", "level": "success"}
    ]


def test_edit_replaces_the_questions_in_the_posted_order(gestor):
    user, client = gestor
    existente = survey(user)
    nuevas = [
        {**preguntas()[1], "orden": 1, "condicion": None},
        {**preguntas()[0], "orden": 2},
    ]
    response = send(
        client,
        f"{API}{existente.pk}/editar/",
        body(titulo="Cambiada", preguntas_json=json.dumps(nuevas)),
    )
    assert response.json()["redirect"] == "/encuestas/"
    existente.refresh_from_db()
    assert existente.titulo == "Cambiada"
    assert list(
        existente.preguntas.order_by("orden").values_list("texto", flat=True)
    ) == [
        "¿Por qué?",
        "¿Volverías?",
    ]
    assert client.get(LIST).json()["messages"][0]["message"] == (
        "Encuesta actualizada correctamente."
    )


def test_invalid_fields_are_the_native_400_with_bound_values_and_no_changes(gestor):
    _, client = gestor
    antes = snapshot()
    response = send(
        client,
        f"{API}crear/",
        body(titulo="", duracion_ronda_dias="x", descripcion="Se conserva"),
    )
    assert response.status_code == 400
    data = response.json()
    assert data["fields"]["titulo"]["errors"] == ["Este campo es requerido."]
    assert data["fields"]["titulo"]["invalid"] is True
    assert data["fields"]["titulo"]["describedby"] == "id_titulo_error"
    assert data["fields"]["duracion_ronda_dias"]["errors"]
    assert data["fields"]["descripcion"]["value"] == "Se conserva"
    assert data["fields"]["modalidad"]["value"] == "obligatoria"
    assert [p["texto"] for p in data["preguntas"]] == ["¿Volverías?", "¿Por qué?"]
    assert snapshot() == antes


def test_invalid_questions_roll_back_the_survey_too(gestor):
    user, client = gestor
    existente = survey(user)
    antes = snapshot()
    malas = [
        {
            **preguntas()[0],
            "tipo": "opcion_unica",
            "opciones": [{"texto": "Una", "puntaje": 0}],
        }
    ]
    for url, datos in (
        (f"{API}crear/", body(preguntas_json=json.dumps(malas))),
        (
            f"{API}{existente.pk}/editar/",
            body(titulo="No", preguntas_json=json.dumps(malas)),
        ),
    ):
        response = send(client, url, datos)
        assert response.status_code == 400
        assert response.json()["non_field_errors"] == [
            "Pregunta 1: las preguntas de opción requieren al menos dos opciones."
        ]
    assert snapshot() == antes


def test_unparseable_questions_are_projected_as_an_empty_editor(gestor):
    _, client = gestor
    response = send(
        client, f"{API}crear/", body(preguntas_json="no es json", titulo="")
    )
    assert response.status_code == 400 and response.json()["preguntas"] == []
    response = send(client, f"{API}crear/", body(preguntas_json='"texto"', titulo=""))
    assert response.status_code == 400 and response.json()["preguntas"] == []


def test_editing_a_survey_with_an_open_round_is_the_native_error(gestor):
    user, client = gestor
    existente = survey(user)
    actualizar_segmentacion(
        existente,
        tipo="listado_documentos",
        destinatarios=[{"tipo_documento": "dni", "numero_documento": "30999999"}],
    )
    solicitar_publicacion(existente, usuario=user)
    publicar(existente, usuario=aprobador())
    existente.refresh_from_db()
    assert existente.estado == EstadoEncuesta.PUBLICADA
    antes = snapshot()
    response = send(client, f"{API}{existente.pk}/editar/", body(titulo="Nueva"))
    assert response.status_code == 400
    assert response.json()["non_field_errors"] == [
        "No se puede editar una encuesta mientras tenga una ronda abierta."
    ]
    assert snapshot() == antes
