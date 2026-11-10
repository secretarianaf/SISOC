"""Tests de las altas desde la app: zona/activación autónoma (N18) y acta
complementaria extraordinaria (N15).

Regla de permisos acordada: el territorial puede CREAR, pero **solo** sobre
comedores de sus provincias (su zona), con ``client_uuid`` idempotente y los
registros marcados con ``origen="app"``.
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from comedores.models import Comedor
from core.models import Provincia
from relevamientos.models import (
    ActaComplementaria,
    PrestacionActaComplementaria,
    PrimerSeguimiento,
    Relevamiento,
)
from users.models import TerritorialComedorProvincia

ZONA_URL = "/api/territorial/comedores-zona/"


def _token_client(user):
    token, _ = Token.objects.get_or_create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client


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


def _escenario(nombre):
    """Territorial con una provincia y un comedor de su zona SIN asignaciones."""
    provincia = Provincia.objects.create(nombre=f"Prov {nombre}")
    comedor = Comedor.objects.create(nombre=f"Comedor {nombre}", provincia=provincia)
    user = _territorial(nombre, [provincia])
    return user, comedor, provincia


def _url_relevamientos(comedor):
    return f"/api/territorial/comedores/{comedor.id}/relevamientos/"


def _url_seguimientos(comedor):
    return f"/api/territorial/comedores/{comedor.id}/seguimientos/"


def _url_actas(comedor):
    return f"/api/territorial/comedores/{comedor.id}/actas-complementarias/"


# --------------------------------------------------------------------------- #
# N18 (a) — listado de zona
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_zona_lista_comedores_de_mis_provincias_sin_asignacion():
    user, comedor, _ = _escenario("zona")
    prov_ajena = Provincia.objects.create(nombre="Prov ajena zona")
    Comedor.objects.create(nombre="Comedor ajeno", provincia=prov_ajena)

    response = _token_client(user).get(ZONA_URL)

    assert response.status_code == 200
    ids = [row["id"] for row in response.data["results"]]
    # Aparece aunque no tenga NADA asignado: es el punto de N18.
    assert ids == [comedor.id]
    fila = response.data["results"][0]
    # Serializer liviano: sin relevamientos ni seguimientos.
    assert "relevamientos" not in fila
    assert "seguimientos" not in fila
    assert fila["provincia"] == comedor.provincia.nombre


@pytest.mark.django_db
def test_zona_busca_por_nombre_localidad_o_municipio():
    """``?search=`` filtra en el servidor: con miles de comedores por provincia
    el filtro solo sobre lo ya paginado en la app no alcanza."""
    user, comedor, provincia = _escenario("zona_search")
    otro = Comedor.objects.create(nombre="Merendero Sur", provincia=provincia)
    client = _token_client(user)

    por_nombre = client.get(ZONA_URL, {"search": "merendero"})
    todos = client.get(ZONA_URL, {"search": ""})
    sin_match = client.get(ZONA_URL, {"search": "inexistente-xyz"})

    assert [row["id"] for row in por_nombre.data["results"]] == [otro.id]
    assert {row["id"] for row in todos.data["results"]} == {comedor.id, otro.id}
    assert sin_match.data["results"] == []


@pytest.mark.django_db
def test_zona_vacia_para_territorial_sin_provincias():
    user = _territorial("zona_sin_prov", [])

    response = _token_client(user).get(ZONA_URL)

    assert response.status_code == 200
    assert response.data["results"] == []


@pytest.mark.django_db
def test_zona_rechaza_no_territorial():
    user = get_user_model().objects.create_user(
        username="no_terr_zona",
        email="no_terr_zona@example.com",
        password="testpass123",
    )

    assert _token_client(user).get(ZONA_URL).status_code == 403


# --------------------------------------------------------------------------- #
# #2781 — el territorial ya no crea relevamientos iniciales
# --------------------------------------------------------------------------- #

DETALLE_403 = (
    "Los relevamientos iniciales se asignan desde SISOC; "
    "no se pueden crear desde la app."
)


@pytest.mark.django_db
def test_crear_relevamiento_desde_la_app_devuelve_403_y_no_crea_nada():
    user, comedor, _ = _escenario("alta_rel")

    response = _token_client(user).post(
        _url_relevamientos(comedor),
        {"client_uuid": "uuid-rel-1", "fecha_visita": "04/09/2026 10:00"},
        format="json",
    )

    assert response.status_code == 403
    assert response.data["detail"] == DETALLE_403
    assert not Relevamiento.all_objects.filter(comedor=comedor).exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"client_uuid": "uuid-rel-fecha", "fecha_visita": "2026-09-04"},
    ],
)
def test_crear_relevamiento_siempre_403_sin_importar_el_payload(payload):
    user, comedor, _ = _escenario("alta_rel_payload")

    response = _token_client(user).post(
        _url_relevamientos(comedor), payload, format="json"
    )

    assert response.status_code == 403
    assert not Relevamiento.all_objects.filter(comedor=comedor).exists()


@pytest.mark.django_db
def test_crear_relevamiento_con_uno_activo_tambien_devuelve_403():
    user, comedor, _ = _escenario("alta_rel_activo")
    Relevamiento.objects.create(comedor=comedor, estado="Visita pendiente")

    response = _token_client(user).post(
        _url_relevamientos(comedor),
        {"client_uuid": "uuid-rel-activo"},
        format="json",
    )

    assert response.status_code == 403
    assert Relevamiento.objects.filter(comedor=comedor).count() == 1


@pytest.mark.django_db
def test_reintento_de_un_alta_previa_devuelve_el_registro_existente():
    """Apps viejas con el alta en la cola offline: si el uuid ya corresponde a
    un relevamiento de ESTE comedor, se devuelve (200) en vez de trabar la cola."""
    user, comedor, _ = _escenario("alta_rel_idem")
    existente = Relevamiento.objects.create(
        comedor=comedor,
        estado="Visita pendiente",
        origen=Relevamiento.ORIGEN_APP,
        asignado_desde_sisoc=False,
        client_uuid="uuid-rel-idem",
    )

    response = _token_client(user).post(
        _url_relevamientos(comedor), {"client_uuid": "uuid-rel-idem"}, format="json"
    )

    assert response.status_code == 200
    assert response.data["id"] == existente.id
    assert Relevamiento.objects.filter(comedor=comedor).count() == 1


@pytest.mark.django_db
def test_uuid_de_otro_comedor_no_se_devuelve_y_da_403():
    user, comedor, provincia = _escenario("alta_rel_otro")
    otro = Comedor.objects.create(nombre="Otro comedor", provincia=provincia)
    Relevamiento.objects.create(
        comedor=otro, estado="Visita pendiente", client_uuid="uuid-rel-otro"
    )

    response = _token_client(user).post(
        _url_relevamientos(comedor), {"client_uuid": "uuid-rel-otro"}, format="json"
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_crear_relevamiento_fuera_de_zona_devuelve_404():
    user, _, _ = _escenario("alta_rel_zona")
    prov_ajena = Provincia.objects.create(nombre="Prov ajena alta")
    comedor_ajeno = Comedor.objects.create(
        nombre="Comedor fuera de zona", provincia=prov_ajena
    )

    response = _token_client(user).post(
        _url_relevamientos(comedor_ajeno),
        {"client_uuid": "uuid-rel-fuera"},
        format="json",
    )

    assert response.status_code == 404
    assert not Relevamiento.objects.filter(comedor=comedor_ajeno).exists()


@pytest.mark.django_db
def test_relevamiento_asignado_desde_sisoc_se_sigue_completando_desde_la_app():
    user, comedor, _ = _escenario("alta_rel_asignado")
    relevamiento = Relevamiento.objects.create(
        comedor=comedor, estado="Visita pendiente", territorial_user=user
    )

    response = _token_client(user).patch(
        "/api/relevamiento", {"sisoc_id": relevamiento.id}, format="json"
    )

    assert response.status_code != 403
    assert response.status_code != 404


# --------------------------------------------------------------------------- #
# N18 (b) — alta de instancia de seguimiento
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_crear_seguimiento_toma_el_siguiente_numero_orden():
    user, comedor, _ = _escenario("alta_seg")
    relevamiento = Relevamiento.objects.create(
        comedor=comedor, estado="Finalizado", territorial_user=user
    )
    PrimerSeguimiento.objects.create(
        id_relevamiento=relevamiento,
        tipo=PrimerSeguimiento.TIPO_PRIMER,
        numero_orden=1,
        estado=PrimerSeguimiento.ESTADO_COMPLETO,
    )

    response = _token_client(user).post(
        _url_seguimientos(comedor),
        {"client_uuid": "uuid-seg-1", "tipo": "posterior"},
        format="json",
    )

    assert response.status_code == 201
    assert response.data["numero_orden"] == 2
    assert response.data["tipo"] == "posterior"
    assert response.data["origen"] == PrimerSeguimiento.ORIGEN_APP
    assert response.data["asignado_desde_sisoc"] is False


@pytest.mark.django_db
def test_crear_seguimiento_rechaza_tipo_primer():
    """`primer` siempre lo asigna SISOC: no se crea desde la app."""
    user, comedor, _ = _escenario("alta_seg_primer")
    Relevamiento.objects.create(comedor=comedor, estado="Finalizado")

    response = _token_client(user).post(
        _url_seguimientos(comedor),
        {"client_uuid": "uuid-seg-primer", "tipo": "primer"},
        format="json",
    )

    assert response.status_code == 400
    assert not PrimerSeguimiento.objects.exists()


@pytest.mark.django_db
def test_crear_seguimiento_sin_relevamiento_ancla_devuelve_409():
    user, comedor, _ = _escenario("alta_seg_sin_ancla")

    response = _token_client(user).post(
        _url_seguimientos(comedor),
        {"client_uuid": "uuid-seg-sin-ancla", "tipo": "virtual"},
        format="json",
    )

    assert response.status_code == 409
    assert not PrimerSeguimiento.objects.exists()


@pytest.mark.django_db
def test_crear_seguimiento_es_idempotente_por_client_uuid():
    user, comedor, _ = _escenario("alta_seg_idem")
    Relevamiento.objects.create(comedor=comedor, estado="Finalizado")
    client = _token_client(user)
    payload = {"client_uuid": "uuid-seg-idem", "tipo": "acta_excepcion"}

    primera = client.post(_url_seguimientos(comedor), payload, format="json")
    segunda = client.post(_url_seguimientos(comedor), payload, format="json")

    assert primera.status_code == 201
    assert segunda.status_code == 200
    assert segunda.data["id"] == primera.data["id"]
    assert PrimerSeguimiento.objects.count() == 1


# --------------------------------------------------------------------------- #
# N15 — acta complementaria extraordinaria
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_crear_acta_complementaria_con_prestaciones():
    user, comedor, _ = _escenario("acta")

    response = _token_client(user).post(
        _url_actas(comedor),
        {
            "client_uuid": "uuid-acta-1",
            "fecha_hora": "04/09/2026 11:20",
            "observaciones": "Amplía almuerzo por demanda",
            "firma": "https://example.com/firma.png",
            "prestaciones": [
                {
                    "dias_prestacion": "Lunes",
                    "tipo_prestacion": "Almuerzo",
                    "cantidad_actual": 120,
                    "cantidad_espera": 15,
                },
                {
                    "dias_prestacion": "Martes",
                    "tipo_prestacion": "Cena",
                    "cantidad_actual": 80,
                    "cantidad_espera": 0,
                },
            ],
        },
        format="json",
    )

    assert response.status_code == 201
    acta = ActaComplementaria.objects.get(pk=response.data["id"])
    assert acta.comedor_id == comedor.id
    assert acta.tecnico_id == user.id
    assert acta.origen == ActaComplementaria.ORIGEN_APP
    assert acta.fecha_hora is not None
    assert PrestacionActaComplementaria.objects.filter(acta=acta).count() == 2
    assert len(response.data["prestaciones"]) == 2


@pytest.mark.django_db
def test_crear_acta_es_idempotente_y_no_duplica_prestaciones():
    user, comedor, _ = _escenario("acta_idem")
    client = _token_client(user)
    payload = {
        "client_uuid": "uuid-acta-idem",
        "observaciones": "x",
        "prestaciones": [
            {
                "dias_prestacion": "Lunes",
                "tipo_prestacion": "Almuerzo",
                "cantidad_actual": 10,
                "cantidad_espera": 1,
            }
        ],
    }

    primera = client.post(_url_actas(comedor), payload, format="json")
    segunda = client.post(_url_actas(comedor), payload, format="json")

    assert primera.status_code == 201
    assert segunda.status_code == 200
    assert segunda.data["id"] == primera.data["id"]
    assert ActaComplementaria.objects.count() == 1
    assert PrestacionActaComplementaria.objects.count() == 1


@pytest.mark.django_db
def test_crear_acta_fuera_de_zona_devuelve_404():
    user, _, _ = _escenario("acta_zona")
    prov_ajena = Provincia.objects.create(nombre="Prov ajena acta")
    comedor_ajeno = Comedor.objects.create(
        nombre="Comedor acta ajeno", provincia=prov_ajena
    )

    response = _token_client(user).post(
        _url_actas(comedor_ajeno),
        {"client_uuid": "uuid-acta-fuera"},
        format="json",
    )

    assert response.status_code == 404
    assert not ActaComplementaria.objects.exists()


@pytest.mark.django_db
def test_crear_acta_con_prestaciones_mal_formadas_devuelve_400():
    user, comedor, _ = _escenario("acta_formato")

    response = _token_client(user).post(
        _url_actas(comedor),
        {"client_uuid": "uuid-acta-formato", "prestaciones": "Lunes"},
        format="json",
    )

    assert response.status_code == 400
    assert not ActaComplementaria.objects.exists()


@pytest.mark.django_db
def test_las_actas_aparecen_en_el_detalle_del_comedor():
    user, comedor, _ = _escenario("acta_detalle")
    # El detalle exige comedor asignado (scope de lectura).
    Relevamiento.objects.create(
        comedor=comedor, estado="Visita pendiente", territorial_user=user
    )
    client = _token_client(user)
    client.post(
        _url_actas(comedor),
        {
            "client_uuid": "uuid-acta-detalle",
            "observaciones": "Cambio de prestación",
            "prestaciones": [
                {
                    "dias_prestacion": "Lunes",
                    "tipo_prestacion": "Almuerzo",
                    "cantidad_actual": 50,
                    "cantidad_espera": 5,
                }
            ],
        },
        format="json",
    )

    response = client.get(f"/api/territorial/comedores/{comedor.id}/")

    assert response.status_code == 200
    actas = response.data["actas_complementarias"]
    assert actas["total"] == 1
    assert actas["items"][0]["observaciones"] == "Cambio de prestación"
    assert len(actas["items"][0]["prestaciones"]) == 1


@pytest.mark.django_db
def test_reintento_con_uuid_de_relevamiento_soft_deleted_no_da_500():
    """El UNIQUE de client_uuid incluye los soft-deleted; la idempotencia tambien.

    Escenario real: la app crea, SISOC lo borra logicamente, la cola offline
    reintenta el mismo uuid. Antes: IntegrityError -> 500 en cada reintento.
    Desde #2781 ya no se crea, pero el reintento sigue devolviendo el registro.
    """
    user, comedor, _ = _escenario("alta_rel_borrado")
    client = _token_client(user)
    payload = {"client_uuid": "uuid-rel-borrado"}
    primera = Relevamiento.objects.create(
        comedor=comedor, estado="Visita pendiente", client_uuid="uuid-rel-borrado"
    )
    primera.delete()  # soft-delete

    reintento = client.post(_url_relevamientos(comedor), payload, format="json")

    assert reintento.status_code == 200
    assert reintento.data["id"] == primera.id
    # No se creo un segundo registro con el mismo uuid.
    assert Relevamiento.all_objects.filter(client_uuid="uuid-rel-borrado").count() == 1
