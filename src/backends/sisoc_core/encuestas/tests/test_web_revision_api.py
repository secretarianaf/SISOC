"""E04.B: session JSON transport of the publication review over the native views."""

import re

import pytest
from django.test import Client
from django.utils.html import strip_tags

from encuestas.models import (
    EstadoEncuesta,
    OpcionPregunta,
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
from encuestas.tests.helpers_web_api import make_actor, send

pytestmark = pytest.mark.django_db
API = "/api/web/encuestas/"
LIST = "/api/web/encuestas/lista/"


@pytest.fixture
def approver():
    return make_actor(
        "aprobadora_rev", ["view_encuesta", "change_encuesta", "aprobar_encuesta"]
    )


def pending_survey(creator, title="Para revisar"):
    survey = crear_encuesta(
        usuario=creator,
        titulo=title,
        descripcion="Primera línea\nSegunda línea",
        es_obligatoria=True,
        duracion_ronda_dias=7,
    )
    single = Pregunta.objects.create(
        encuesta=survey,
        texto="¿Cómo calificás?",
        tipo=TipoPregunta.OPCION_UNICA,
        orden=1,
        pondera=True,
    )
    OpcionPregunta.objects.create(
        pregunta=single, texto="Bueno", valor="Bueno", orden=1, puntaje=5
    )
    OpcionPregunta.objects.create(
        pregunta=single, texto="Malo", valor="Malo", orden=2, puntaje=1
    )
    yes_no = Pregunta.objects.create(
        encuesta=survey,
        texto="¿Volverías?",
        tipo=TipoPregunta.SI_NO,
        orden=2,
        pondera=True,
        puntaje_si=3,
        puntaje_no=1,
    )
    Pregunta.objects.create(
        encuesta=survey,
        texto="Comentarios",
        tipo=TipoPregunta.TEXTO_LARGO,
        orden=3,
        obligatoria=False,
        pregunta_condicion=yes_no,
        operador_condicion="igual",
        valor_condicion="no",
    )
    # Document list segmentation: an all-users survey would block every web actor of the test.
    actualizar_segmentacion(
        survey,
        tipo=TipoSegmentacion.LISTADO_DOCUMENTOS,
        destinatarios=[{"tipo_documento": "dni", "numero_documento": "30999999"}],
    )
    solicitar_publicacion(survey, usuario=creator)
    survey.refresh_from_db()
    return survey


def state(survey):
    survey.refresh_from_db()
    return (
        survey.estado,
        survey.motivo_rechazo,
        survey.usuario_rechazo_id,
        RondaEncuesta.objects.filter(encuesta=survey).count(),
    )


def native_text(client, survey):
    html = client.get(f"/encuestas/{survey.pk}/revision/").content.decode()
    body = html[html.index('<div class="encuesta-revision">') :]
    return re.sub(r"\s+", " ", strip_tags(body)).strip()


# --- access --------------------------------------------------------------------


def test_anonymous_is_401_and_head_does_not_leak_admindocs(approver):
    survey = pending_survey(approver[0])
    url = f"{API}{survey.pk}/revision/"
    assert Client().get(url).status_code == 401
    response = Client(REMOTE_ADDR="10.0.0.5").head(url)
    assert response.status_code == 401 and "X-View" not in response


def test_read_needs_review_permission_and_flags_the_approver(approver):
    user, client = approver
    survey = pending_survey(user)
    url = f"{API}{survey.pk}/revision/"
    _, nobody = make_actor("sin_rev", ["view_encuesta"])
    assert nobody.get(url).status_code == 403
    _, editor = make_actor("edita_rev", ["change_encuesta"])
    assert editor.get(url).json()["puede_aprobar"] is False
    assert client.get(url).json()["puede_aprobar"] is True
    assert client.get(f"{API}999999/revision/").status_code == 404


def test_only_approvers_resolve_and_nothing_changes_for_others(approver):
    user, _ = approver
    survey = pending_survey(user)
    _, editor = make_actor("edita_rev2", ["change_encuesta"])
    before = state(survey)
    assert send(editor, f"{API}{survey.pk}/aprobar/").status_code == 403
    assert (
        send(editor, f"{API}{survey.pk}/rechazar/", {"motivo": "x"}).status_code == 403
    )
    assert state(survey) == before


# --- read ----------------------------------------------------------------------


def test_projection_matches_the_native_page(approver):
    user, client = approver
    survey = pending_survey(user)
    body = client.get(f"{API}{survey.pk}/revision/").json()
    text = native_text(client, survey)
    assert (
        body["estado"] == "pendiente_aprobacion" and body["modalidad"] == "Obligatoria"
    )
    assert body["descripcion"] == "Primera línea\nSegunda línea"
    assert body["segmentacion"]["destinatarios"] == ["DNI: 30999999"]
    assert [p["numero"] for p in body["preguntas"]] == [1, 2, 3]
    assert body["preguntas"][0]["opciones"] == [
        {"texto": "Bueno", "puntaje": 5},
        {"texto": "Malo", "puntaje": 1},
    ]
    assert body["preguntas"][2]["condicion"].startswith("Se muestra si «¿Volverías?»")
    for fragment in (
        body["titulo"],
        f"Versión {body['version']} · Creada por {body['creador']}",
        body["solicitada_por"],
        body["fecha_solicitud"],
        body["preguntas"][2]["condicion"],
        "Ver 1 destinatario",
        "Preguntas (3)",
        "· 5 puntos",
        "· 3 puntos",
    ):
        assert fragment in text


def test_rejection_reason_is_projected_for_a_returned_draft(approver):
    user, client = approver
    survey = pending_survey(user)
    send(client, f"{API}{survey.pk}/rechazar/", {"motivo": "Falta contexto."})
    body = client.get(f"{API}{survey.pk}/revision/").json()
    assert body["estado"] == "borrador"
    assert body["motivo_rechazo"]["texto"] == "Falta contexto."
    assert body["motivo_rechazo"]["usuario"] == str(user)
    assert "Falta contexto." in native_text(client, survey)


# --- approve / reject: persisted effects, unchanged on rejection ----------------


def test_approve_publishes_and_leaves_the_message_queued(approver):
    user, client = approver
    survey = pending_survey(user)
    response = send(client, f"{API}{survey.pk}/aprobar/")
    assert response.json() == {"ok": True, "redirect": "/encuestas/", "messages": []}
    assert state(survey)[0] == EstadoEncuesta.PUBLICADA
    assert state(survey)[3] == 1
    assert client.get(LIST).json()["messages"] == [
        {"message": "Encuesta aprobada y publicada correctamente.", "level": "success"}
    ]


def test_approving_twice_is_the_native_error_without_changes(approver):
    user, client = approver
    survey = pending_survey(user)
    send(client, f"{API}{survey.pk}/aprobar/")
    client.get(LIST)
    before = state(survey)
    send(client, f"{API}{survey.pk}/aprobar/")
    assert state(survey) == before
    assert client.get(LIST).json()["messages"][0]["level"] == "error"


def test_reject_stores_the_reason_and_returns_to_draft(approver):
    user, client = approver
    survey = pending_survey(user)
    response = send(
        client, f"{API}{survey.pk}/rechazar/", {"motivo": "  Revisar las opciones  "}
    )
    assert response.json()["redirect"] == "/encuestas/"
    estado, motivo, quien, rondas = state(survey)
    assert (estado, motivo, quien, rondas) == (
        "borrador",
        "Revisar las opciones",
        user.pk,
        0,
    )
    assert client.get(LIST).json()["messages"][0]["message"] == (
        "Solicitud rechazada. El gestor podrá ver el motivo y corregir la encuesta."
    )


def test_invalid_reason_is_the_native_400_and_changes_nothing(approver):
    user, client = approver
    survey = pending_survey(user)
    before = state(survey)
    empty = send(client, f"{API}{survey.pk}/rechazar/", {"motivo": "   "})
    assert empty.status_code == 400
    assert (
        empty.json()["errors"]["motivo"][0]["message"]
        == "Indicá qué debe corregir el gestor."
    )
    long = send(client, f"{API}{survey.pk}/rechazar/", {"motivo": "x" * 2001})
    assert long.status_code == 400 and long.json()["errors"]["motivo"]
    assert state(survey) == before


def test_rejecting_a_non_pending_survey_is_the_native_error_without_changes(approver):
    user, client = approver
    survey = pending_survey(user)
    send(client, f"{API}{survey.pk}/aprobar/")
    client.get(LIST)
    before = state(survey)
    response = send(client, f"{API}{survey.pk}/rechazar/", {"motivo": "Tarde"})
    assert response.status_code == 200 and response.json()["redirect"].endswith(
        "/revision/"
    )
    assert state(survey) == before
    assert client.get(LIST).json()["messages"][0]["level"] == "error"


def test_guards_csrf_method_and_unknown(approver):
    user, client = approver
    survey = pending_survey(user)
    before = state(survey)
    assert send(client, f"{API}{survey.pk}/aprobar/", csrf=False).status_code == 403
    assert (
        send(
            client, f"{API}{survey.pk}/rechazar/", {"motivo": "x"}, csrf=False
        ).status_code
        == 403
    )
    assert client.get(f"{API}{survey.pk}/aprobar/").status_code == 405
    assert send(client, f"{API}999999/aprobar/").status_code == 404
    assert state(survey) == before
