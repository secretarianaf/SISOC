"""T04: contratos AJAX de geografía, columnas y filtros favoritos que ya consumen las pantallas React.

No son pantallas: estas pruebas fijan forma, orden, mensajes y efectos persistidos para que un
cambio posterior falle acá y no en los consumidores (listados, formularios de domicilio).
"""

import json

import pytest
from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import Client

from core.models import (
    FiltroFavorito,
    Localidad,
    Municipio,
    PreferenciaColumnas,
    Provincia,
)
from core.services.favorite_filters import ConfiguracionFiltrosSeccion
from core.services.favorite_filters import registry

pytestmark = pytest.mark.django_db

SECCION = "t04_seccion_contrato"
FAVORITOS = "/ajax/filtros-favoritos/"
COLUMNAS = "/ajax/columnas-preferencias/"


@pytest.fixture(autouse=True)
def limpiar_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture(name="seccion")
def seccion_fixture(monkeypatch):
    configuracion = ConfiguracionFiltrosSeccion(
        tipos_campos={"nombre": "text"},
        operadores_permitidos={"text": ["contains", "empty"]},
    )
    monkeypatch.setitem(registry._CONFIGURACIONES_POR_SECCION, SECCION, configuracion)
    return SECCION


def _cliente(username="t04_user"):
    user = User.objects.create_user(username=username, password="x")
    client = Client()
    client.force_login(user)
    client.user = user
    return client


def _json(client, url, datos):
    return client.post(url, json.dumps(datos), content_type="application/json")


# --- Geografía -----------------------------------------------------------------------------


@pytest.fixture(name="geografia")
def geografia_fixture():
    provincia = Provincia.objects.create(nombre="Provincia T04")
    otra = Provincia.objects.create(nombre="Otra T04")
    zeta = Municipio.objects.create(nombre="Zeta", provincia=provincia)
    alfa = Municipio.objects.create(nombre="Alfa", provincia=provincia)
    ajeno = Municipio.objects.create(nombre="Ajeno", provincia=otra)
    loc_a = Localidad.objects.create(nombre="Loc A", municipio=alfa)
    loc_z = Localidad.objects.create(nombre="Loc Z", municipio=zeta)
    return {
        "provincia": provincia,
        "otra": otra,
        "zeta": zeta,
        "alfa": alfa,
        "ajeno": ajeno,
        "loc_a": loc_a,
        "loc_z": loc_z,
    }


def test_geografia_exige_sesion_y_solo_admite_get(geografia):
    for url in ("/ajax/load-municipios/", "/ajax/load-localidades/"):
        assert Client().get(url).status_code == 302
        assert _cliente(f"geo_{url[-6:-1]}").post(url).status_code == 405


def test_municipios_devuelve_id_y_nombre_ordenados_por_nombre(geografia):
    respuesta = _cliente().get(
        "/ajax/load-municipios/", {"provincia_id": geografia["provincia"].pk}
    )
    assert respuesta.status_code == 200
    assert respuesta.json() == [
        {"id": geografia["alfa"].pk, "nombre": "Alfa"},
        {"id": geografia["zeta"].pk, "nombre": "Zeta"},
    ]


def test_municipios_sin_provincia_o_inexistente_es_lista_vacia(geografia):
    cliente = _cliente()
    assert cliente.get("/ajax/load-municipios/").json() == []
    assert cliente.get("/ajax/load-municipios/", {"provincia_id": 0}).json() == []


def test_municipios_respeta_el_alcance_territorial(geografia, monkeypatch):
    provincia, otra = geografia["provincia"], geografia["otra"]
    cliente = _cliente()
    url = "/ajax/load-municipios/"

    monkeypatch.setattr(
        "core.views.get_geography_scope_map",
        lambda user: {provincia.pk: {geografia["zeta"].pk}},
    )
    assert cliente.get(url, {"provincia_id": provincia.pk}).json() == [
        {"id": geografia["zeta"].pk, "nombre": "Zeta"}
    ]
    assert cliente.get(url, {"provincia_id": otra.pk}).json() == []

    monkeypatch.setattr(
        "core.views.get_geography_scope_map", lambda user: {provincia.pk: None}
    )
    assert len(cliente.get(url, {"provincia_id": provincia.pk}).json()) == 2


def test_localidades_por_municipio_por_provincia_o_ninguna(geografia):
    cliente = _cliente()
    url = "/ajax/load-localidades/"
    por_municipio = cliente.get(url, {"municipio_id": geografia["alfa"].pk}).json()
    assert por_municipio == [{"id": geografia["loc_a"].pk, "nombre": "Loc A"}]
    por_provincia = cliente.get(url, {"provincia_id": geografia["provincia"].pk}).json()
    assert {item["nombre"] for item in por_provincia} == {"Loc A", "Loc Z"}
    assert cliente.get(url).json() == []
    # El municipio tiene prioridad sobre la provincia.
    ambos = cliente.get(
        url,
        {
            "municipio_id": geografia["zeta"].pk,
            "provincia_id": geografia["provincia"].pk,
        },
    ).json()
    assert ambos == [{"id": geografia["loc_z"].pk, "nombre": "Loc Z"}]


# --- Preferencias de columnas ----------------------------------------------------------------


def test_columnas_exige_sesion_y_rechaza_otros_metodos():
    assert Client().get(COLUMNAS, {"list_key": "x"}).status_code == 302
    assert _cliente("col_metodos").delete(COLUMNAS).status_code == 405


def test_columnas_get_sin_preferencia_y_listado_invalido():
    cliente = _cliente()
    assert cliente.get(COLUMNAS, {"list_key": "listado_t04"}).json() == {
        "list_key": "listado_t04",
        "columns": [],
    }
    invalido = cliente.get(COLUMNAS)
    assert invalido.status_code == 400
    assert invalido.json() == {"error": "Listado invalido."}


def test_columnas_post_guarda_normaliza_y_aisla_por_usuario():
    cliente = _cliente()
    respuesta = _json(
        cliente,
        COLUMNAS,
        {"list_key": "listado_t04", "columns": [" a ", "b", "a", "", "c"]},
    )
    assert respuesta.status_code == 200
    assert respuesta.json() == {"list_key": "listado_t04", "columns": ["a", "b", "c"]}
    guardada = PreferenciaColumnas.objects.get(
        usuario=cliente.user, listado="listado_t04"
    )
    assert guardada.columnas == ["a", "b", "c"]
    assert cliente.get(COLUMNAS, {"list_key": "listado_t04"}).json()["columns"] == [
        "a",
        "b",
        "c",
    ]
    otro = _cliente("col_otro")
    assert otro.get(COLUMNAS, {"list_key": "listado_t04"}).json()["columns"] == []
    _json(cliente, COLUMNAS, {"list_key": "listado_t04", "columns": ["z"]})
    assert PreferenciaColumnas.objects.filter(listado="listado_t04").count() == 1


def test_columnas_post_invalido_no_escribe():
    cliente = _cliente()
    assert _json(cliente, COLUMNAS, {"columns": ["a"]}).json() == {
        "error": "Listado invalido."
    }
    erroneo = _json(
        cliente, COLUMNAS, {"list_key": "listado_t04", "columns": "no-lista"}
    )
    assert (erroneo.status_code, erroneo.json()) == (
        400,
        {"error": "Columnas invalidas."},
    )
    assert PreferenciaColumnas.objects.count() == 0


def test_columnas_reset_borra_la_preferencia():
    cliente = _cliente()
    _json(cliente, COLUMNAS, {"list_key": "listado_t04", "columns": ["a"]})
    respuesta = _json(cliente, COLUMNAS, {"list_key": "listado_t04", "reset": "1"})
    assert respuesta.json() == {"list_key": "listado_t04", "columns": []}
    assert PreferenciaColumnas.objects.count() == 0


# --- Filtros favoritos -------------------------------------------------------------------------


def _filtros(valor="x"):
    return {
        "logic": "or",
        "items": [{"field": "nombre", "op": "contains", "value": valor}],
    }


def test_favoritos_exige_sesion_y_valida_la_seccion(seccion):
    assert Client().get(FAVORITOS, {"seccion": seccion}).status_code == 302
    cliente = _cliente()
    invalida = cliente.get(FAVORITOS, {"seccion": "no_existe"})
    assert (invalida.status_code, invalida.json()) == (
        400,
        {"error": "Seccion invalida."},
    )
    assert cliente.get(FAVORITOS).status_code == 400


def test_favoritos_alta_listado_y_detalle(seccion):
    cliente = _cliente()
    creado = _json(
        cliente,
        FAVORITOS,
        {"seccion": seccion, "nombre": "  Mi filtro ", "filtros": _filtros()},
    )
    assert creado.status_code == 201
    datos = creado.json()
    assert (datos["nombre"], datos["seccion"]) == ("Mi filtro", seccion)
    favorito = FiltroFavorito.objects.get(pk=datos["id"])
    assert favorito.usuario == cliente.user
    assert favorito.filtros == {"logic": "OR", "items": _filtros()["items"]}
    listado = cliente.get(FAVORITOS, {"seccion": seccion}).json()
    assert listado["seccion"] == seccion
    assert [(f["id"], f["nombre"]) for f in listado["favoritos"]] == [
        (favorito.pk, "Mi filtro")
    ]
    detalle = cliente.get(f"{FAVORITOS}{favorito.pk}/", {"seccion": seccion})
    assert detalle.json() == {
        "id": favorito.pk,
        "nombre": "Mi filtro",
        "filtros": favorito.filtros,
    }


def test_favoritos_alta_rechazada_no_escribe(seccion):
    cliente = _cliente()
    cliente_post = lambda datos: _json(cliente, FAVORITOS, datos)  # noqa: E731
    sin_nombre = cliente_post(
        {"seccion": seccion, "nombre": " ", "filtros": _filtros()}
    )
    assert (sin_nombre.status_code, sin_nombre.json()) == (
        400,
        {"error": "El nombre es obligatorio."},
    )
    sin_seccion = cliente_post({"nombre": "a", "filtros": _filtros()})
    assert sin_seccion.json() == {"error": "Seccion invalida."}
    invalidos = cliente_post({"seccion": seccion, "nombre": "a", "filtros": "no-json{"})
    assert invalidos.json() == {"error": "Filtros invalidos."}
    obsoleto = cliente_post(
        {
            "seccion": seccion,
            "nombre": "a",
            "filtros": {"items": [{"field": "viejo", "op": "contains", "value": "x"}]},
        }
    )
    assert obsoleto.status_code == 409
    assert obsoleto.json() == {
        "error": "El filtro contiene parametros obsoletos.",
        "items_obsoletos": [{"indice": 0, "motivo": "campo"}],
    }
    assert FiltroFavorito.objects.count() == 0


def test_favoritos_nombre_repetido_sin_distinguir_mayusculas(seccion):
    cliente = _cliente()
    _json(
        cliente,
        FAVORITOS,
        {"seccion": seccion, "nombre": "Repetido", "filtros": _filtros()},
    )
    repetido = _json(
        cliente,
        FAVORITOS,
        {"seccion": seccion, "nombre": "REPETIDO", "filtros": _filtros()},
    )
    assert (repetido.status_code, repetido.json()) == (
        400,
        {"error": "El nombre ya existe."},
    )
    assert FiltroFavorito.objects.count() == 1
    otro = _cliente("fav_otro")
    assert (
        _json(
            otro,
            FAVORITOS,
            {"seccion": seccion, "nombre": "Repetido", "filtros": _filtros()},
        ).status_code
        == 201
    )


def test_favoritos_baja_solo_del_dueno_y_limpia_el_listado(seccion):
    cliente = _cliente()
    favorito = FiltroFavorito.objects.get(
        pk=_json(
            cliente,
            FAVORITOS,
            {"seccion": seccion, "nombre": "Baja", "filtros": _filtros()},
        ).json()["id"]
    )
    assert len(cliente.get(FAVORITOS, {"seccion": seccion}).json()["favoritos"]) == 1
    ajeno = _cliente("fav_ajeno")
    rechazo = ajeno.delete(f"{FAVORITOS}{favorito.pk}/")
    assert (rechazo.status_code, rechazo.json()) == (
        404,
        {"error": "Filtro favorito no encontrado."},
    )
    assert FiltroFavorito.objects.filter(pk=favorito.pk).exists()
    baja = cliente.delete(f"{FAVORITOS}{favorito.pk}/")
    assert (baja.status_code, baja.json()) == (200, {"exito": True})
    assert not FiltroFavorito.objects.filter(pk=favorito.pk).exists()
    assert cliente.get(FAVORITOS, {"seccion": seccion}).json()["favoritos"] == []


def test_favoritos_detalle_con_seccion_distinta_u_obsoleto(seccion, monkeypatch):
    cliente = _cliente()
    favorito = FiltroFavorito.objects.create(
        usuario=cliente.user,
        seccion=seccion,
        nombre="Viejo",
        filtros={
            "logic": "AND",
            "items": [{"field": "viejo", "op": "contains", "value": "x"}],
        },
    )
    distinta = cliente.get(f"{FAVORITOS}{favorito.pk}/", {"seccion": "otra"})
    assert (distinta.status_code, distinta.json()) == (
        400,
        {"error": "Seccion invalida."},
    )
    obsoleto = cliente.get(f"{FAVORITOS}{favorito.pk}/", {"seccion": seccion})
    assert obsoleto.status_code == 409
    assert obsoleto.json()["items_obsoletos"] == [{"indice": 0, "motivo": "campo"}]
    assert cliente.get(f"{FAVORITOS}0/").status_code == 404
