import json
from uuid import uuid4

import pytest
from django.core.exceptions import ValidationError
from django.contrib.auth.models import Permission
from django.urls import reverse
from rest_framework.authtoken.models import Token

from core.internal_services import RespuestaInterna
from encuestas.models import (
    CumplimientoRonda,
    EstadoEncuesta,
    RespuestaPregunta,
    RespuestaRonda,
    TipoSegmentacion,
)
from encuestas.services import (
    actualizar_segmentacion,
    crear_encuesta,
    nueva_version,
    reemplazar_preguntas,
    serializar_preguntas,
)
from encuestas.tests.helpers import publicar_para_test
from encuestas.validators import parse_preguntas_payload


@pytest.fixture
def movil(client, django_user_model, monkeypatch):
    user = django_user_model.objects.create_user(username="encuesta-mobile")
    token = Token.objects.create(user=user)
    client.defaults["HTTP_AUTHORIZATION"] = f"Token {token.key}"
    monkeypatch.setattr(
        "encuestas.api_permissions.pedir_json_interno",
        lambda *a, **k: RespuestaInterna(200, {"pwa": {"is_pwa_user": True}}),
    )
    return client, user


@pytest.fixture
def ronda(movil):
    _, user = movil
    encuesta = crear_encuesta(
        usuario=user,
        titulo="Encuesta configurable",
        disponible_pwa=True,
        es_opcional=True,
        duracion_ronda_dias=7,
    )
    reemplazar_preguntas(
        encuesta,
        json.dumps(
            [
                {
                    "orden": 1,
                    "texto": "Experiencia",
                    "tipo": "opcion_unica",
                    "opciones": ["Bien", "Mal"],
                    "bloque": "Experiencia",
                },
                {
                    "orden": 2,
                    "texto": "Sugerencias",
                    "tipo": "texto_largo",
                    "obligatoria": False,
                    "max_caracteres": 500,
                    "bloque": "Sugerencias",
                },
            ]
        ),
    )
    actualizar_segmentacion(encuesta, tipo=TipoSegmentacion.TODOS_LOS_USUARIOS)
    return publicar_para_test(encuesta, usuario=user)


def payload(ronda):
    pregunta = ronda.encuesta.preguntas.get(orden=1)
    return {"response_id": str(uuid4()), "respuestas": {str(pregunta.pk): "Bien"}}


@pytest.mark.django_db
def test_listado_respeta_configuracion_y_orden(movil, ronda):
    client, _ = movil
    response = client.get(reverse("encuestas_pwa_listar"))
    assert response.status_code == 200
    data = response.json()[0]
    assert data["titulo"] == "Encuesta configurable"
    assert data["respondida"] is False
    assert [p["texto"] for p in data["preguntas"]] == ["Experiencia", "Sugerencias"]
    assert data["preguntas"][1]["max_caracteres"] == 500
    assert data["preguntas"][0]["bloque"] == "Experiencia"
    assert "puntaje" not in data["preguntas"][0]["opciones"][0]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "cambio", ["deshabilitada", "borrador", "cerrada", "destinatarios"]
)
def test_no_ofrece_encuestas_fuera_de_alcance(movil, ronda, cambio):
    client, user = movil
    encuesta = ronda.encuesta
    if cambio == "deshabilitada":
        encuesta.disponible_pwa = False
    elif cambio == "borrador":
        encuesta.estado = EstadoEncuesta.BORRADOR
    elif cambio == "cerrada":
        ronda.estado = "cerrada"
        ronda.save()
    else:
        otro = type(user).objects.create_user(username="otro-destinatario")
        actualizar_segmentacion(
            encuesta, tipo=TipoSegmentacion.LISTADO_USUARIOS, usuarios_ids=[otro.pk]
        )
    encuesta.save()
    assert client.get(reverse("encuestas_pwa_listar")).json() == []


@pytest.mark.django_db
@pytest.mark.parametrize("anonima", [False, True])
def test_responder_es_idempotente_y_conserva_anonimato(movil, ronda, anonima):
    client, user = movil
    ronda.encuesta.es_anonima = anonima
    ronda.encuesta.save()
    url = reverse("encuestas_pwa_responder", args=[ronda.pk])
    body = payload(ronda)
    assert client.post(url, body, content_type="application/json").status_code == 200
    response = client.post(url, body, content_type="application/json")
    assert response.status_code == 200
    assert response.json()["ya_registrada"] is True
    assert RespuestaRonda.objects.count() == 1
    assert CumplimientoRonda.objects.filter(usuario=user).count() == 1
    assert RespuestaRonda.objects.get().usuario_id == (None if anonima else user.pk)
    assert client.get(reverse("encuestas_pwa_listar")).json()[0]["respondida"] is True


@pytest.mark.django_db
@pytest.mark.parametrize("error", ["obligatoria", "opcion", "ajena", "tipo", "largo"])
def test_rechaza_respuestas_invalidas_sin_guardar_parciales(movil, ronda, error):
    client, _ = movil
    body = payload(ronda)
    first = next(iter(body["respuestas"]))
    if error == "obligatoria":
        body["respuestas"] = {}
    elif error == "opcion":
        body["respuestas"][first] = "Inventada"
    elif error == "ajena":
        body["respuestas"]["9999999"] = "Otro"
    elif error == "tipo":
        body["respuestas"][first] = {"dato": "invalido"}
    else:
        body["respuestas"][str(ronda.encuesta.preguntas.get(orden=2).pk)] = "x" * 501
    response = client.post(
        reverse("encuestas_pwa_responder", args=[ronda.pk]),
        body,
        content_type="application/json",
    )
    assert response.status_code == 400
    assert not RespuestaRonda.objects.exists()
    assert not RespuestaPregunta.objects.exists()
    assert not CumplimientoRonda.objects.exists()


@pytest.mark.django_db
def test_exige_token_y_acceso_espacios(client, movil, monkeypatch, caplog):
    client.defaults.pop("HTTP_AUTHORIZATION")
    assert client.get(reverse("encuestas_pwa_listar")).status_code == 401
    _, user = movil
    client.defaults["HTTP_AUTHORIZATION"] = f"Token {Token.objects.get(user=user).key}"
    monkeypatch.setattr(
        "encuestas.api_permissions.pedir_json_interno",
        lambda *a, **k: RespuestaInterna(200, {"pwa": {"is_pwa_user": False}}),
    )
    assert client.get(reverse("encuestas_pwa_listar")).status_code == 403
    monkeypatch.setattr(
        "encuestas.api_permissions.pedir_json_interno",
        lambda *a, **k: RespuestaInterna(503, None),
    )
    with caplog.at_level("WARNING", logger="django"):
        assert client.get(reverse("encuestas_pwa_listar")).status_code == 503
    assert f"user_id={user.pk} status=503" in caplog.text


@pytest.mark.django_db
def test_nueva_version_conserva_publicacion_y_presentacion(movil, ronda):
    _, user = movil
    ronda.estado = "cerrada"
    ronda.save()
    nueva = nueva_version(ronda.encuesta, usuario=user)
    assert nueva.disponible_pwa is True
    assert nueva.estado == EstadoEncuesta.BORRADOR
    assert serializar_preguntas(nueva) == serializar_preguntas(ronda.encuesta)


@pytest.mark.django_db
def test_opcion_pwa_se_configura_en_segmentacion(movil):
    client, user = movil
    user.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="encuestas",
            codename__in=["add_encuesta", "change_encuesta"],
        )
    )
    client.force_login(user)
    response = client.post(
        reverse("encuestas_crear"),
        {
            "titulo": "Desde formulario",
            "modalidad": "opcional",
            "duracion_ronda_dias": 7,
            "disponible_pwa": "on",
            "preguntas_json": "[]",
        },
    )
    assert response.status_code == 302
    encuesta = user.encuestas_creadas.get()
    assert encuesta.disponible_pwa is False
    response = client.get(reverse("encuestas_segmentacion", args=[encuesta.pk]))
    assert b'name="disponible_pwa"' in response.content
    response = client.post(
        reverse("encuestas_segmentacion_tipo", args=[encuesta.pk]),
        {
            "tipo": TipoSegmentacion.TODOS_LOS_USUARIOS,
            "disponibilidad_pwa_presente": "1",
            "disponible_pwa": "on",
        },
    )
    assert response.status_code == 302
    encuesta.refresh_from_db()
    assert encuesta.disponible_pwa is True


@pytest.mark.parametrize("limite", [0, -1, True, 10001])
def test_limite_caracteres_invalido(limite):
    with pytest.raises(ValidationError):
        parse_preguntas_payload(
            json.dumps(
                [
                    {
                        "orden": 1,
                        "texto": "Sugerencias",
                        "tipo": "texto_largo",
                        "max_caracteres": limite,
                    }
                ]
            )
        )


@pytest.mark.django_db
def test_api_rechaza_respuesta_de_usuario_fuera_de_segmentacion(movil, ronda):
    client, user = movil
    otro = type(user).objects.create_user(username="destino-distinto")
    actualizar_segmentacion(
        ronda.encuesta, tipo=TipoSegmentacion.LISTADO_USUARIOS, usuarios_ids=[otro.pk]
    )
    response = client.post(
        reverse("encuestas_pwa_responder", args=[ronda.pk]),
        payload(ronda),
        content_type="application/json",
    )
    assert response.status_code == 403
    assert not CumplimientoRonda.objects.exists()


@pytest.mark.django_db
def test_condiciones_encadenadas_no_exigen_descendientes_de_pregunta_oculta(
    movil, ronda
):
    client, _ = movil
    ronda.estado = "cerrada"
    ronda.save()
    reemplazar_preguntas(
        ronda.encuesta,
        json.dumps(
            [
                {"orden": 1, "texto": "Primera", "tipo": "si_no"},
                {
                    "orden": 2,
                    "texto": "Segunda",
                    "tipo": "si_no",
                    "condicion": {"orden": 1, "operador": "igual", "valor": "si"},
                },
                {
                    "orden": 3,
                    "texto": "Tercera",
                    "tipo": "texto_corto",
                    "condicion": {"orden": 2, "operador": "distinto", "valor": "si"},
                },
            ]
        ),
    )
    ronda.estado = "abierta"
    ronda.save()
    preguntas = list(ronda.encuesta.preguntas.all())
    config = client.get(reverse("encuestas_pwa_listar")).json()[0]
    assert config["preguntas"][2]["condicion"]["pregunta_id"] == preguntas[1].pk
    response = client.post(
        reverse("encuestas_pwa_responder", args=[ronda.pk]),
        {"response_id": str(uuid4()), "respuestas": {str(preguntas[0].pk): "no"}},
        content_type="application/json",
    )
    assert response.status_code == 200
    assert RespuestaPregunta.objects.count() == 1


@pytest.mark.django_db
def test_respuestas_multiples_y_validacion_del_tipo(movil, ronda):
    client, _ = movil
    pregunta = ronda.encuesta.preguntas.get(orden=1)
    pregunta.tipo = "opcion_multiple"
    pregunta.save()
    body = payload(ronda)
    url = reverse("encuestas_pwa_responder", args=[ronda.pk])
    assert client.post(url, body, content_type="application/json").status_code == 400
    body["respuestas"][str(pregunta.pk)] = ["Bien", "Mal"]
    assert client.post(url, body, content_type="application/json").status_code == 200
    assert RespuestaPregunta.objects.get().opciones_seleccionadas.count() == 2


@pytest.mark.django_db
@pytest.mark.parametrize(
    "campo,valor",
    [("max_caracteres", 0), ("max_caracteres", 10001), ("bloque", "x" * 121)],
)
def test_configuracion_de_presentacion_valida_en_modelo(movil, ronda, campo, valor):
    pregunta = ronda.encuesta.preguntas.get(orden=2)
    setattr(pregunta, campo, valor)
    with pytest.raises(ValidationError):
        pregunta.full_clean()
