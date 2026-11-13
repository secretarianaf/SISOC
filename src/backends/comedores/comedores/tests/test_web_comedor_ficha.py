"""Web API (G1 v1) of the comedor ficha: ``/api/web/comedores/comedores/<pk>/`` (CO07.01).

The endpoint runs the native ``ComedorDetailView``; these tests compare its JSON
with what ``comedor_detail.html`` shows and check that reading never writes.
"""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client

from admisiones.models.admisiones import Admision
from comedores.models import Comedor, Programas
from core.models import Localidad, Municipio, Provincia
from organizaciones.models import Organizacion
from comedores.utils import get_prestacion_conformidad_pending_period
from core import web_gate

pytestmark = pytest.mark.django_db
ROOT = "/api/web/comedores/comedores/"


@pytest.fixture(name="comedor_fixture", autouse=True)
def sin_dobles_del_conftest():
    """Same name as the folder's autouse double: the ficha runs the real services."""


def _ready(user):
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    return user


def _client(username, *codenames):
    usuario = _ready(get_user_model().objects.create_user(username, password="x"))
    for codename in codenames:
        usuario.user_permissions.add(Permission.objects.get(codename=codename))
    client = Client()
    client.force_login(usuario)
    return client


@pytest.fixture(name="lector")
def lector_fixture():
    return _client("lector_ficha", "view_comedor")


@pytest.fixture(name="comedor")
def comedor_fixture():
    return Comedor.objects.create(nombre="Comedor Norte")


def test_header_and_title_project_the_native_blocks(lector, comedor):
    datos = lector.get(f"{ROOT}{comedor.pk}/").json()

    assert datos["id"] == comedor.pk
    assert datos["nombre"] == "Comedor Norte"
    header = datos["header"]
    assert header["acciones"]["editar"] == f"/comedores/{comedor.pk}/editar"
    assert header["acciones"]["eliminar"] == f"/comedores/{comedor.pk}/eliminar"
    assert header["acciones"]["equipo_tecnico"] is None
    assert header["acciones"]["responsable_tarjeta"] is None
    assert header["validar"] is False
    assert header["historial"] is None
    assert header["convenios"] == []
    assert (
        header["acompanamiento_territorial"]
        == f"/comedores/{comedor.pk}/relevamiento/listar"
    )
    titulo = datos["titulo"]
    assert titulo["nombre"] == "Comedor Norte"
    assert titulo["programa"] == "Sin programa"
    periodo = get_prestacion_conformidad_pending_period(comedor)
    assert titulo["conformidad_pendiente"] == (
        None if periodo is None else {"periodo": periodo.strftime("%m/%Y")}
    )
    assert titulo["inicio_ejecucion"] is None
    assert datos["messages"] == []


def test_convenios_selector_marks_the_selected_one_and_keeps_the_query(lector, comedor):
    primera = Admision.objects.create(comedor=comedor, activa=False)
    segunda = Admision.objects.create(comedor=comedor, activa=True)

    datos = lector.get(f"{ROOT}{comedor.pk}/", {"admision_id": primera.pk}).json()

    convenios = {c["id"]: c for c in datos["header"]["convenios"]}
    assert set(convenios) == {primera.pk, segunda.pk}
    assert convenios[primera.pk]["seleccionada"] is True
    assert convenios[segunda.pk]["seleccionada"] is False
    assert convenios[segunda.pk]["url"].endswith(f"admision_id={segunda.pk}")
    assert datos["titulo"]["inicio_ejecucion"] == primera.creado.strftime("%d/%m/%Y")


def test_actions_follow_the_permissions_the_template_checks(comedor):
    admin = Client()
    admin.force_login(
        _ready(get_user_model().objects.create_superuser("admin_ficha", password="x"))
    )

    header = admin.get(f"{ROOT}{comedor.pk}/").json()["header"]

    assert header["historial"] == f"/auditoria/comedores/comedor/{comedor.pk}/"
    assert header["acciones"]["equipo_tecnico"]["label"] == "Asignar Equipo Técnico"
    assert header["acciones"]["comenzar_admision"] is False


def test_a_comedor_outside_the_scope_or_missing_is_404(lector, comedor):
    assert lector.get(f"{ROOT}999999/").status_code == 404
    assert lector.get(f"{ROOT}{comedor.pk}/").status_code == 200


def test_reading_the_ficha_writes_nothing(lector, comedor):
    antes = list(Comedor.objects.values())
    admisiones = Admision.objects.count()

    lector.get(f"{ROOT}{comedor.pk}/")

    assert list(Comedor.objects.values()) == antes
    assert Admision.objects.count() == admisiones


def test_only_get_is_served(lector, comedor):
    for metodo in ("post", "put", "delete"):
        assert (
            getattr(lector, metodo)(f"{ROOT}{comedor.pk}/").status_code == 405
        ), metodo
    assert Comedor.objects.filter(pk=comedor.pk).exists()


@pytest.mark.parametrize("codename", ["view_admision", "view_informacionrelevante"])
def test_any_of_the_three_native_permissions_is_enough(codename, comedor):
    assert (
        _client(f"lector_{codename}", codename).get(f"{ROOT}{comedor.pk}/").status_code
        == 200
    )


def test_anonymous_and_without_permission(client, comedor):
    respuesta = client.get(f"{ROOT}{comedor.pk}/")
    assert respuesta.status_code == 401
    assert respuesta.json() == {"detail": web_gate.DETAIL_UNAUTHENTICATED}
    client.force_login(
        _ready(get_user_model().objects.create_user("sin_permiso_ficha", password="x"))
    )
    assert client.get(f"{ROOT}{comedor.pk}/").status_code == 403


def test_pending_web_requirement_is_reported_and_a_forged_header_is_ignored(comedor):
    usuario = get_user_model().objects.create_superuser("pendiente_ficha", password="x")
    usuario.profile.acceso_web = True
    usuario.profile.must_change_password = True
    usuario.profile.save()
    client = Client()
    client.force_login(usuario)
    url = f"{ROOT}{comedor.pk}/"
    falso = web_gate.sign(
        audience="comedores",
        user_pk=usuario.pk,
        session_key=client.cookies["sessionid"].value,
        method="GET",
        target=url,
    )

    respuesta = client.get(url, HTTP_X_SISOC_WEB_GATE=falso, RAW_URI=url)

    assert respuesta.status_code == 403
    assert respuesta.json()["state"] == "password_change_required"


def _acordeon(client, comedor):
    return client.get(f"{ROOT}{comedor.pk}/").json()["acordeon"]


def test_ubicacion_panel_shows_the_native_values_and_the_map_branches(lector):
    provincia = Provincia.objects.create(nombre="Chaco")
    municipio = Municipio.objects.create(nombre="Resistencia", provincia=provincia)
    localidad = Localidad.objects.create(nombre="Centro", municipio=municipio)
    comedor = Comedor.objects.create(
        nombre="Comedor Norte",
        calle="Mitre",
        numero=120,
        piso="2",
        departamento="B",
        categoria_espacio_comunitario="otra",
        categoria_espacio_comunitario_otra="Club barrial",
        provincia=provincia,
        municipio=municipio,
        localidad=localidad,
    )

    panel = _acordeon(lector, comedor)["ubicacion"]

    datos = {d["label"]: d["value"] for d in panel["datos"]}
    assert datos["Nombre del espacio comunitario"] == "Comedor Norte"
    assert datos["Categorización"].endswith("— Club barrial")
    assert datos["Calle"] == "Mitre"
    assert datos["Numeración"] == "120"
    assert datos["Manzana"] == "-"
    assert datos["Piso y/o departamento"] == "2 - B"
    assert datos["Localidad"] == "Centro"
    assert datos["Provincia"] == "Chaco"
    assert panel["datos"][0]["icon"] == "bi bi-house-door-fill"
    # Without coordinates, the address of the template builds the map query.
    assert panel["mapa"] == {
        "tipo": "iframe",
        "src": "https://maps.google.com/maps?q=Mitre+120,+Centro,+Resistencia,+Chaco&output=embed",
    }
    comedor.latitud, comedor.longitud = -27.45, -58.98
    comedor.save()
    assert _acordeon(lector, comedor)["ubicacion"]["mapa"]["src"].startswith(
        "https://maps.google.com/maps?q=-27.45,-58.98"
    )
    vacio = Comedor.objects.create(nombre="Sin datos")
    assert _acordeon(lector, vacio)["ubicacion"]["mapa"] == {
        "tipo": "vacio",
        "src": None,
    }


def test_responsables_panel_with_and_without_organizacion(lector):
    sin = Comedor.objects.create(nombre="Sin organizacion")
    assert _acordeon(lector, sin)["responsables"]["hay_organizacion"] is False
    assert _acordeon(lector, sin)["responsables"]["foto"]["default"] is True
    organizacion = Organizacion.objects.create(nombre="Org Uno", cuit=20123456786)
    con = Comedor.objects.create(nombre="Con organizacion", organizacion=organizacion)

    panel = _acordeon(lector, con)["responsables"]

    assert panel["hay_organizacion"] is True
    assert panel["items"][0] == {
        "icon": "bi bi-building",
        "label": "Nombre",
        "value": "Org Uno",
    }
    assert [i["label"] for i in panel["items"]][:2] == ["Nombre", "CUIT"]


def test_prestaciones_panel_without_informe_and_the_tradicional_row(lector, comedor):
    panel = _acordeon(lector, comedor)["prestaciones"]

    assert panel["dias"] == [
        "Lunes",
        "Martes",
        "Miercoles",
        "Jueves",
        "Viernes",
        "Sabado",
        "Domingo",
    ]
    assert [f["comida"] for f in panel["filas"]] == [
        "Desayuno",
        "Almuerzo",
        "Merienda",
        "Cena",
    ]
    assert panel["filas"][0]["valores"] == ["-"] * 7
    assert panel["prestaciones_mensuales"] == "-"
    assert panel["monto_mensual"] == "-"
    assert panel["dias_por_semana"] == "-"


def test_territorial_panel_has_every_native_option_unmarked_without_relevamiento(
    lector, comedor
):
    panel = _acordeon(lector, comedor)["relevamientos"]

    assert panel["titulo"] == "Acompañamiento Territorial"
    assert panel["pnud"] is False
    assert [d["label"] for d in panel["donaciones"]] == [
        "Particulares",
        "Estado nacional",
        "Estado provincial",
        "Estado municipal",
        "Otros",
    ]
    assert not any(
        d["marcado"] for d in panel["donaciones"] + panel["servicio"] + panel["espacio"]
    )
    assert len(panel["espacio"]) == 6
    assert panel["actividades_anexo"] == []


def _tablero(client, comedor, **params):
    return client.get(f"{ROOT}{comedor.pk}/", params).json()["tablero"]


def test_timeline_follows_the_selected_admission(lector, comedor):
    antes = _tablero(lector, comedor)["timeline"]
    assert antes["admision"]["clase"] == "step active"
    assert antes["admision"]["completada"] is False
    assert antes["admision"]["fecha"] == "-"
    assert antes["conector"] == "connector"
    assert antes["ejecucion"] == {"clase": "step", "circulo": "2"}
    assert antes["rendicion"] == {"circulo": "3"}

    admision = Admision.objects.create(
        comedor=comedor, activa=True, enviado_acompaniamiento=True
    )
    despues = _tablero(lector, comedor)["timeline"]

    assert despues["admision"]["clase"] == "step completed"
    assert despues["admision"]["completada"] is True
    assert despues["admision"]["fecha"] == admision.creado.strftime("%d/%m/%Y")
    assert despues["conector"] == "connector completed"
    assert despues["ejecucion"]["clase"] == "step active"


def test_summary_boxes_and_chart_use_the_native_defaults(lector, comedor):
    tablero = _tablero(lector, comedor)

    assert [c["label"] for c in tablero["resumen"]] == [
        "Prestaciones mensuales",
        "Actividades Comunitarias",
        "Acompañamiento Territorial",
        "Numero de Convenio",
    ]
    assert [c["icon"] for c in tablero["resumen"]][0] == "bi bi-cup-hot"
    assert tablero["resumen"][3]["valor"] == "0"
    assert [g["label"] for g in tablero["grafico"]] == [
        "Sin dato",
        "0-13 años",
        "14-17 años",
        "18-49 años",
        "50-65 años",
        "+66 años",
    ]
    assert all(isinstance(g["valor"], float) for g in tablero["grafico"])
    Admision.objects.create(comedor=comedor, activa=True)
    assert _tablero(lector, comedor)["resumen"][3]["valor"] in ("- / 1", "1° / 1")


def test_admission_card_shows_the_native_texts_and_the_link(lector, comedor):
    sin = _tablero(lector, comedor)["detalles"]
    assert sin["tipo"] == "admision"
    assert sin["titulo"] == "Detalles de Admisión"
    assert sin["filas"][0] == {
        "label": "Fecha",
        "value": "Sin información",
        "mayusculas": False,
    }
    assert sin["accion"] == {"label": "Ver detalles", "url": None}

    admision = Admision.objects.create(
        comedor=comedor, activa=True, num_expediente="EX-1"
    )
    con = _tablero(lector, comedor)["detalles"]

    valores = {f["label"]: f["value"] for f in con["filas"]}
    assert valores["Fecha"] == admision.creado.strftime("%d/%m/%Y")
    assert valores["Número de expediente"] == "EX-1"
    # As the page: a missing dupla resolves to an empty string, not None.
    assert valores["Dupla"] == ""
    assert (
        con["accion"]["url"]
        == f"/comedores/{comedor.pk}/admision/{admision.pk}/detalle/"
    )


def test_card_holder_card_only_for_who_can_manage_it(lector, comedor):
    assert _tablero(lector, comedor)["responsable_tarjeta"] is None


def test_transactions_card_follows_the_dw_summary_and_the_permission(
    lector, comedor, monkeypatch
):
    from decimal import Decimal

    from comedores.services.dw_transacciones_service.impl import (
        DWTransaccion,
        DWTransaccionesService,
    )

    sin_dato = _tablero(lector, comedor)["transacciones"]
    assert sin_dato == {
        "periodo": "Sin información",
        "movimientos": "Sin información",
        "transferido": "Sin información",
        "gastado": "Sin información",
        "saldo": "Sin información",
        "detalle": f"/comedores/{comedor.pk}/transacciones",
    }
    monkeypatch.setattr(
        DWTransaccionesService,
        "obtener_resumen_ultimo_periodo",
        staticmethod(
            lambda _id: DWTransaccion(
                comedor_id_sisoc=_id,
                periodo="202609",
                cantidad_debitos=14,
                credito_total=Decimal("1500"),
                debito_total=Decimal("12000"),
                cereo=Decimal("0"),
            )
        ),
    )

    con = _tablero(lector, comedor)["transacciones"]

    assert con["periodo"] == "2026-09"
    assert con["movimientos"] == "14"
    assert con["transferido"] == "$12.000"
    assert con["gastado"] == "$1.500"
    assert con["saldo"] == "$0"
    sin_permiso = _client("solo_admision", "view_admision")
    assert _tablero(sin_permiso, comedor)["transacciones"] is None


def test_execution_month_card_only_for_pnud_secos_and_with_the_expediente(
    lector, comedor
):
    from expedientespagos.models import ExpedientePago

    assert _tablero(lector, comedor)["mes_ejecucion"] is None
    # The native view keys the card on the PNUD - SECOS program id.
    comedor.programa = Programas.objects.create(pk=2, nombre="PNUD - SECOS")
    comedor.save()

    sin = _tablero(lector, comedor)["mes_ejecucion"]
    assert sin["expediente"] is None
    assert sin["ver_mas"] == f"/expedientespagos/expedientespagos/{comedor.pk}/"

    ExpedientePago.objects.create(
        comedor=comedor,
        expediente_convenio="EX-C-1",
        mes_pago="Octubre",
        ano="2026",
        prestaciones_mensuales_desayuno=10,
        prestaciones_mensuales_almuerzo=5,
        prestaciones_mensuales_merienda=0,
        prestaciones_mensuales_cena=0,
        monto_mensual_desayuno=0,
        monto_mensual_almuerzo=0,
        monto_mensual_merienda=0,
        monto_mensual_cena=0,
        total=1234.5,
    )
    con = _tablero(lector, comedor)["mes_ejecucion"]["expediente"]

    assert con["convenio"] == "EX-C-1"
    assert con["pago"] == "Sin información"
    assert con["prestaciones"] == "15"
    assert con["monto"] == "$1.235"
    assert con["mes_pago"] == "Octubre"
    assert con["ano"] == "2026"
    assert con["mes_ejecucion"] == "Sin información"
