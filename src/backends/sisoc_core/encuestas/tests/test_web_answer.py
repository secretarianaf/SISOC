"""Public-session transport contracts over the original survey answer services."""

import hashlib
import secrets
from urllib.parse import urlencode

import pytest
from django.contrib.auth.models import Group, User
from django.test import Client
from django.utils import timezone

from encuestas.models import (
    CumplimientoRonda,
    OpcionPregunta,
    Pregunta,
    RecordatorioUsuario,
    RespuestaPregunta,
    RespuestaRonda,
    TipoPregunta,
    TipoSegmentacion,
)
from encuestas.services import actualizar_segmentacion, crear_encuesta
from encuestas.tests.helpers import publicar_para_test

pytestmark = pytest.mark.django_db
PENDING = "/api/web/surveys/pending/"


def fingerprint():
    rows = [
        list(model.objects.order_by("pk").values())
        for model in (
            RespuestaRonda,
            RespuestaPregunta,
            CumplimientoRonda,
            RecordatorioUsuario,
        )
    ]
    return hashlib.sha256(repr(rows).encode()).hexdigest()


def send(client, path, data):
    return client.post(
        path,
        urlencode(data, doseq=True),
        content_type="application/x-www-form-urlencoded",
        CONTENT_TYPE="application/x-www-form-urlencoded",
        HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value,
    )


@pytest.fixture
def actor():
    secret = secrets.token_urlsafe(24)
    user = User.objects.create_user(
        username="survey_synthetic",
        password=secret,
        first_name="Ana",
        last_name="Persona",
        email="survey@example.invalid",
    )
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.dni = "12345678"
    profile.cuil = "20123456786"
    profile.save()
    client = Client(enforce_csrf_checks=True, REMOTE_ADDR="203.0.113.42")
    assert client.get("/api/web/login/").status_code == 200
    assert (
        send(
            client, "/api/web/login/", {"username": user.username, "password": secret}
        ).status_code
        == 200
    )
    return user, client


def make_round(user, *, mode="obligatoria", anonymous=False, types=None):
    survey = crear_encuesta(
        usuario=user,
        titulo="Encuesta sintética",
        duracion_ronda_dias=7,
        es_obligatoria=mode == "obligatoria",
        es_opcional=mode == "opcional",
        intervalo_recordatorio_dias=2 if mode == "postergable" else None,
        es_anonima=anonymous,
    )
    questions = []
    for order, kind in enumerate(types or [TipoPregunta.SI_NO], start=1):
        question = Pregunta.objects.create(
            encuesta=survey,
            texto=f"Pregunta {order}",
            tipo=kind,
            orden=order,
            obligatoria=True,
        )
        if kind in (TipoPregunta.OPCION_UNICA, TipoPregunta.OPCION_MULTIPLE):
            for position, value in enumerate(("a", "b"), start=1):
                OpcionPregunta.objects.create(
                    pregunta=question,
                    texto=value.upper(),
                    valor=value,
                    orden=position,
                )
        questions.append(question)
    actualizar_segmentacion(survey, tipo=TipoSegmentacion.TODOS_LOS_USUARIOS)
    return publicar_para_test(survey, usuario=user), questions


def action(ronda, operation="answer"):
    return f"/api/web/surveys/{ronda.pk}/{operation}/"


def test_metadata_requires_session_and_has_no_business_effects():
    client = Client(REMOTE_ADDR="203.0.113.42")
    before = fingerprint()
    assert client.get(PENDING).status_code == 401
    assert fingerprint() == before


def test_empty_home_and_existing_inet_variant(actor):
    user, client = actor
    data = client.get(PENDING).json()
    assert data["round"] is None and data["home_variant"] == "default"
    group, _ = Group.objects.get_or_create(name="CFPINET")
    user.groups.add(group)
    assert client.get(PENDING).json()["home_variant"] == "inet"
    user.is_superuser = True
    user.save(update_fields=["is_superuser"])
    assert client.get(PENDING).json()["home_variant"] == "default"


def test_metadata_keeps_optional_first_and_private_whitelist(actor):
    user, client = actor
    mandatory, _ = make_round(user)
    optional, _ = make_round(user, mode="opcional")
    optional.fecha_cierre_programada = (
        mandatory.fecha_cierre_programada - timezone.timedelta(days=1)
    )
    optional.save(update_fields=["fecha_cierre_programada"])
    response = client.get(PENDING)
    assert response.status_code == 200
    data = response.json()
    assert set(data) == {"presentation", "home_variant", "round", "messages"}
    assert data["round"]["id"] == optional.pk
    assert set(data["round"]) == {
        "id",
        "title",
        "description",
        "mode",
        "anonymous",
        "questions",
        "actions",
    }
    assert set(data["round"]["questions"][0]) == {
        "id",
        "order",
        "text",
        "type",
        "required",
        "condition",
        "options",
    }
    assert (
        data["round"]["actions"]["dismiss"]
        == f"/encuestas/responder/{optional.pk}/descartar/"
    )
    session = client.get("/api/web/session/").json()
    assert session["access"]["state"] == "mandatory_survey_required"
    assert session["navigation"] == []
    assert "legacy_frame_navigation" in data["presentation"]
    assert (
        "private" in response["Cache-Control"]
        and "no-store" in response["Cache-Control"]
    )
    assert "Cookie" in response["Vary"]


@pytest.mark.parametrize(
    "flag,state",
    [
        ("acceso_web", "web_access_denied"),
        ("must_change_password", "password_change_required"),
        ("needs_profile_confirmation", "profile_confirmation_required"),
    ],
)
def test_higher_guards_precede_object_lookup_and_preserve_data(actor, flag, state):
    user, client = actor
    setattr(user.profile, flag, flag != "acceso_web")
    user.profile.save(update_fields=[flag])
    before = fingerprint()
    for response in (
        client.get(PENDING),
        send(client, "/api/web/surveys/999999/answer/", {}),
    ):
        assert response.status_code == 403
        assert response.json()["state"] == state
    assert fingerprint() == before


def test_methods_media_csrf_and_missing_object(actor):
    user, client = actor
    ronda, _ = make_round(user)
    before = fingerprint()
    assert client.get(action(ronda)).status_code == 405
    assert client.head(PENDING).status_code == 200
    assert client.head(PENDING).content == b""
    assert (
        client.post(
            action(ronda), "", content_type="application/x-www-form-urlencoded"
        ).status_code
        == 403
    )
    assert (
        client.post(
            action(ronda),
            "{}",
            content_type="application/json",
            HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value,
        ).status_code
        == 415
    )
    assert send(client, "/api/web/surveys/999999/answer/", {}).status_code == 404
    assert fingerprint() == before


def test_invalid_answer_is_atomic_and_preserves_source_redirect_messages(actor):
    user, client = actor
    ronda, questions = make_round(
        user, types=[TipoPregunta.SI_NO, TipoPregunta.TEXTO_CORTO]
    )
    before = fingerprint()
    response = send(
        client,
        action(ronda),
        {f"respuesta-{questions[0].pk}": "si", "next": "https://outside.invalid/"},
    )
    assert response.status_code == 200 and response.json() == {"redirect": "/inicio/"}
    assert fingerprint() == before
    data = client.get(PENDING).json()
    assert data["round"]["id"] == ronda.pk
    assert data["messages"] and all(
        item["level"] == "error" for item in data["messages"]
    )
    assert client.get(PENDING).json()["messages"] == []


@pytest.mark.parametrize("anonymous", [False, True])
def test_answers_without_admin_permissions_and_keeps_anonymous_separation(
    actor, anonymous
):
    user, client = actor
    ronda, questions = make_round(user, anonymous=anonymous)
    payload = {f"respuesta-{questions[0].pk}": "si", "next": "/inicio/?completed=1"}
    assert not user.has_perm("encuestas.change_encuesta")
    response = send(client, action(ronda), payload)
    assert response.json() == {"redirect": "/inicio/?completed=1"}
    answer = RespuestaRonda.objects.get(ronda=ronda)
    assert answer.completa and answer.usuario_id == (None if anonymous else user.pk)
    assert CumplimientoRonda.objects.filter(ronda=ronda, usuario=user).count() == 1
    before = fingerprint()
    assert send(client, action(ronda), payload).status_code == 200
    assert fingerprint() == before
    assert client.get(PENDING).json()["round"] is None


def test_all_types_multiple_values_and_conditional_questions(actor):
    user, client = actor
    types = list(TipoPregunta.values)
    ronda, questions = make_round(user, types=types)
    values = ["Corto", "Largo", "a", ["a", "b"], "7", "no", "12.50", "2026-11-04"]
    hidden = Pregunta.objects.create(
        encuesta=ronda.encuesta,
        texto="Condicional",
        tipo=TipoPregunta.TEXTO_CORTO,
        orden=9,
        obligatoria=True,
        pregunta_condicion=questions[5],
        operador_condicion="igual",
        valor_condicion="si",
    )
    payload = {f"respuesta-{q.pk}": value for q, value in zip(questions, values)}
    assert send(client, action(ronda), payload).status_code == 200
    assert RespuestaPregunta.objects.count() == 8
    assert not RespuestaPregunta.objects.filter(pregunta=hidden).exists()
    multiple = RespuestaPregunta.objects.get(pregunta=questions[3])
    assert set(multiple.opciones_seleccionadas.values_list("valor", flat=True)) == {
        "a",
        "b",
    }
    assert (
        str(RespuestaPregunta.objects.get(pregunta=questions[6]).valor_numero)
        == "12.50"
    )


@pytest.mark.parametrize(
    "kind,value",
    [
        (TipoPregunta.ESCALA, "1.5"),
        (TipoPregunta.NUMERICO, "NaN"),
        (TipoPregunta.FECHA, "not-a-date"),
    ],
)
def test_source_type_rejections_leave_no_partial_answers(actor, kind, value):
    user, client = actor
    ronda, questions = make_round(user, types=[kind])
    before = fingerprint()
    assert send(
        client, action(ronda), {f"respuesta-{questions[0].pk}": value}
    ).json() == {"redirect": "/inicio/"}
    assert fingerprint() == before


@pytest.mark.parametrize(
    "mode,operation,discarded",
    [("opcional", "dismiss", True), ("postergable", "postpone", False)],
)
def test_source_alternative_actions_and_mandatory_rejection(
    actor, mode, operation, discarded
):
    user, client = actor
    mandatory, _ = make_round(user)
    before = fingerprint()
    assert send(client, action(mandatory, operation), {}).status_code == 200
    assert fingerprint() == before
    ronda, _ = make_round(user, mode=mode)
    assert send(client, action(ronda, operation), {"next": "/inicio/"}).json() == {
        "redirect": "/inicio/"
    }
    reminder = RecordatorioUsuario.objects.get(ronda=ronda, usuario=user)
    assert reminder.descartada is discarded
    assert not RespuestaRonda.objects.exists()
    assert client.get(PENDING).json()["round"]["id"] == mandatory.pk


def test_expired_round_cannot_write(actor):
    user, client = actor
    ronda, questions = make_round(user)
    ronda.fecha_cierre_programada = timezone.now() - timezone.timedelta(seconds=1)
    ronda.save(update_fields=["fecha_cierre_programada"])
    before = fingerprint()
    assert (
        send(client, action(ronda), {f"respuesta-{questions[0].pk}": "si"}).status_code
        == 200
    )
    assert fingerprint() == before


@pytest.mark.parametrize(
    "request_case",
    [
        (route, address, kind)
        for route in ("pending", "answer", "postpone", "dismiss")
        for address in ("127.0.0.1", "203.0.113.42")
        for kind in (
            "anonymous",
            "ready",
            "survey_required",
            "profile_pending",
            "password_pending",
            "web_denied",
        )
    ],
)
def test_survey_head_enforces_guards_and_action_methods(actor, request_case, settings):
    user, _ = actor
    route, address, kind = request_case
    settings.INTERNAL_IPS = ["127.0.0.1"]
    ronda, _ = make_round(
        user, mode="obligatoria" if kind == "survey_required" else "opcional"
    )
    path = PENDING if route == "pending" else action(ronda, route)
    profile = user.profile
    if kind == "web_denied":
        profile.acceso_web = False
    elif kind == "profile_pending":
        profile.needs_profile_confirmation = True
    elif kind == "password_pending":
        profile.must_change_password = True
    profile.save()
    client = Client(enforce_csrf_checks=True, REMOTE_ADDR=address)
    if kind != "anonymous":
        client.force_login(user)
    expected = 401 if kind == "anonymous" else 403
    if kind in {"ready", "survey_required"}:
        expected = 200 if route == "pending" else 405
    before = fingerprint()
    response = client.head(path)
    assert response.status_code == expected
    assert response.content == b""
    assert "X-View" not in response
    assert "private" in response["Cache-Control"]
    assert "no-store" in response["Cache-Control"]
    assert "Cookie" in response["Vary"]
    if expected == 405:
        assert "POST" in response["Allow"]
    else:
        assert response["Content-Type"].startswith("application/json")
    if route == "pending":
        assert "csrftoken" in client.cookies
    if kind == "anonymous":
        assert "sessionid" not in client.cookies
    assert fingerprint() == before
