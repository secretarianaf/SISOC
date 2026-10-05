"""Ajustes de la revisión del PR #2596 (QA 28/9).

1. El listado asignado junta los ids primero y filtra ``Comedor`` por PK (sin
   subconsultas por fila).
2. SISOC no asigna dos veces el mismo formulario PNUD o acta mientras haya uno
   sin terminar.
3. La migración 0021 pasa a "Pendiente validación coordinador" las actas que la
   app ya había enviado.
4. ``ActaComplementaria.sin_cargar`` consulta las prestaciones una sola vez.
"""

import importlib
import json

import pytest
from django.apps import apps as django_apps
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from comedores.models import Comedor, Programas
from core.models import Provincia
from relevamientos.models import (
    ActaComplementaria,
    PrestacionActaComplementaria,
    Relevamiento,
    SeguimientoPnud,
)
from users.models import TerritorialComedorProvincia

pytestmark = pytest.mark.django_db

PENDIENTE = ActaComplementaria.ESTADO_VALIDACION_PENDIENTE
A_SUBSANAR = ActaComplementaria.ESTADO_VALIDACION_A_SUBSANAR
VALIDADO = ActaComplementaria.ESTADO_VALIDACION_VALIDADO

migracion_0021 = importlib.import_module(
    "relevamientos.migrations.0021_actas_app_pendiente_validacion"
)


@pytest.fixture
def provincia():
    return Provincia.objects.create(nombre="Prov ajustes")


def _territorial(username, provincia):
    user = get_user_model().objects.create_user(username=username, password="x")
    user.profile.es_territorial_comedor = True
    user.profile.save(update_fields=["es_territorial_comedor"])
    TerritorialComedorProvincia.objects.create(
        profile=user.profile, provincia=provincia
    )
    return user


def _api(user):
    token, _ = Token.objects.get_or_create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client


def _comedor(provincia, nombre="Comedor", programa=None):
    return Comedor.objects.create(
        nombre=nombre,
        provincia=provincia,
        programa=Programas.objects.create(nombre=programa) if programa else None,
    )


# ------------------------------------------------ 1. listado asignado


def _poblar(provincia, territorial, sufijo):
    con_relevamiento = _comedor(provincia, f"Rel {sufijo}")
    Relevamiento.objects.create(
        comedor=con_relevamiento,
        estado="Visita pendiente",
        territorial_user=territorial,
    )
    con_pnud = _comedor(provincia, f"PNUD {sufijo}")
    SeguimientoPnud.objects.create(
        comedor=con_pnud, tecnico=territorial, formulario="secos"
    )
    con_acta = _comedor(provincia, f"Acta {sufijo}")
    ActaComplementaria.objects.create(comedor=con_acta, tecnico=territorial)
    _comedor(provincia, f"Ajeno {sufijo}")
    return {con_relevamiento.id, con_pnud.id, con_acta.id}


def _listar(api):
    with CaptureQueriesContext(connection) as queries:
        response = api.get("/api/territorial/comedores/")
    assert response.status_code == 200, response.content
    return {item["id"] for item in response.json()["results"]}, queries


def test_listado_asignado_filtra_comedor_por_pk_sin_subconsultas(provincia):
    territorial = _territorial("terr_listado", provincia)
    esperados = _poblar(provincia, territorial, "a")
    api = _api(territorial)

    ids, queries = _listar(api)

    assert ids == esperados
    tabla = Comedor._meta.db_table
    consultas_comedor = [
        q["sql"]
        for q in queries.captured_queries
        if q["sql"].startswith("SELECT") and f'FROM "{tabla}"' in q["sql"]
    ]
    assert consultas_comedor
    for sql in consultas_comedor:
        # Solo la lista de PKs: ni subconsultas ni JOIN con relevamientos.
        assert sql.count("SELECT") == 1, sql
        assert "DISTINCT" not in sql, sql


def test_listado_asignado_no_crece_en_consultas_con_mas_comedores(provincia):
    territorial = _territorial("terr_listado_n", provincia)
    _poblar(provincia, territorial, "a")
    api = _api(territorial)
    _, pocas = _listar(api)

    for sufijo in ("b", "c"):  # 9 comedores: entran en la primera página
        _poblar(provincia, territorial, sufijo)
    ids, muchas = _listar(api)

    assert len(ids) == 9
    assert len(muchas) == len(pocas)


def test_listado_asignado_excluye_relevamientos_borrados(provincia):
    territorial = _territorial("terr_listado_borrado", provincia)
    comedor = _comedor(provincia, "Solo borrado")
    relevamiento = Relevamiento.objects.create(
        comedor=comedor, estado="Visita pendiente", territorial_user=territorial
    )
    relevamiento.delete()

    ids, _ = _listar(_api(territorial))

    assert comedor.id not in ids


# ------------------------------------------------ 2. sin duplicados


def _login_backoffice(client):
    user = get_user_model().objects.create_user(username="bo_dup", password="x")
    user.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="relevamientos",
            codename__in=["add_relevamiento", "add_actacomplementaria"],
        )
    )
    client.force_login(user)


def _asignar(client, comedor, tipo, territorial):
    return client.post(
        reverse("relevamiento_create_edit_ajax", kwargs={"pk": comedor.pk}),
        {
            "tipo_relevamiento": tipo,
            "territorial": json.dumps(
                {"gestionar_uid": str(territorial.id), "nombre": "T"}
            ),
        },
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )


def test_no_asigna_dos_veces_el_mismo_pnud_sin_terminar(client, provincia):
    comedor = _comedor(provincia, programa="Abordaje comunitario - Línea Tradicional")
    territorial = _territorial("terr_dup_pnud", provincia)
    _login_backoffice(client)

    primero = _asignar(client, comedor, "pnud_iia", territorial)
    repetido = _asignar(client, comedor, "pnud_iia", territorial)
    otro_formulario = _asignar(client, comedor, "pnud_iib", territorial)

    assert primero.status_code == 200
    assert repetido.status_code == 400
    assert "sin terminar" in repetido.json()["error"]
    assert otro_formulario.status_code == 200
    assert SeguimientoPnud.objects.filter(formulario="iia").count() == 1

    # Pendiente de validación también bloquea; "A subsanar" y Validado no.
    SeguimientoPnud.objects.filter(formulario="iia").update(
        estado_validacion=PENDIENTE, datos={"x": 1}
    )
    assert _asignar(client, comedor, "pnud_iia", territorial).status_code == 400
    SeguimientoPnud.objects.filter(formulario="iia").update(estado_validacion=VALIDADO)
    assert _asignar(client, comedor, "pnud_iia", territorial).status_code == 200


def test_el_mismo_pnud_para_otro_territorial_si_se_asigna(client, provincia):
    comedor = _comedor(provincia, programa="Abordaje comunitario - Línea Secos")
    uno = _territorial("terr_dup_uno", provincia)
    dos = _territorial("terr_dup_dos", provincia)
    _login_backoffice(client)

    assert _asignar(client, comedor, "pnud_secos", uno).status_code == 200
    assert _asignar(client, comedor, "pnud_secos", dos).status_code == 200


def test_no_asigna_dos_actas_sin_terminar(client, provincia):
    comedor = _comedor(provincia, programa="Alimentar comunidad")
    territorial = _territorial("terr_dup_acta", provincia)
    _login_backoffice(client)

    primero = _asignar(client, comedor, "acta_complementaria", territorial)
    repetido = _asignar(client, comedor, "acta_complementaria", territorial)

    assert primero.status_code == 200
    assert repetido.status_code == 400
    assert ActaComplementaria.objects.count() == 1

    ActaComplementaria.objects.update(estado_validacion=A_SUBSANAR)
    assert (
        _asignar(client, comedor, "acta_complementaria", territorial).status_code == 200
    )


# ------------------------------------------------ 3. migración de datos


def test_migracion_0021_marca_pendientes_las_actas_enviadas_por_la_app(provincia):
    comedor = _comedor(provincia)
    con_texto = ActaComplementaria.objects.create(
        comedor=comedor, origen="app", observaciones="Cambio de prestación"
    )
    con_prestacion = ActaComplementaria.objects.create(comedor=comedor, origen="app")
    PrestacionActaComplementaria.objects.create(
        acta=con_prestacion, dias_prestacion="Lunes"
    )
    PrestacionActaComplementaria.objects.create(
        acta=con_prestacion, dias_prestacion="Martes"
    )
    vacia_app = ActaComplementaria.objects.create(comedor=comedor, origen="app")
    de_sisoc = ActaComplementaria.objects.create(
        comedor=comedor, origen="sisoc", observaciones="Cargada en SISOC"
    )
    revisada = ActaComplementaria.objects.create(
        comedor=comedor,
        origen="app",
        observaciones="Ya revisada",
        estado_validacion=A_SUBSANAR,
    )

    migracion_0021.marcar_pendientes(django_apps, None)

    def estado(acta):
        acta.refresh_from_db()
        return acta.estado_validacion

    assert estado(con_texto) == PENDIENTE
    assert estado(con_prestacion) == PENDIENTE
    assert estado(vacia_app) is None
    assert estado(de_sisoc) is None
    assert estado(revisada) == A_SUBSANAR

    migracion_0021.desmarcar_pendientes(django_apps, None)

    assert estado(con_texto) is None
    assert estado(con_prestacion) is None
    assert estado(revisada) == A_SUBSANAR


# ------------------------------------------------ 4. sin_cargar cacheado


def test_sin_cargar_consulta_las_prestaciones_una_sola_vez(provincia):
    comedor = _comedor(provincia)
    acta = ActaComplementaria.objects.create(comedor=comedor)
    acta = ActaComplementaria.objects.get(pk=acta.pk)

    with CaptureQueriesContext(connection) as queries:
        resultados = [acta.sin_cargar for _ in range(3)]

    assert resultados == [True, True, True]
    assert len(queries) == 1


def test_sin_cargar_usa_el_prefetch(provincia):
    comedor = _comedor(provincia)
    acta = ActaComplementaria.objects.create(comedor=comedor)
    PrestacionActaComplementaria.objects.create(acta=acta, dias_prestacion="Lunes")
    acta = ActaComplementaria.objects.prefetch_related("prestaciones").get(pk=acta.pk)

    with CaptureQueriesContext(connection) as queries:
        assert acta.sin_cargar is False

    assert len(queries) == 0


def test_detalle_del_acta_no_repite_la_consulta_de_prestaciones(client, provincia):
    comedor = _comedor(provincia)
    acta = ActaComplementaria.objects.create(comedor=comedor)
    user = get_user_model().objects.create_user(username="coord_nq", password="x")
    user.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="relevamientos",
            codename__in=["review_relevamiento", "view_relevamiento"],
        )
    )
    client.force_login(user)

    with CaptureQueriesContext(connection) as queries:
        response = client.get(
            reverse(
                "acta_complementaria_detalle",
                kwargs={"comedor_pk": comedor.id, "pk": acta.id},
            )
        )

    assert response.status_code == 200
    tabla = PrestacionActaComplementaria._meta.db_table
    consultas = [q for q in queries.captured_queries if f'FROM "{tabla}"' in q["sql"]]
    assert len(consultas) == 1
