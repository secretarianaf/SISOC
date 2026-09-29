"""``sin_cargar`` en las actas complementarias de la API territorial.

La app (1.1.54) lo usa para no ofrecer "Completar" sobre actas ya cargadas:
es ``True`` solo para un acta asignada desde SISOC que sigue vacia.
"""

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from comedores.models import Comedor
from core.models import Provincia
from relevamientos.models import ActaComplementaria, PrestacionActaComplementaria
from users.models import TerritorialComedorProvincia

pytestmark = pytest.mark.django_db


@pytest.fixture
def comedor():
    provincia = Provincia.objects.create(nombre="Prov sin cargar")
    return Comedor.objects.create(nombre="Comedor sin cargar", provincia=provincia)


@pytest.fixture
def territorial(comedor):
    user = get_user_model().objects.create_user(username="terr_sc", password="x")
    user.profile.es_territorial_comedor = True
    user.profile.save(update_fields=["es_territorial_comedor"])
    TerritorialComedorProvincia.objects.create(
        profile=user.profile, provincia=comedor.provincia
    )
    return user


@pytest.fixture
def api(territorial):
    token, _ = Token.objects.get_or_create(user=territorial)
    cliente = APIClient()
    cliente.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return cliente


def _acta_vacia(comedor, territorial):
    return ActaComplementaria.objects.create(
        comedor=comedor, tecnico=territorial, origen="sisoc"
    )


def _acta_cargada(comedor, territorial):
    acta = ActaComplementaria.objects.create(
        comedor=comedor,
        tecnico=territorial,
        fecha_hora=timezone.now(),
        observaciones="Cambio de prestacion",
    )
    PrestacionActaComplementaria.objects.create(
        acta=acta,
        dias_prestacion="Lunes",
        tipo_prestacion="Almuerzo",
        cantidad_actual=10,
    )
    return acta


def _listado(api, comedor):
    respuesta = api.get("/api/territorial/comedores/")
    assert respuesta.status_code == 200
    item = next(i for i in respuesta.json()["results"] if i["id"] == comedor.id)
    return item["actas_complementarias"]["items"]


def _detalle(api, comedor):
    respuesta = api.get(f"/api/territorial/comedores/{comedor.id}/")
    assert respuesta.status_code == 200
    return respuesta.json()["actas_complementarias"]["items"]


def test_acta_asignada_vacia_es_sin_cargar_en_listado_y_detalle(
    api, comedor, territorial
):
    acta = _acta_vacia(comedor, territorial)

    (fila_listado,) = _listado(api, comedor)
    (fila_detalle,) = _detalle(api, comedor)

    assert fila_listado["id"] == acta.id
    assert fila_listado["sin_cargar"] is True
    assert fila_detalle["sin_cargar"] is True


def test_acta_cargada_desde_el_backoffice_no_es_sin_cargar(api, comedor, territorial):
    _acta_cargada(comedor, territorial)

    (fila_listado,) = _listado(api, comedor)
    (fila_detalle,) = _detalle(api, comedor)

    assert fila_listado["sin_cargar"] is False
    assert fila_detalle["sin_cargar"] is False


def test_acta_solo_con_prestaciones_no_es_sin_cargar(api, comedor, territorial):
    acta = _acta_vacia(comedor, territorial)
    PrestacionActaComplementaria.objects.create(
        acta=acta, dias_prestacion="Martes", cantidad_actual=3
    )

    assert _listado(api, comedor)[0]["sin_cargar"] is False
    assert _detalle(api, comedor)[0]["sin_cargar"] is False


def test_el_listado_no_hace_una_consulta_por_acta(api, comedor, territorial):
    """Con actas vacias ``sin_cargar`` mira las prestaciones: el prefetch del
    listado evita el N+1 (la cantidad de consultas no depende de las actas)."""
    _acta_vacia(comedor, territorial)
    with CaptureQueriesContext(connection) as una:
        _listado(api, comedor)

    for _ in range(4):
        _acta_vacia(comedor, territorial)
    with CaptureQueriesContext(connection) as cinco:
        filas = _listado(api, comedor)

    assert len(filas) == 5
    assert all(fila["sin_cargar"] is True for fila in filas)
    assert len(cinco) == len(una)


def _patch(api, comedor, acta, **datos):
    return api.patch(
        f"/api/territorial/comedores/{comedor.id}/actas-complementarias/{acta.id}/",
        datos,
        format="json",
    )


def test_patch_sobre_acta_cargada_sin_estado_es_409_y_no_pisa(
    api, comedor, territorial
):
    acta = _acta_cargada(comedor, territorial)
    respuesta = _patch(
        api,
        comedor,
        acta,
        observaciones="Pisado por la app",
        prestaciones=[],
    )
    assert respuesta.status_code == 409
    assert "ya fue cargada en SISOC" in respuesta.json()["detail"]
    acta.refresh_from_db()
    assert acta.estado_validacion is None
    assert acta.observaciones == "Cambio de prestacion"
    assert acta.prestaciones.count() == 1


def test_patch_sobre_acta_vacia_asignada_pasa_a_pendiente_y_es_idempotente(
    api, comedor, territorial
):
    acta = _acta_vacia(comedor, territorial)
    assert acta.sin_cargar
    for _ in range(2):
        respuesta = _patch(api, comedor, acta, observaciones="Cargada desde la app")
        assert respuesta.status_code == 200
    acta.refresh_from_db()
    assert acta.estado_validacion == ActaComplementaria.ESTADO_VALIDACION_PENDIENTE
    assert acta.observaciones == "Cargada desde la app"


def test_patch_sobre_acta_a_subsanar_sigue_permitido(api, comedor, territorial):
    acta = _acta_cargada(comedor, territorial)
    acta.estado_validacion = ActaComplementaria.ESTADO_VALIDACION_A_SUBSANAR
    acta.save()
    respuesta = _patch(api, comedor, acta, observaciones="Subsanada")
    assert respuesta.status_code == 200
    acta.refresh_from_db()
    assert acta.estado_validacion == ActaComplementaria.ESTADO_VALIDACION_PENDIENTE
    assert acta.observaciones == "Subsanada"
