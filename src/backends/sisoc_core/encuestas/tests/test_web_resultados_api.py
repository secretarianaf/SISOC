"""E03: session JSON transport of the survey results screen over the native view."""

import re

import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.utils.html import strip_tags

from encuestas.models import (
    OpcionPregunta,
    Pregunta,
    RondaEncuesta,
    TipoDocumento,
    TipoPregunta,
    TipoSegmentacion,
)
from encuestas.services import (
    actualizar_segmentacion,
    crear_encuesta,
    registrar_respuesta,
)
from encuestas.tests.helpers import publicar_para_test
from encuestas.tests.helpers_web_api import make_actor

pytestmark = pytest.mark.django_db


@pytest.fixture
def viewer():
    return make_actor("lectora_res", ["ver_resultados"])


def build_survey(creator, *, title="Satisfacción", answers=3):
    survey = crear_encuesta(
        usuario=creator, titulo=title, es_obligatoria=True, duracion_ronda_dias=7
    )
    single = Pregunta.objects.create(
        encuesta=survey,
        texto="¿Cómo calificás?",
        tipo=TipoPregunta.OPCION_UNICA,
        orden=1,
    )
    for order, name in enumerate(("Bueno", "Malo", "Regular"), 1):
        OpcionPregunta.objects.create(
            pregunta=single, texto=name, valor=name, orden=order
        )
    yes_no = Pregunta.objects.create(
        encuesta=survey, texto="¿Volverías?", tipo=TipoPregunta.SI_NO, orden=2
    )
    scale = Pregunta.objects.create(
        encuesta=survey,
        texto="Puntuá del 1 al 10",
        tipo=TipoPregunta.ESCALA,
        orden=3,
        obligatoria=False,
    )
    comment = Pregunta.objects.create(
        encuesta=survey,
        texto="Comentarios",
        tipo=TipoPregunta.TEXTO_LARGO,
        orden=4,
        obligatoria=False,
    )
    Pregunta.objects.create(
        encuesta=survey,
        texto="Sin respuestas",
        tipo=TipoPregunta.TEXTO_CORTO,
        orden=5,
        obligatoria=False,
    )
    users = []
    for index in range(answers):
        user = User.objects.create_user(username=f"resp_{survey.pk}_{index}")
        user.profile.dni = f"3100{survey.pk:03d}{index}"
        user.profile.save()
        users.append(user)
    actualizar_segmentacion(
        survey,
        tipo=TipoSegmentacion.LISTADO_DOCUMENTOS,
        destinatarios=[
            {"tipo_documento": TipoDocumento.DNI, "numero_documento": u.profile.dni}
            for u in users
        ],
    )
    ronda = publicar_para_test(survey, usuario=creator)
    values = [
        ("Bueno", "si", "8", "Todo bien"),
        ("Bueno", "no", "4", ""),
        ("Malo", "no", "", ""),
    ]
    for user, (one, two, three, four) in zip(users, values):
        data = {f"respuesta-{single.pk}": one, f"respuesta-{yes_no.pk}": two}
        if three:
            data[f"respuesta-{scale.pk}"] = three
        if four:
            data[f"respuesta-{comment.pk}"] = four
        registrar_respuesta(ronda, user, data)
    return survey, ronda


def url(survey, query=""):
    return f"/api/web/encuestas/{survey.pk}/resultados/{query}"


def native_text(client, survey, query=""):
    html = client.get(f"/encuestas/{survey.pk}/resultados/{query}").content.decode()
    body = html[html.index('<div class="encuesta-editor">') :]
    return re.sub(r"\s+", " ", strip_tags(body)).strip()


# --- access -------------------------------------------------------------


def test_anonymous_is_401_and_head_does_not_leak_admindocs(viewer):
    survey, _ = build_survey(viewer[0])
    assert Client().get(url(survey)).status_code == 401
    response = Client(REMOTE_ADDR="10.0.0.5").head(url(survey))
    assert response.status_code == 401 and "X-View" not in response


def test_only_ver_resultados_reads_it(viewer):
    survey, _ = build_survey(viewer[0])
    _, manager = make_actor("solo_gestiona", ["change_encuesta", "view_encuesta"])
    assert manager.get(url(survey)).status_code == 403
    assert viewer[1].get(url(survey)).status_code == 200


def test_unknown_survey_is_404_and_post_is_not_allowed(viewer):
    _, client = viewer
    assert client.get("/api/web/encuestas/999999/resultados/").status_code == 404
    survey, _ = build_survey(viewer[0])
    response = client.post(
        url(survey), {}, HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value
    )
    assert response.status_code == 405


# --- projection ----------------------------------------------------------------


def test_projection_matches_the_native_page_text(viewer):
    user, client = viewer
    survey, ronda = build_survey(user)
    response = client.get(url(survey))
    assert response.status_code == 200 and "no-store" in response["Cache-Control"]
    body = response.json()
    text = native_text(client, survey)
    assert body["titulo"] == "Satisfacción" and body["messages"] == []
    assert (
        body["ronda_actual"]["id"] == ronda.pk
        and body["ronda_actual"]["respuestas"] == 3
    )
    assert body["ronda_actual"]["export_url"] == (
        f"/encuestas/{survey.pk}/resultados/rondas/{ronda.pk}/exportar/"
    )
    assert [r["selected"] for r in body["rondas"]] == [True]
    for label in (
        body["rondas"][0]["label"],
        body["ronda_actual"]["estado_label"],
        body["ronda_actual"]["cierre"],
    ):
        assert label in text
    for item in body["resultados"]:
        assert item["texto"] in text
        for option in item["opciones"]:
            assert (
                f"{option['texto']} {option['cantidad']} ({option['porcentaje']}%)"
                in text
            )
    by_text = {item["texto"]: item for item in body["resultados"]}
    assert [o["porcentaje"] for o in by_text["¿Cómo calificás?"]["opciones"]] == [
        "66,7",
        "33,3",
        "0,0",
    ]
    assert by_text["¿Cómo calificás?"]["opcion_lider_texto"] == "Bueno"
    assert by_text["Puntuá del 1 al 10"]["numerico"] == {
        "promedio": "6,0",
        "minimo": "4",
        "maximo": "8",
        "posicion": "50,0",
    }
    assert by_text["Comentarios"]["respuestas_texto"] == ["Todo bien"]
    assert by_text["Sin respuestas"]["respuestas_texto"] == []
    assert "Sin respuestas todavía." in text


def test_scores_come_from_the_service_and_anonymous_answers_have_no_name(viewer):
    user, client = viewer
    survey, ronda = build_survey(user, title="Con puntaje")
    Pregunta.objects.filter(encuesta=survey, tipo=TipoPregunta.SI_NO).update(
        pondera=True, puntaje_si=3, puntaje_no=1
    )
    first = client.get(url(survey)).json()["puntajes"]
    assert [p["total_posible"] for p in first] == [3, 3, 3]
    assert first[0]["usuario"] != "" or ronda.encuesta.es_anonima
    text = native_text(client, survey)
    for puntaje in first:
        assert (
            f"{puntaje['obtenido']} / {puntaje['total_posible']} ({puntaje['porcentaje']}%)"
            in text
        )


def test_round_selection_and_missing_rounds(viewer):
    user, client = viewer
    survey, ronda = build_survey(user)
    other, other_round = build_survey(user, title="Otra")
    body = client.get(url(survey, f"?ronda={other_round.pk}")).json()
    assert body["ronda_actual"] is None and [r["selected"] for r in body["rondas"]] == [
        False
    ]
    assert (
        client.get(url(survey, f"?ronda={ronda.pk}")).json()["ronda_actual"]["id"]
        == ronda.pk
    )
    empty = crear_encuesta(
        usuario=user, titulo="Sin rondas", es_obligatoria=True, duracion_ronda_dias=7
    )
    body = client.get(url(empty)).json()
    assert body["rondas"] == [] and body["ronda_actual"] is None
    assert "Esta encuesta todavía no tiene rondas." in native_text(client, empty)
    assert RondaEncuesta.objects.filter(encuesta=empty).count() == 0


def test_reading_writes_nothing(viewer):
    user, client = viewer
    survey, _ = build_survey(user)
    counts = (
        RondaEncuesta.objects.count(),
        Pregunta.objects.count(),
        User.objects.count(),
    )
    for _ in range(2):
        assert client.get(url(survey)).status_code == 200
    assert counts == (
        RondaEncuesta.objects.count(),
        Pregunta.objects.count(),
        User.objects.count(),
    )
