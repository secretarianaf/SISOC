"""API de la PWA: escuelas, borradores, imágenes y permisos entre usuarios."""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from inspecciones.models import EventoInspeccion, ImagenInspeccion, Inspeccion

pytestmark = pytest.mark.django_db

BASE = "/api/inspecciones"


# ------------------------------------------------------------- acceso


def test_sin_token_responde_401():
    assert APIClient().get(f"{BASE}/escuelas/asignadas/").status_code == 401


def test_usuario_sin_el_programa_responde_403(cliente_de):
    ajeno = get_user_model().objects.create_user(username="ajeno", password="x")

    response = cliente_de(ajeno).get(f"{BASE}/escuelas/asignadas/")

    assert response.status_code == 403


def test_flag_sin_rol_no_alcanza(cliente_de):
    user = get_user_model().objects.create_user(username="sin_rol", password="x")
    user.profile.es_inspector_escolar = True
    user.profile.save(update_fields=["es_inspector_escolar"])

    assert cliente_de(user).get(f"{BASE}/actas/").status_code == 403


# ------------------------------------------------------------- escuelas


def test_escuelas_asignadas_con_estado(api_a, asignada_a, escuela, payload):
    response = api_a.get(f"{BASE}/escuelas/asignadas/")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": "060123400",
            "nombre": escuela.nombre,
            "cue": "060123400",
            "distrito": "La Matanza",
            "localidad": "San Justo",
            "domicilio": "Av. Pres. Perón 3245",
            "nivel": "Primario",
            "estado": "pendiente",
        }
    ]

    api_a.put(
        f"{BASE}/borradores/7b5c1c52-37a4-4d4f-9b1c-4f1d1f2f0a01/",
        payload(escuela),
        format="json",
    )
    assert api_a.get(f"{BASE}/escuelas/asignadas/").json()[0]["estado"] == "borrador"


def test_asignadas_es_por_inspector(api_b, asignada_a):
    assert api_b.get(f"{BASE}/escuelas/asignadas/").json() == []


def test_busqueda_minimo_tres_caracteres_y_cue_con_ceros(api_a, escuela):
    assert api_a.get(f"{BASE}/escuelas/", {"q": "06"}).json() == []

    por_cue = api_a.get(f"{BASE}/escuelas/", {"q": "0601"}).json()
    por_nombre = api_a.get(f"{BASE}/escuelas/", {"q": "sarmiento"}).json()
    por_domicilio = api_a.get(f"{BASE}/escuelas/", {"q": "Perón"}).json()

    assert [e["cue"] for e in por_cue] == ["060123400"]
    assert por_nombre == por_cue == por_domicilio
    assert "estado" not in por_cue[0]


def test_ficha_con_visitas_de_hoy_de_cualquier_inspector(api_a, api_b, escuela, cerrar):
    _, cierre = cerrar(api_b, escuela)
    assert cierre.status_code == 200, cierre.json()

    ficha = api_a.get(f"{BASE}/escuelas/{escuela.codigo}/").json()

    assert ficha["id"] == escuela.codigo
    assert ficha["visitas_hoy"] == [
        {
            "turno": "tarde",
            "numero": cierre.json()["numero"],
            "cerrada_at": cierre.json()["cerrada_at"],
            "propia": False,
        }
    ]
    assert api_a.get(f"{BASE}/escuelas/no-existe/").status_code == 404


# ------------------------------------------------------------- borradores


def test_borrador_upsert_e_idempotencia_por_revision(api_a, payload, nuevo_uuid):
    uuid = nuevo_uuid()
    url = f"{BASE}/borradores/{uuid}/"

    primera = api_a.put(url, payload(revision=7), format="json")
    assert primera.status_code == 200
    assert primera.json()["uuid"] == uuid
    assert primera.json()["revision"] == 7
    assert primera.json()["guardado_at"]

    cambiado = payload(revision=5)
    cambiado["respuestas"]["f16"] = "Llegó tarde, no pisa"
    vieja = api_a.put(url, cambiado, format="json")
    assert vieja.status_code == 200
    assert vieja.json()["revision"] == 7
    repetida = api_a.put(url, payload(revision=7), format="json")
    assert repetida.json() == primera.json()

    inspeccion = Inspeccion.objects.get(uuid=uuid)
    assert inspeccion.revision == 7
    assert inspeccion.payload["respuestas"]["f16"] == ""

    nueva = payload(revision=8)
    nueva["respuestas"]["f16"] = "Observación nueva"
    assert api_a.put(url, nueva, format="json").json()["revision"] == 8
    inspeccion.refresh_from_db()
    assert inspeccion.payload["respuestas"]["f16"] == "Observación nueva"


def test_borrador_revision_invalida_es_400(api_a, payload, nuevo_uuid):
    datos = payload()
    datos["revision"] = 0

    response = api_a.put(f"{BASE}/borradores/{nuevo_uuid()}/", datos, format="json")

    assert response.status_code == 400


def test_borrador_finalizado_responde_409_con_numero(api_a, payload, cerrar):
    uuid, cierre = cerrar(api_a)
    assert cierre.status_code == 200, cierre.json()

    response = api_a.put(
        f"{BASE}/borradores/{uuid}/", payload(revision=99), format="json"
    )

    assert response.status_code == 409
    assert response.json()["numero"] == cierre.json()["numero"]
    assert api_a.delete(f"{BASE}/borradores/{uuid}/").status_code == 409


def test_listar_y_descartar_borradores_propios(api_a, api_b, payload, nuevo_uuid):
    uuid = nuevo_uuid()
    api_a.put(f"{BASE}/borradores/{uuid}/", payload(revision=3), format="json")

    listado = api_a.get(f"{BASE}/borradores/").json()
    assert [b["uuid"] for b in listado] == [uuid]
    assert listado[0]["revision"] == 3
    assert listado[0]["respuestas"]["resultado"] == "constatado"
    assert api_b.get(f"{BASE}/borradores/").json() == []

    assert api_b.delete(f"{BASE}/borradores/{uuid}/").status_code == 404
    assert api_a.delete(f"{BASE}/borradores/{uuid}/").status_code == 204
    assert api_a.delete(f"{BASE}/borradores/{uuid}/").status_code == 204
    assert api_a.get(f"{BASE}/borradores/").json() == []
    inspeccion = Inspeccion.all_objects.get(uuid=uuid)
    assert inspeccion.deleted_at is not None
    assert inspeccion.eventos.filter(accion=EventoInspeccion.Accion.DESCARTADA).exists()


def test_inspector_b_no_puede_escribir_el_borrador_de_a(
    api_a, api_b, payload, nuevo_uuid
):
    uuid = nuevo_uuid()
    api_a.put(f"{BASE}/borradores/{uuid}/", payload(revision=1), format="json")

    response = api_b.put(
        f"{BASE}/borradores/{uuid}/", payload(revision=50), format="json"
    )

    assert response.status_code == 404
    assert Inspeccion.objects.get(uuid=uuid).revision == 1


# ------------------------------------------------------------- imágenes


def _subir(client, inspeccion_uuid, imagen_uuid, archivo, tipo="ingreso", **extra):
    return client.put(
        f"{BASE}/borradores/{inspeccion_uuid}/imagenes/{imagen_uuid}/",
        {"archivo": archivo, "tipo": tipo, **extra},
        format="multipart",
    )


def test_subir_imagen_idempotente_con_sha256(api_a, imagen, nuevo_uuid):
    inspeccion_uuid, imagen_uuid = nuevo_uuid(), nuevo_uuid()

    primera = _subir(
        api_a, inspeccion_uuid, imagen_uuid, imagen(), descripcion="Frente"
    )
    assert primera.status_code == 200, primera.json()
    assert len(primera.json()["sha256"]) == 64

    segunda = _subir(
        api_a, inspeccion_uuid, imagen_uuid, imagen(b"\xff\xd8\xff" + b"1" * 9)
    )
    assert segunda.json() == primera.json()
    assert ImagenInspeccion.objects.filter(uuid=imagen_uuid).count() == 1


def test_imagen_rechaza_tipos_no_permitidos_y_mas_de_10_mb(api_a, imagen, nuevo_uuid):
    inspeccion_uuid = nuevo_uuid()
    gif = imagen(b"GIF89a" + b"0" * 10, "x.gif", "image/jpeg")
    grande = imagen(b"\xff\xd8\xff" + b"0" * (10 * 1024 * 1024 + 1))

    assert _subir(api_a, inspeccion_uuid, nuevo_uuid(), gif).status_code == 422
    assert _subir(api_a, inspeccion_uuid, nuevo_uuid(), grande).status_code == 422


def test_hasta_10_imagenes_adicionales(api_a, imagen, nuevo_uuid):
    inspeccion_uuid = nuevo_uuid()
    for _ in range(10):
        respuesta = _subir(api_a, inspeccion_uuid, nuevo_uuid(), imagen(), "adicional")
        assert respuesta.status_code == 200

    extra = _subir(api_a, inspeccion_uuid, nuevo_uuid(), imagen(), "adicional")

    assert extra.status_code == 422


def test_imagen_descarga_con_permisos_y_borrado_antes_del_cierre(
    api_a, api_b, api_coord, imagen, nuevo_uuid
):
    inspeccion_uuid, imagen_uuid = nuevo_uuid(), nuevo_uuid()
    _subir(api_a, inspeccion_uuid, imagen_uuid, imagen())

    propia = api_a.get(f"{BASE}/imagenes/{imagen_uuid}/")
    assert propia.status_code == 200
    assert propia["Content-Type"] == "image/jpeg"
    assert propia["Cache-Control"] == "private, no-store"
    assert b"".join(propia.streaming_content).startswith(b"\xff\xd8\xff")
    assert api_b.get(f"{BASE}/imagenes/{imagen_uuid}/").status_code == 404
    assert api_coord.get(f"{BASE}/imagenes/{imagen_uuid}/").status_code == 200

    url = f"{BASE}/borradores/{inspeccion_uuid}/imagenes/{imagen_uuid}/"
    assert api_b.delete(url).status_code == 404
    assert api_a.delete(url).status_code == 204
    assert api_a.delete(url).status_code == 204
    assert api_a.get(f"{BASE}/imagenes/{imagen_uuid}/").status_code == 404
