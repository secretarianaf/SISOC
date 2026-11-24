"""Colaboradores, interacciones and capacitaciones of the comedor ficha web API (CO07.01).

The blocks are projections of the native context; «Eliminar» a colaborador points at
the colaboradores API (CO03.01), which runs the native soft delete. These tests check
the values against the native ones, the actions each permission allows and that the
URL the ficha publishes does the baja the ficha then shows.
"""

from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client

from ciudadanos.models import Ciudadano
from comedores.models import (
    ActividadColaboradorEspacio,
    CapacitacionComedorCertificado,
    ColaboradorEspacio,
    Comedor,
)
from core.models import Sexo
from intervenciones.models.intervenciones import Intervencion

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
    client.usuario = usuario
    return client


@pytest.fixture(name="lector")
def lector_fixture():
    return _client("lector_reg", "view_comedor")


@pytest.fixture(name="comedor")
def comedor_fixture():
    return Comedor.objects.create(nombre="Comedor Norte")


def _colaborador(comedor, documento, **campos):
    sexo, _ = Sexo.objects.get_or_create(sexo="Femenino")
    ciudadano = Ciudadano.objects.create(
        apellido="Gomez",
        nombre="Ana",
        fecha_nacimiento="1992-05-03",
        tipo_documento=Ciudadano.DOCUMENTO_DNI,
        documento=documento,
        sexo=sexo,
        cuil_cuit=f"27{documento}6",
    )
    datos = {"fecha_alta": date(2026, 3, 26), "genero": "M"}
    datos.update(campos)
    return ColaboradorEspacio.objects.create(
        comedor=comedor, ciudadano=ciudadano, **datos
    )


def _ficha(client, comedor):
    return client.get(f"{ROOT}{comedor.pk}/").json()


def test_colaboradores_card_without_records(lector, comedor):
    card = _ficha(lector, comedor)["colaboradores"]

    assert card["items"] == []
    assert card["resultados"] == "Se encontraron 0 resultados."
    assert card["agregar"] is None


def test_colaboradores_rows_project_the_native_cells(lector, comedor):
    actividad = ActividadColaboradorEspacio.objects.create(
        alias="COM", nombre="Compras"
    )
    otra = ActividadColaboradorEspacio.objects.create(alias="COC", nombre="Cocina")
    activo = _colaborador(
        comedor,
        28999111,
        codigo_telefono="11",
        numero_telefono="5555",
    )
    activo.actividades.set([actividad, otra])
    baja = _colaborador(comedor, 28999222, fecha_baja=date(2026, 4, 1), genero="ND")

    card = _ficha(lector, comedor)["colaboradores"]

    filas = {f["id"]: f for f in card["items"]}
    fila = filas[activo.pk]
    assert fila["nombre"] == "Gomez, Ana"
    assert fila["dni"] == "28999111"
    assert fila["sexo"] == "Femenino"
    assert fila["genero"] == "Mujer"
    assert fila["telefono"] == "11 5555"
    assert fila["alta"] == "26/03/2026"
    assert fila["baja"] == "-"
    assert fila["actividades"] == "Compras , Cocina"
    assert filas[baja.pk]["baja"] == "01/04/2026"
    assert filas[baja.pk]["telefono"] == "-"
    assert filas[baja.pk]["actividades"] == "-"
    assert card["resultados"] == "Se encontraron 2 resultados."


def test_colaboradores_actions_follow_the_permissions_and_the_baja(comedor):
    activo = _colaborador(comedor, 28999111)
    baja = _colaborador(comedor, 28999222, fecha_baja=date(2026, 4, 1))
    solo_ver = _client("solo_ver_reg", "view_comedor")
    gestor = _client(
        "gestor_reg",
        "view_comedor",
        "add_colaboradorespacio",
        "change_colaboradorespacio",
        "delete_colaboradorespacio",
    )

    sin = _ficha(solo_ver, comedor)["colaboradores"]
    assert sin["agregar"] is None
    assert all(f["editar"] is None and f["eliminar"] is None for f in sin["items"])

    con = _ficha(gestor, comedor)["colaboradores"]
    assert con["agregar"] == f"/comedores/{comedor.pk}/colaboradores/crear/"
    filas = {f["id"]: f for f in con["items"]}
    assert filas[activo.pk]["editar"] == (
        f"/comedores/{comedor.pk}/colaboradores/{activo.pk}/editar/"
    )
    assert filas[activo.pk]["eliminar"] == {
        "url": f"/api/web/comedores/colaboradores/comedor/{comedor.pk}/{activo.pk}/eliminar/",
        "deshabilitado": False,
    }
    # An inactive colaborador cannot be edited and its «Eliminar» is disabled.
    assert filas[baja.pk]["editar"] is None
    assert filas[baja.pk]["eliminar"]["deshabilitado"] is True


def test_the_baja_url_of_the_ficha_is_the_colaboradores_api_and_persists(comedor):
    colaborador = _colaborador(comedor, 28999111)
    eliminador = _client("eliminador_reg", "view_comedor", "delete_colaboradorespacio")
    fila = _ficha(eliminador, comedor)["colaboradores"]["items"][0]
    url = fila["eliminar"]["url"]
    assert (
        url
        == f"/api/web/comedores/colaboradores/comedor/{comedor.pk}/{colaborador.pk}/eliminar/"
    )

    respuesta = eliminador.post(url)

    assert respuesta.status_code == 200
    assert respuesta.json() == {"ok": True, "redirect": f"/comedores/{comedor.pk}"}
    colaborador.refresh_from_db()
    assert colaborador.fecha_baja is not None
    # The ficha the redirect lands on shows the native message and the disabled button.
    ficha = _ficha(eliminador, comedor)
    assert ficha["messages"] == [
        {"message": "Colaborador dado de baja correctamente.", "level": "success"}
    ]
    assert ficha["colaboradores"]["items"][0]["eliminar"]["deshabilitado"] is True
    assert ficha["colaboradores"]["items"][0]["editar"] is None


def test_interacciones_chart_counts_the_interventions_by_month(lector, comedor):
    assert _ficha(lector, comedor)["interacciones"] == {"labels": [], "values": []}
    for dia in (date(2026, 3, 1), date(2026, 3, 20), date(2026, 5, 2)):
        Intervencion.objects.create(comedor=comedor, fecha=dia)

    grafico = _ficha(lector, comedor)["interacciones"]

    assert grafico == {"labels": ["Mar 2026", "May 2026"], "values": [2, 1]}


def test_capacitaciones_rows_follow_the_native_certificates(lector, comedor):
    capacitaciones = _ficha(lector, comedor)["capacitaciones"]["items"]

    # The native view creates one record per capacitación the first time.
    assert len(capacitaciones) == len(
        CapacitacionComedorCertificado.CAPACITACION_CHOICES
    )
    primero = capacitaciones[0]
    assert primero["capacitacion"] == (
        "Creación de Usuario en Plataforma Alimentar Comunidad"
    )
    assert primero["estado"] == "sin_presentar"
    assert primero["archivo"] is None
    assert primero["observacion"] == "-"
    assert primero["revisar"] == (
        f"{ROOT}{comedor.pk}/capacitaciones/{primero['id']}/estado/"
    )
    CapacitacionComedorCertificado.objects.filter(pk=primero["id"]).update(
        estado="rechazado", observacion="Ilegible"
    )
    nuevo = _ficha(lector, comedor)["capacitaciones"]["items"][0]
    assert (nuevo["estado"], nuevo["observacion"]) == ("rechazado", "Ilegible")
