"""E02: session JSON transport of the segmentation and import screens over the native views."""

import json

import pytest
from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client

from encuestas.models import (
    Encuesta,
    Pregunta,
    SegmentacionDestinatario,
    TipoPregunta,
    TipoSegmentacion,
)
from encuestas.tests.helpers_web_api import make_actor, multipart, send
from encuestas.services import (
    actualizar_segmentacion,
    agregar_destinatario,
    crear_encuesta,
    exportar_encuesta,
    solicitar_publicacion,
)

pytestmark = pytest.mark.django_db
IMPORT = "/api/web/encuestas/importar/"


@pytest.fixture
def manager():
    return make_actor("gestora_seg", ["change_encuesta", "add_encuesta"])


@pytest.fixture
def survey(manager):
    return crear_encuesta(
        usuario=manager[0],
        titulo="Satisfacción",
        es_obligatoria=True,
        duracion_ronda_dias=7,
    )


def seg_url(survey, suffix=""):
    return f"/api/web/encuestas/{survey.pk}/segmentacion/{suffix}"


def state(survey):
    survey.refresh_from_db()
    segmentacion = getattr(survey, "segmentacion", None)
    if segmentacion is None:
        return (survey.disponible_pwa, None)
    return (
        survey.disponible_pwa,
        segmentacion.tipo,
        sorted(segmentacion.grupos.values_list("pk", flat=True)),
        sorted(segmentacion.usuarios.values_list("pk", flat=True)),
        sorted(
            segmentacion.destinatarios.values_list("tipo_documento", "numero_documento")
        ),
    )


# --- access -------------------------------------------------------------


def test_anonymous_is_401_on_every_endpoint(survey):
    client = Client(enforce_csrf_checks=True)
    assert client.get(seg_url(survey)).status_code == 401
    assert client.post(IMPORT).status_code == 401
    # an internal address must not expose admindocs metadata on HEAD
    response = Client(REMOTE_ADDR="10.0.0.5").head(seg_url(survey))
    assert response.status_code == 401
    assert "X-View" not in response


def test_user_without_permission_is_403_and_nothing_changes(survey):
    _, client = make_actor("sin_permiso", ["view_encuesta"])
    before = state(survey)
    assert client.get(seg_url(survey)).status_code == 403
    for suffix, data in (
        ("tipo/", {"tipo": "todos_los_usuarios"}),
        ("agregar/", {"tipo_documento": "dni", "numero_documento": "30111222"}),
    ):
        assert send(client, seg_url(survey, suffix), data).status_code == 403
    assert state(survey) == before
    assert not SegmentacionDestinatario.objects.exists()
    count = Encuesta.objects.count()
    assert send(client, IMPORT).status_code == 403
    assert Encuesta.objects.count() == count


def test_import_needs_add_permission(survey):
    _, client = make_actor("solo_cambia", ["change_encuesta"])
    count = Encuesta.objects.count()
    response = multipart(
        client, IMPORT, {"archivo": SimpleUploadedFile("e.json", b"{}")}
    )
    assert response.status_code == 403
    assert Encuesta.objects.count() == count
    assert client.get(seg_url(survey)).status_code == 200


def test_post_without_csrf_is_403_and_unchanged(manager, survey):
    _, client = manager
    before = state(survey)
    response = send(client, seg_url(survey, "tipo/"), {"tipo": "grupos"}, csrf=False)
    assert response.status_code == 403
    assert state(survey) == before


def test_json_body_is_415_and_unchanged(manager, survey):
    _, client = manager
    before = state(survey)
    response = client.post(
        seg_url(survey, "tipo/"),
        json.dumps({"tipo": "todos_los_usuarios"}),
        content_type="application/json",
        HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value,
    )
    assert response.status_code == 415
    assert state(survey) == before


def test_unknown_survey_is_404(manager):
    _, client = manager
    assert client.get("/api/web/encuestas/999999/segmentacion/").status_code == 404
    response = send(client, "/api/web/encuestas/999999/segmentacion/tipo/")
    assert response.status_code == 404


# --- read ----------------------------------------------------------------


def test_get_projects_the_template_context(manager, survey):
    _, client = manager
    grupo = Group.objects.create(name="Equipo Norte")
    otro = User.objects.create_user(
        username="destino", first_name="Dora", last_name="Sur"
    )
    actualizar_segmentacion(
        survey, tipo=TipoSegmentacion.GRUPOS, grupos_ids=[grupo.pk], disponible_pwa=True
    )
    response = client.get(seg_url(survey))
    assert response.status_code == 200
    assert "no-store" in response["Cache-Control"]
    body = response.json()
    assert body["id"] == survey.pk and body["titulo"] == "Satisfacción"
    assert body["tipo"] == "grupos" and body["disponible_pwa"] is True
    assert {"id": grupo.pk, "name": "Equipo Norte", "selected": True} in body["grupos"]
    assert body["usuarios"] == [] and body["destinatarios"] == []
    assert (
        body["urls"]["plantilla"] == f"/encuestas/{survey.pk}/segmentacion/plantilla/"
    )
    assert body["messages"] == []
    actualizar_segmentacion(
        survey, tipo=TipoSegmentacion.LISTADO_USUARIOS, usuarios_ids=[otro.pk]
    )
    users = client.get(seg_url(survey)).json()["usuarios"]
    assert users == [{"id": otro.pk, "username": "destino", "full_name": "Dora Sur"}]


def test_get_without_segmentation_has_empty_type(manager, survey):
    _, client = manager
    body = client.get(seg_url(survey)).json()
    assert body["tipo"] == "" and body["disponible_pwa"] is False


def test_pending_survey_redirects_to_review_like_native(manager, survey):
    user, client = manager
    Pregunta.objects.create(
        encuesta=survey, texto="¿Conforme?", tipo=TipoPregunta.SI_NO, orden=1
    )
    actualizar_segmentacion(survey, tipo=TipoSegmentacion.TODOS_LOS_USUARIOS)
    solicitar_publicacion(survey, usuario=user)
    body = client.get(seg_url(survey)).json()
    assert body == {"redirect": f"/encuestas/{survey.pk}/revision/"}


# --- writes: persisted effects and unchanged on rejection ---------------------


def test_tipo_groups_persists_and_returns_the_native_message(manager, survey):
    _, client = manager
    grupo = Group.objects.create(name="Equipo Sur")
    response = send(
        client,
        seg_url(survey, "tipo/"),
        {
            "tipo": "grupos",
            "grupos": [grupo.pk],
            "disponibilidad_pwa_presente": "1",
            "disponible_pwa": "on",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["redirect"] == f"/encuestas/{survey.pk}/segmentacion/"
    assert body["messages"] == [
        {"message": "Segmentación actualizada correctamente.", "level": "success"}
    ]
    assert state(survey) == (True, "grupos", [grupo.pk], [], [])
    assert client.get(seg_url(survey)).json()["messages"] == []


def test_tipo_file_upload_replaces_the_list(manager, survey):
    _, client = manager
    csv = b"tipo_documento,numero_documento\ndni,30111222\ncuit,20301112229\n"
    response = multipart(
        client,
        seg_url(survey, "tipo/"),
        {
            "tipo": "listado_documentos",
            "archivo_listado": SimpleUploadedFile("l.csv", csv),
        },
    )
    assert response.json()["messages"] == [
        {"message": "Segmentación actualizada correctamente.", "level": "success"}
    ]
    assert state(survey)[4] == [("cuit", "20301112229"), ("dni", "30111222")]


def test_tipo_rejected_keeps_state(manager, survey):
    _, client = manager
    actualizar_segmentacion(survey, tipo=TipoSegmentacion.TODOS_LOS_USUARIOS)
    before = state(survey)
    response = send(client, seg_url(survey, "tipo/"), {"tipo": "inventado"})
    body = response.json()
    assert response.status_code == 200 and body["ok"] is True
    assert body["messages"][0]["level"] == "error"
    assert state(survey) == before
    response = send(
        client, seg_url(survey, "tipo/"), {"tipo": "grupos", "grupos": ["999999"]}
    )
    assert response.json()["messages"][0]["level"] == "error"
    assert state(survey) == before


def test_agregar_and_quitar_destinatario(manager, survey):
    _, client = manager
    actualizar_segmentacion(survey, tipo=TipoSegmentacion.LISTADO_DOCUMENTOS)
    response = send(
        client,
        seg_url(survey, "agregar/"),
        {"tipo_documento": "dni", "numero_documento": "30111222"},
    )
    assert response.json()["messages"] == [
        {"message": "Destinatario agregado correctamente.", "level": "success"}
    ]
    destinatario = SegmentacionDestinatario.objects.get()
    assert destinatario.numero_documento == "30111222"
    shown = client.get(seg_url(survey)).json()["destinatarios"]
    assert shown == [
        {"id": destinatario.pk, "tipo_label": "DNI", "numero_documento": "30111222"}
    ]
    before = state(survey)
    rejected = send(
        client,
        seg_url(survey, "agregar/"),
        {"tipo_documento": "pasaporte", "numero_documento": "x"},
    )
    assert rejected.json()["messages"][0]["level"] == "error"
    assert state(survey) == before
    gone = send(client, seg_url(survey, f"{destinatario.pk + 999}/quitar/"))
    assert gone.json()["messages"][0]["level"] == "error"
    assert state(survey) == before
    quitado = send(client, seg_url(survey, f"{destinatario.pk}/quitar/"))
    assert quitado.json()["messages"] == [
        {"message": "Destinatario eliminado correctamente.", "level": "success"}
    ]
    assert not SegmentacionDestinatario.objects.exists()


def test_agregar_usuario_by_id(manager, survey):
    _, client = manager
    target = User.objects.create_user(username="elegida")
    actualizar_segmentacion(survey, tipo=TipoSegmentacion.LISTADO_USUARIOS)
    response = send(client, seg_url(survey, "agregar/"), {"usuario_id": target.pk})
    assert response.json()["messages"][0]["level"] == "success"
    assert state(survey)[3] == [target.pk]
    before = state(survey)
    response = send(client, seg_url(survey, "agregar/"), {"usuario_id": "999999"})
    assert response.json()["messages"][0]["level"] == "error"
    assert state(survey) == before


# --- import -----------------------------------------------------------------


def test_import_creates_a_draft_and_rejects_bad_files(manager, survey):
    user, client = manager
    agregar_destinatario(survey, tipo_documento="dni", numero_documento="30111222")
    payload = json.dumps(exportar_encuesta(survey, incluir_segmentacion=True)).encode()
    response = multipart(
        client, IMPORT, {"archivo": SimpleUploadedFile("e.json", payload)}
    )
    body = response.json()
    assert response.status_code == 200 and body["redirect"] == "/encuestas/"
    assert body["messages"] == [
        {
            "message": "Encuesta importada en borrador con su segmentación. "
            "Revisá los destinatarios antes de publicarla.",
            "level": "success",
        }
    ]
    assert Encuesta.objects.filter(estado="borrador", usuario_creador=user).count() == 2
    count = Encuesta.objects.count()
    bad = multipart(
        client, IMPORT, {"archivo": SimpleUploadedFile("e.json", b"no es json")}
    )
    assert bad.json()["messages"][0]["level"] == "error"
    assert Encuesta.objects.count() == count
