"""Errores HTTP de la API territorial detectados por la auditoría de la app.

Un test por arreglo: sin 500 (ni HTML) bajo ``/api/``, "asignado o de mi zona"
para ver y adjuntar (S1, S3), pk no numérico (S4), validación de entrada del
acta (S5), borrado de fotos (S2), referente sin documento (S9b), carreras que
ahora dan 409 (S6, S9), coordenadas vacías (S7), errores JSON (S8) y firmas
verificadas e idempotentes (S9).
"""

import io
from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.http import Http404
from django.test import RequestFactory
from PIL import Image
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from comedores.api_views_territorial import TerritorialComedorViewSet
from comedores.models import Comedor, ImagenComedor, Programas
from config.api_errors import api_exception_handler
from core.models import Provincia
from relevamientos.models import (
    ActaComplementaria,
    PrimerSeguimiento,
    Referente,
    Relevamiento,
    SeguimientoPnud,
)
from relevamientos.serializer import RelevamientoSerializer
from relevamientos.service import (
    RelevamientoService,
    _upsert_referente_por_documento_data,
)
from users.models import TerritorialComedorProvincia

pytestmark = pytest.mark.django_db

VALIDADO = Relevamiento.ESTADO_VALIDACION_VALIDADO


def _territorial(nombre, provincias):
    user = get_user_model().objects.create_user(
        username=f"terr_{nombre}",
        email=f"terr_{nombre}@example.com",
        password="testpass123",
    )
    user.profile.es_territorial_comedor = True
    user.profile.save(update_fields=["es_territorial_comedor"])
    for provincia in provincias:
        TerritorialComedorProvincia.objects.create(
            profile=user.profile, provincia=provincia
        )
    return user


def _client(user):
    token, _ = Token.objects.get_or_create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client


def _png(nombre="foto.png", content_type="image/png"):
    buffer = io.BytesIO()
    Image.new("RGB", (2, 2), color="red").save(buffer, format="PNG")
    return SimpleUploadedFile(nombre, buffer.getvalue(), content_type=content_type)


def _zona_con_ancla_ajena(nombre):
    """Comedor de la zona del técnico cuyo relevamiento ancla está asignado a
    OTRO técnico: el técnico puede activar un seguimiento (POST) pero no tenía
    el comedor "asignado a mí"."""
    provincia = Provincia.objects.create(nombre=f"Prov {nombre}")
    comedor = Comedor.objects.create(nombre=f"Comedor {nombre}", provincia=provincia)
    tecnico = _territorial(nombre, [provincia])
    otro = _territorial(f"{nombre}_otro", [provincia])
    ancla = Relevamiento.objects.create(
        comedor=comedor, estado="Finalizado", territorial_user=otro
    )
    return tecnico, comedor, ancla


def _activar_seguimiento(client, comedor, uuid="seg-zona-1"):
    response = client.post(
        f"/api/territorial/comedores/{comedor.id}/seguimientos/",
        {"client_uuid": uuid, "tipo": PrimerSeguimiento.TIPO_POSTERIOR},
        format="json",
    )
    assert response.status_code == 201, response.content
    return response.json()["id"]


def _url_imagenes(comedor):
    return f"/api/territorial/comedores/{comedor.id}/imagenes/"


def _url_actas(comedor):
    return f"/api/territorial/comedores/{comedor.id}/actas-complementarias/"


# ------------------------------------------------------------- S1 / S3


def test_s1_imagenes_acepta_comedor_de_la_zona_con_ancla_de_otro_tecnico():
    tecnico, comedor, _ = _zona_con_ancla_ajena("s1")
    client = _client(tecnico)
    seguimiento_id = _activar_seguimiento(client, comedor)

    response = client.post(
        _url_imagenes(comedor),
        {"imagen": _png(), "seguimiento_id": seguimiento_id, "client_uuid": "f-1"},
        format="multipart",
    )

    assert response.status_code == 201, response.content
    foto = response.json()["imagenes"][0]
    assert foto["seguimiento"] == seguimiento_id
    assert foto["client_uuid"] == "f-1"
    assert ImagenComedor.objects.filter(comedor=comedor, origen="mobile").count() == 1


def test_s3_detalle_acepta_comedor_de_la_zona_y_muestra_el_seguimiento_creado():
    tecnico, comedor, ancla = _zona_con_ancla_ajena("s3")
    client = _client(tecnico)
    seguimiento_id = _activar_seguimiento(client, comedor)

    response = client.get(f"/api/territorial/comedores/{comedor.id}/")

    assert response.status_code == 200, response.content
    data = response.json()
    assert data["id"] == comedor.id
    assert [s["id"] for s in data["seguimientos"]["items"]] == [seguimiento_id]
    # En la zona se ve el ciclo completo del comedor, ancla incluida.
    assert [r["id"] for r in data["relevamientos"]["items"]] == [ancla.id]
    assert "seguimiento_anterior_mobile" in data


def test_s3_fuera_de_zona_y_sin_asignacion_sigue_siendo_404_json():
    tecnico, _, _ = _zona_con_ancla_ajena("s3_fuera")
    ajena = Provincia.objects.create(nombre="Prov ajena s3")
    comedor_ajeno = Comedor.objects.create(nombre="Ajeno", provincia=ajena)

    response = _client(tecnico).get(f"/api/territorial/comedores/{comedor_ajeno.id}/")

    assert response.status_code == 404
    assert response.json() == {"detail": "El comedor no pertenece a su zona."}


def test_s3_el_listado_sigue_siendo_solo_asignados_a_mi():
    tecnico, comedor, _ = _zona_con_ancla_ajena("s3_lista")

    response = _client(tecnico).get("/api/territorial/comedores/")

    assert response.status_code == 200
    assert comedor.id not in [row["id"] for row in response.json()["results"]]


def test_s3_asignado_fuera_de_la_zona_expone_solo_mis_relevamientos():
    provincia = Provincia.objects.create(nombre="Prov s3 asignado")
    comedor = Comedor.objects.create(nombre="Asignado lejos", provincia=provincia)
    tecnico = _territorial("s3_asignado", [])
    otro = _territorial("s3_asignado_otro", [provincia])
    mio = Relevamiento.objects.create(
        comedor=comedor, estado="Visita pendiente", territorial_user=tecnico
    )
    Relevamiento.objects.create(
        comedor=comedor, estado="Finalizado", territorial_user=otro
    )

    response = _client(tecnico).get(f"/api/territorial/comedores/{comedor.id}/")

    assert response.status_code == 200
    assert [r["id"] for r in response.json()["relevamientos"]["items"]] == [mio.id]


def test_s3_detalle_por_zona_no_expone_datos_pnud_de_otro_tecnico():
    """Regla D8 de N22: el detalle ampliado a la zona sigue sin mostrar
    ``datos`` ni ``observaciones_coordinador`` de los PNUD ajenos."""
    tecnico, comedor, _ = _zona_con_ancla_ajena("s3_d8")
    comedor.programa = Programas.objects.create(
        nombre="Abordaje comunitario - Línea Tradicional"
    )
    comedor.save(update_fields=["programa"])
    otro = _territorial("s3_d8_pnud", [comedor.provincia])
    ajeno = SeguimientoPnud.objects.create(
        comedor=comedor,
        tecnico=otro,
        formulario="iia",
        datos={"ent_nombre_apellido": "SECRETO", "ent_dni": "30111222"},
        observaciones_coordinador="Corregir el DNI 30111222",
        origen=SeguimientoPnud.ORIGEN_APP,
        asignado_desde_sisoc=False,
        client_uuid="pnud-ajeno-d8",
    )

    response = _client(tecnico).get(f"/api/territorial/comedores/{comedor.id}/")

    assert response.status_code == 200
    cuerpo = response.content.decode()
    assert "SECRETO" not in cuerpo
    assert "30111222" not in cuerpo
    items = response.json()["seguimientos_pnud"]["items"]
    assert [i["id"] for i in items] == [ajeno.id]
    assert "datos" not in items[0]
    assert items[0]["observaciones_coordinador"] is None


# -------------------------------------------------------------------- S4


@pytest.mark.parametrize(
    "metodo, sufijo",
    [
        ("get", ""),
        ("post", "relevamientos/"),
        ("post", "seguimientos/"),
        ("post", "actas-complementarias/"),
        ("post", "firma/"),
        ("post", "imagenes/"),
        ("get", "seguimientos-pnud/"),
        ("post", "seguimientos-pnud/"),
    ],
)
def test_s4_pk_no_numerico_devuelve_404_json(metodo, sufijo):
    tecnico, _, _ = _zona_con_ancla_ajena(f"s4_{metodo}_{sufijo.strip('/')}")
    client = _client(tecnico)

    response = getattr(client, metodo)(
        f"/api/territorial/comedores/loc_abc/{sufijo}", {}, format="json"
    )

    assert response.status_code == 404, response.content
    assert response["Content-Type"].startswith("application/json")
    assert response.json() == {"detail": "No encontrado."}


# -------------------------------------------------------------------- S5


@pytest.mark.parametrize(
    "payload",
    [
        {"prestaciones": [{"cantidad_actual": -1}]},
        {"prestaciones": [{"cantidad_actual": "abc"}]},
        {"prestaciones": [{"cantidad_espera": 10**12}]},
        {"prestaciones": [{"cantidad_actual": True}]},
        {"prestaciones": [{"cantidad_actual": 1.5}]},
        {"prestaciones": [{"dias_prestacion": "x" * 256}]},
        {"prestaciones": [{"tipo_prestacion": 5}]},
        {"prestaciones": [{}] * 101},
        {"fecha_hora": 20260927},
        {"firma": "f" * 601},
        {"observaciones": 42},
    ],
)
def test_s5_acta_rechaza_entrada_invalida_con_400_json(payload):
    tecnico, comedor, _ = _zona_con_ancla_ajena("s5")

    response = _client(tecnico).post(
        _url_actas(comedor),
        {"client_uuid": "acta-s5", "prestaciones": [], **payload},
        format="json",
    )

    assert response.status_code == 400, response.content
    assert response["Content-Type"].startswith("application/json")
    assert response.json()["detail"]
    assert not ActaComplementaria.objects.exists()


def test_s5_acta_acepta_cantidades_vacias_y_numeros_en_texto():
    tecnico, comedor, _ = _zona_con_ancla_ajena("s5_ok")

    response = _client(tecnico).post(
        _url_actas(comedor),
        {
            "client_uuid": "acta-s5-ok",
            "fecha_hora": "27/09/2026 10:30",
            "prestaciones": [
                {
                    "dias_prestacion": " Lunes ",
                    "tipo_prestacion": "Almuerzo",
                    "cantidad_actual": "12",
                    "cantidad_espera": "",
                }
            ],
        },
        format="json",
    )

    assert response.status_code == 201, response.content
    fila = response.json()["prestaciones"][0]
    assert fila["dias_prestacion"] == "Lunes"
    assert fila["cantidad_actual"] == 12
    assert fila["cantidad_espera"] is None


# -------------------------------------------------------------------- S2


def _subir_fotos(client, comedor, relevamiento, cantidad, prefijo):
    ultimo = None
    for i in range(cantidad):
        ultimo = client.post(
            _url_imagenes(comedor),
            {
                "imagen": _png(f"{prefijo}{i}.png"),
                "sisoc_id": relevamiento.id,
                "client_uuid": f"{prefijo}{i}",
            },
            format="multipart",
        )
        assert ultimo.status_code == 201, ultimo.content
    return ultimo


def test_s2_borrar_una_foto_libera_el_tope_para_corregir_y_reenviar():
    tecnico, comedor, ancla = _zona_con_ancla_ajena("s2")
    client = _client(tecnico)
    respuesta = _subir_fotos(client, comedor, ancla, 15, "s2-")
    primera = respuesta.json()["imagenes"][0]

    tope = client.post(
        _url_imagenes(comedor),
        {"imagen": _png(), "sisoc_id": ancla.id, "client_uuid": "s2-extra"},
        format="multipart",
    )
    borrado = client.delete(f"{_url_imagenes(comedor)}{primera['id']}/")
    de_nuevo = client.post(
        _url_imagenes(comedor),
        {"imagen": _png(), "sisoc_id": ancla.id, "client_uuid": "s2-extra"},
        format="multipart",
    )

    assert tope.status_code == 400
    assert "Borre alguna" in tope.json()["detail"]
    assert borrado.status_code == 200, borrado.content
    assert len(borrado.json()["imagenes"]) == 14
    assert not ImagenComedor.objects.filter(pk=primera["id"]).exists()
    assert de_nuevo.status_code == 201, de_nuevo.content
    assert ImagenComedor.objects.filter(comedor=comedor).count() == 15


def test_s2_borrar_foto_rechaza_web_validado_y_fuera_de_zona():
    tecnico, comedor, ancla = _zona_con_ancla_ajena("s2_no")
    client = _client(tecnico)
    web = ImagenComedor.objects.create(
        comedor=comedor, imagen=_png("web.png"), origen=ImagenComedor.ORIGEN_WEB
    )
    ancla.estado_validacion = VALIDADO
    ancla.save(update_fields=["estado_validacion"])
    validada = ImagenComedor.objects.create(
        comedor=comedor,
        imagen=_png("val.png"),
        origen=ImagenComedor.ORIGEN_MOBILE,
        relevamiento=ancla,
        subido_por=tecnico,
    )
    ajena = Provincia.objects.create(nombre="Prov ajena s2")
    comedor_ajeno = Comedor.objects.create(nombre="Ajeno s2", provincia=ajena)
    foto_ajena = ImagenComedor.objects.create(
        comedor=comedor_ajeno, imagen=_png("aj.png"), origen="mobile"
    )

    r_web = client.delete(f"{_url_imagenes(comedor)}{web.id}/")
    r_validada = client.delete(f"{_url_imagenes(comedor)}{validada.id}/")
    r_ajena = client.delete(f"{_url_imagenes(comedor_ajeno)}{foto_ajena.id}/")
    r_metodo = client.delete(f"/api/territorial/comedores/{comedor.id}/")
    r_inexistente = client.delete(f"{_url_imagenes(comedor)}999999/")

    assert r_web.status_code == 404
    assert r_validada.status_code == 409
    assert r_validada.json()["estado_validacion"] == VALIDADO
    assert r_ajena.status_code == 404
    assert r_metodo.status_code == 405
    # Idempotente para la app: "ya no existe" es 404, y la app lo toma como éxito.
    assert r_inexistente.status_code == 404
    assert ImagenComedor.objects.count() == 3


def test_s2_solo_el_tecnico_que_subio_la_foto_puede_borrarla():
    tecnico, comedor, ancla = _zona_con_ancla_ajena("s2_propia")
    otro = _territorial("s2_propia_tercero", [comedor.provincia])
    subida = _subir_fotos(_client(tecnico), comedor, ancla, 1, "s2-propia-")
    foto = subida.json()["imagenes"][0]
    # Fotos anteriores al campo `subido_por`: valen como propias solo si el
    # relevamiento (o el ancla del seguimiento) está asignado al técnico.
    mio = Relevamiento.objects.create(
        comedor=comedor, estado="Visita pendiente", territorial_user=tecnico
    )
    legado_mio = ImagenComedor.objects.create(
        comedor=comedor, imagen=_png("l1.png"), origen="mobile", relevamiento=mio
    )
    legado_ajeno = ImagenComedor.objects.create(
        comedor=comedor, imagen=_png("l2.png"), origen="mobile", relevamiento=ancla
    )
    assert ImagenComedor.objects.get(pk=foto["id"]).subido_por_id == tecnico.id

    r_otro = _client(otro).delete(f"{_url_imagenes(comedor)}{foto['id']}/")
    r_legado_ajeno = _client(tecnico).delete(
        f"{_url_imagenes(comedor)}{legado_ajeno.id}/"
    )
    r_legado_mio = _client(tecnico).delete(f"{_url_imagenes(comedor)}{legado_mio.id}/")
    r_propia = _client(tecnico).delete(f"{_url_imagenes(comedor)}{foto['id']}/")

    assert r_otro.status_code == 403
    assert "otro técnico" in r_otro.json()["detail"]
    assert r_legado_ajeno.status_code == 403
    assert r_legado_mio.status_code == 200
    assert r_propia.status_code == 200
    assert set(ImagenComedor.objects.values_list("pk", flat=True)) == {legado_ajeno.pk}


# ------------------------------------------------------------------- S9b


def test_s9b_referente_sin_documento_no_pisa_otro_referente():
    otro = Referente.objects.create(nombre="Otro", apellido="Sin DNI", documento=None)

    nuevo = _upsert_referente_por_documento_data({"nombre": "Nuevo", "documento": None})
    otro_mas = _upsert_referente_por_documento_data(
        {"nombre": "Vacío", "documento": ""}
    )

    otro.refresh_from_db()
    assert otro.nombre == "Otro"
    assert nuevo.pk != otro.pk and otro_mas.pk not in {otro.pk, nuevo.pk}
    assert Referente.objects.count() == 3


def test_s9b_referente_con_documento_se_sigue_reusando():
    existente = Referente.objects.create(nombre="Ana", documento=30111222)

    actualizado = _upsert_referente_por_documento_data(
        {"nombre": "Ana María", "documento": 30111222}
    )

    assert actualizado.pk == existente.pk
    assert Referente.objects.count() == 1
    assert actualizado.nombre == "Ana María"


# -------------------------------------------------------------------- S6


def test_s6_carrera_de_numero_orden_devuelve_409_json():
    tecnico, comedor, _ = _zona_con_ancla_ajena("s6")

    with mock.patch.object(
        PrimerSeguimiento, "save", side_effect=IntegrityError("unique numero_orden")
    ):
        response = _client(tecnico).post(
            f"/api/territorial/comedores/{comedor.id}/seguimientos/",
            {"client_uuid": "seg-s6", "tipo": PrimerSeguimiento.TIPO_POSTERIOR},
            format="json",
        )

    assert response.status_code == 409, response.content
    assert "Reintente" in response.json()["detail"]


# -------------------------------------------------------------------- S7


def test_s7_excepcion_convierte_coordenadas_vacias_en_none():
    parsed = RelevamientoService.populate_excepcion_data(
        {"latitud": "", "longitud": "  ", "descripcion": "sin georreferencia"}
    )

    assert parsed["latitud"] is None
    assert parsed["longitud"] is None
    assert parsed["descripcion"] == "sin georreferencia"


# -------------------------------------------------------------------- S8


def test_s8_404_de_ruteo_es_json_bajo_api_y_html_fuera():
    tecnico, _, _ = _zona_con_ancla_ajena("s8_404")
    client = _client(tecnico)

    api = client.get("/api/territorial/no-existe/")
    web = client.get("/no-existe/")

    assert api.status_code == 404
    assert api.json() == {"detail": "No encontrado."}
    assert web.status_code == 404
    assert not web["Content-Type"].startswith("application/json")


def test_s8_500_bajo_api_es_json():
    tecnico, comedor, _ = _zona_con_ancla_ajena("s8_500")
    client = _client(tecnico)
    client.raise_request_exception = False

    with mock.patch.object(
        TerritorialComedorViewSet, "retrieve", side_effect=RuntimeError("boom")
    ):
        response = client.get(f"/api/territorial/comedores/{comedor.id}/")

    assert response.status_code == 500
    assert response.json() == {"detail": "Error interno del servidor."}


@pytest.mark.parametrize(
    "path, mensaje, esperado",
    [
        ("/api/x/", "No Comedor matches the given query.", "No encontrado."),
        ("/api/x/", "Rendición no encontrada.", "Rendición no encontrada."),
        (
            "/web/x/",
            "No Comedor matches the given query.",
            "No Comedor matches the given query.",
        ),
    ],
)
def test_s8_http404_de_django_se_traduce_solo_bajo_api(path, mensaje, esperado):
    request = RequestFactory().get(path)

    response = api_exception_handler(Http404(mensaje), {"request": request})

    assert response.status_code == 404
    assert response.data == {"detail": esperado}


@pytest.mark.parametrize("url", ["/api/relevamiento", "/api/relevamiento/seguimiento"])
def test_s8_patch_legacy_con_cuerpo_lista_devuelve_400_string(url):
    tecnico, _, _ = _zona_con_ancla_ajena("s8_lista")

    response = _client(tecnico).patch(url, [{"sisoc_id": 1}], format="json")

    assert response.status_code == 400
    assert isinstance(response.data, str)
    assert "objeto JSON" in response.data


# -------------------------------------------------------------------- S9


def test_s9_firma_rechaza_svg_y_contenido_que_no_es_imagen():
    tecnico, comedor, _ = _zona_con_ancla_ajena("s9_svg")
    client = _client(tecnico)
    url = f"/api/territorial/comedores/{comedor.id}/firma/"
    svg = SimpleUploadedFile(
        "f.svg", b"<svg xmlns='http://www.w3.org/2000/svg'/>", "image/svg+xml"
    )
    falso = SimpleUploadedFile("f.png", b"no soy una imagen", "image/png")

    r_svg = client.post(url, {"firma": svg}, format="multipart")
    r_falso = client.post(url, {"firma": falso}, format="multipart")

    assert r_svg.status_code == 400
    assert r_falso.status_code == 400
    assert "imagen PNG" in r_falso.json()["detail"]


def test_s9_firma_con_client_uuid_es_idempotente(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    tecnico, comedor, _ = _zona_con_ancla_ajena("s9_idem")
    client = _client(tecnico)
    url = f"/api/territorial/comedores/{comedor.id}/firma/"

    primera = client.post(
        url, {"firma": _png("a.png"), "client_uuid": "firma-1"}, format="multipart"
    )
    reintento = client.post(
        url, {"firma": _png("b.png"), "client_uuid": "firma-1"}, format="multipart"
    )
    largo = client.post(
        url, {"firma": _png("c.png"), "client_uuid": "x" * 65}, format="multipart"
    )

    assert primera.status_code == 201, primera.content
    assert reintento.status_code == 200
    assert reintento.json()["url"] == primera.json()["url"]
    assert primera.json()["url"].endswith(".png")
    assert len(list((tmp_path / "firmas" / str(comedor.id)).iterdir())) == 1
    assert largo.status_code == 400


def test_s9_carrera_de_fecha_visita_en_patch_devuelve_409_string():
    tecnico, comedor, _ = _zona_con_ancla_ajena("s9_patch")
    relevamiento = Relevamiento.objects.create(comedor=comedor, estado="Pendiente")

    with mock.patch.object(
        RelevamientoSerializer, "save", side_effect=IntegrityError("unique fecha")
    ):
        response = _client(tecnico).patch(
            "/api/relevamiento",
            {"sisoc_id": relevamiento.id, "estado": "Finalizado"},
            format="json",
        )

    assert response.status_code == 409, response.content
    assert isinstance(response.data, str)
    assert "fecha de visita" in response.data
