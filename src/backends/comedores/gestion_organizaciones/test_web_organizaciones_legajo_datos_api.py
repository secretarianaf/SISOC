"""Legajo data blocks (región, proyectos, comedores) as sections of the legajo API (O05.01).

The section JSON must carry what the native partial renders, with the
native permission rules and no write path.
"""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.test import Client

from comedores.models import Comedor, Programas, Referente, TipoDeComedor
from duplas.models import Dupla
from gestion_organizaciones.models import LineaProyecto, ProgramaOrganizacion
from organizaciones.models import (
    Organizacion,
    ProyectoOrganizacion,
    RegionAbordajeComunitario,
    SubzonaAbordajeComunitario,
)

API = "/api/web/comedores/organizaciones/"
VIEW = "organizaciones.view_organizacion"

pytestmark = pytest.mark.django_db


def _usuario(nombre, *codes, **extra):
    usuario = get_user_model().objects.create_user(nombre, **extra)
    profile = usuario.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    for code in codes:
        app, codename = code.split(".")
        if app == "auth":
            permiso = Permission.objects.get_or_create(
                content_type=ContentType.objects.get_for_model(Group),
                codename=codename,
                defaults={"name": codename},
            )[0]
        else:
            permiso = Permission.objects.get(
                content_type__app_label=app, codename=codename
            )
        usuario.user_permissions.add(permiso)
    return usuario


@pytest.fixture(name="web")
def web_fixture():
    client = Client()
    client.force_login(_usuario("datos_web", VIEW))
    return client


def _secciones(client, organizacion, kind):
    data = client.get(f"{API}{organizacion.pk}/").json()
    return data, [s for s in data["sections"] if s["kind"] == kind]


def _marcador(data, seccion):
    return f'<div data-legajo-seccion="{data["sections"].index(seccion)}"></div>'


def test_region_section_carries_region_subzona_and_the_old_territoriales(web):
    region = RegionAbordajeComunitario.objects.create(nombre="Región Sintética")
    subzona = SubzonaAbordajeComunitario.objects.create(nombre="Subzona Uno")
    organizacion = Organizacion.objects.create(
        nombre="Con región", region_abordaje=region, subzona_abordaje=subzona
    )
    ana = _usuario("ana.t", first_name="Ana", last_name="Pérez")
    sin_nombre = _usuario("solo.usuario")
    organizacion.territoriales_abordaje_comunitario.add(ana, sin_nombre)

    data, (seccion,) = _secciones(web, organizacion, "region")

    assert seccion["has_data"] is True
    assert (seccion["region"], seccion["subzona"]) == (
        "Región Sintética",
        "Subzona Uno",
    )
    assert seccion["territorials"] == ["solo.usuario", "Pérez, Ana (ana.t)"]
    assert seccion["can_manage"] is True
    assert seccion["edit_url"] == (
        f"/organizaciones/editar/{organizacion.pk}#abordaje-card"
    )
    assert _marcador(data, seccion) in data["html"]
    assert "Datos de Región" not in data["html"]


def test_region_section_without_data_and_with_only_a_subzona(web):
    sin_datos = Organizacion.objects.create(nombre="Sin región")
    sin_datos.territoriales_abordaje_comunitario.add(_usuario("t.solo"))
    solo_subzona = Organizacion.objects.create(
        nombre="Solo subzona",
        subzona_abordaje=SubzonaAbordajeComunitario.objects.create(nombre="Sub"),
    )

    _, (vacia,) = _secciones(web, sin_datos, "region")
    _, (parcial,) = _secciones(web, solo_subzona, "region")

    assert vacia["has_data"] is False and vacia["territorials"] == ["t.solo"]
    assert parcial["has_data"] is True
    assert (parcial["region"], parcial["subzona"]) == ("-", "Sub")


def test_region_section_of_a_dupla_technician_has_no_edit_link():
    organizacion = Organizacion.objects.create(
        nombre="Dupla región",
        region_abordaje=RegionAbordajeComunitario.objects.create(nombre="R"),
    )
    tecnico = _usuario("tecnico_region", "auth.role_tecnico_comedor")
    dupla = Dupla.objects.create(
        nombre="D", estado="Activo", abogado=_usuario("abogado_region")
    )
    dupla.tecnico.add(tecnico)
    Comedor.objects.create(nombre="C", organizacion=organizacion, dupla=dupla)
    cliente = Client()
    cliente.force_login(tecnico)

    _, (seccion,) = _secciones(cliente, organizacion, "region")

    assert seccion["can_manage"] is False and seccion["edit_url"] is None


def test_native_page_still_renders_the_region_block(web):
    organizacion = Organizacion.objects.create(
        nombre="Nativa región",
        region_abordaje=RegionAbordajeComunitario.objects.create(nombre="Reg Nat"),
    )
    web.get(f"{API}{organizacion.pk}/")

    html = web.get(f"/organizaciones/detalle/{organizacion.pk}").content.decode()

    assert "Datos de Región" in html and "Reg Nat" in html
    assert "data-legajo-seccion" not in html


def test_proyectos_section_without_program_lists_only_active_projects(web):
    organizacion = Organizacion.objects.create(nombre="Con proyectos")
    activo = ProyectoOrganizacion.objects.create(
        organizacion=organizacion, codigo="B-2"
    )
    ProyectoOrganizacion.objects.create(organizacion=organizacion, codigo="A-1")
    ProyectoOrganizacion.objects.create(
        organizacion=organizacion, codigo="Z-9", activo=False
    )
    activo.territoriales.add(_usuario("pt.uno", first_name="Uno", last_name="Territ"))

    data, secciones = _secciones(web, organizacion, "proyectos")

    (seccion,) = secciones
    assert (seccion["title"], seccion["color"], seccion["total"]) == (
        "Proyectos",
        "otro",
        2,
    )
    assert [r["code"] for r in seccion["rows"]] == ["A-1", "B-2"]
    assert [r["territorials"] for r in seccion["rows"]] == [
        [],
        ["Territ, Uno (pt.uno)"],
    ]
    assert (
        seccion["edit_url"] == f"/organizaciones/editar/{organizacion.pk}#abordaje-card"
    )
    assert _marcador(data, seccion) in data["html"]
    assert "Cada proyecto pertenece a una sola línea" not in data["html"]


def test_proyectos_section_of_a_program_uses_its_title_color_and_lines(web):
    secos = Programas.objects.create(nombre="Abordaje comunitario - Línea Secos")
    organizacion = Organizacion.objects.create(nombre="Con Secos")
    ProgramaOrganizacion.objects.create(organizacion=organizacion, programa=secos)
    proyecto = ProyectoOrganizacion.objects.create(
        organizacion=organizacion, codigo="S-1"
    )
    LineaProyecto.objects.create(proyecto=proyecto, programa=secos)

    _, secciones = _secciones(web, organizacion, "proyectos")

    assert [s["title"] for s in secciones][0] == (
        "Proyectos · Abordaje comunitario - Línea Secos"
    )
    assert secciones[0]["color"] == "secos"
    assert [r["code"] for r in secciones[0]["rows"]] == ["S-1"]


def test_proyectos_section_empty_and_without_management_permission():
    organizacion = Organizacion.objects.create(nombre="Dupla proyectos")
    tecnico = _usuario("tecnico_proy", "auth.role_tecnico_comedor")
    dupla = Dupla.objects.create(
        nombre="D", estado="Activo", abogado=_usuario("abogado_proy")
    )
    dupla.tecnico.add(tecnico)
    Comedor.objects.create(nombre="C", organizacion=organizacion, dupla=dupla)
    cliente = Client()
    cliente.force_login(tecnico)
    ProyectoOrganizacion.objects.create(
        organizacion=organizacion, codigo="P-1", activo=False
    )
    organizacion.territoriales_abordaje_comunitario.add(_usuario("t.proy"))

    _, secciones = _secciones(cliente, organizacion, "proyectos")

    (seccion,) = secciones
    assert seccion["rows"] == [] and seccion["total"] == 0
    assert seccion["can_manage"] is False and seccion["edit_url"] is None


def test_comedores_section_carries_the_native_cells_and_defaults(web):
    organizacion = Organizacion.objects.create(nombre="Con espacios")
    referente = Referente.objects.create(nombre="Ana", apellido="Pérez", celular="1155")
    completo = Comedor.objects.create(
        nombre="Comedor Completo",
        organizacion=organizacion,
        tipocomedor=TipoDeComedor.objects.create(nombre="Comedor"),
        codigo_de_proyecto="COD-7",
        calle="Mitre",
        numero=120,
        referente=referente,
        estado_validacion="Validado",
        es_caritas=True,
    )
    pelado = Comedor.objects.create(
        nombre="Comedor Pelado",
        organizacion=organizacion,
        estado_validacion="No Validado",
    )
    pendiente = Comedor.objects.create(nombre="Pendiente", organizacion=organizacion)

    data, secciones = _secciones(web, organizacion, "comedores")

    (seccion,) = secciones
    assert (seccion["title"], seccion["color"], seccion["total"]) == (
        "Comedores",
        "sin",
        3,
    )
    assert seccion["show_code"] is True and seccion["show_program"] is True
    filas = {r["name"]: r for r in seccion["rows"]}
    lleno = filas["Comedor Completo"]
    assert lleno["id"] == completo.pk and lleno["url"] == f"/comedores/{completo.pk}"
    assert (lleno["caritas"], lleno["type"], lleno["code"]) == (
        True,
        "Comedor",
        "COD-7",
    )
    assert (lleno["address"], lleno["referent"], lleno["validation"]) == (
        "Mitre 120",
        "Ana Pérez",
        "ok",
    )
    vacio = filas["Comedor Pelado"]
    assert (vacio["type"], vacio["code"], vacio["program"], vacio["address"]) == (
        "-",
        None,
        "-",
        "- S/N",
    )
    assert (vacio["province"], vacio["municipality"], vacio["locality"]) == ("-",) * 3
    assert (vacio["referent"], vacio["validation"]) == (None, "no")
    assert filas["Pendiente"]["validation"] == "pending"
    assert pelado.pk and pendiente.pk
    assert _marcador(data, seccion) in data["html"]
    assert "Comedor Completo" not in data["html"]


def test_comedores_section_empty_has_no_rows(web):
    organizacion = Organizacion.objects.create(nombre="Sin espacios")

    data, secciones = _secciones(web, organizacion, "comedores")

    (seccion,) = secciones
    assert seccion["rows"] == [] and seccion["total"] == 0
    assert _marcador(data, seccion) in data["html"]
