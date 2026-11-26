"""Catálogo y dependencia Región/Subzona del Excel recibido para #2642."""

import json
from importlib import import_module
from types import SimpleNamespace

import pytest
from django.apps import apps
from django.db import connection

from core.models import Provincia
from gestion_organizaciones.forms import OrganizacionForm
from organizaciones.models import (
    Organizacion,
    ProyectoOrganizacion,
    RegionAbordajeComunitario,
    SubzonaAbordajeComunitario,
)


def _cargar():
    migracion = import_module(
        "organizaciones.migrations.0026_issue_2642_regiones_zonas_excel"
    )
    migracion.cargar_catalogo_excel(apps, SimpleNamespace(connection=connection))


@pytest.mark.django_db
def test_excel_carga_cinco_regiones_y_28_subzonas_sin_duplicar_san_juan():
    region, _ = RegionAbordajeComunitario.objects.update_or_create(
        nombre="AGBA", defaults={"activo": False}
    )
    zona, _ = SubzonaAbordajeComunitario.objects.update_or_create(
        nombre="NOROESTE", defaults={"region": None}
    )
    _cargar()
    _cargar()
    assert set(
        RegionAbordajeComunitario.objects.filter(activo=True).values_list(
            "nombre", flat=True
        )
    ) == {
        "AGBA",
        "CENTRO",
        "CUYO PATAGONIA BAI",
        "NEA",
        "NOA",
    }
    assert SubzonaAbordajeComunitario.objects.filter(activo=True).count() == 28
    assert SubzonaAbordajeComunitario.objects.filter(nombre="SAN JUAN").count() == 1
    assert (
        SubzonaAbordajeComunitario.objects.get(nombre="SAN JUAN").region.nombre
        == "CUYO PATAGONIA BAI"
    )
    zona.refresh_from_db()
    region.refresh_from_db()
    assert zona.region_id == region.pk
    assert region.activo
    assert set(region.subzonas.values_list("nombre", flat=True)) == {
        "CABA NORTE y OTROS",
        "NOROESTE",
        "SUR ESTE",
        "OESTE (LM)",
    }


def _datos_con_proyecto(provincia, region="", subzona=""):
    """Organización sin programas con un proyecto (la línea no se exige)."""
    return {
        "nombre": "Organización",
        "provincia": str(provincia.pk),
        "sin_vencimiento": "on",
        "proyectos_lineas": json.dumps(
            [{"codigo": "P-1", "linea": None, "region": region, "subzona": subzona}]
        ),
    }


@pytest.mark.django_db
def test_opciones_inactivas_se_conservan_en_asignaciones_existentes():
    region = RegionAbordajeComunitario.objects.create(nombre="Región dada de baja")
    zona = SubzonaAbordajeComunitario.objects.create(nombre="Zona dada de baja")
    provincia = Provincia.objects.create(nombre="Provincia de prueba")
    organizacion = Organizacion.objects.create(
        nombre="Legado", provincia=provincia, sin_vencimiento=True
    )
    ProyectoOrganizacion.objects.create(
        organizacion=organizacion,
        codigo="P-1",
        region_abordaje=region,
        subzona_abordaje=zona,
    )
    RegionAbordajeComunitario.objects.filter(pk=region.pk).update(activo=False)
    SubzonaAbordajeComunitario.objects.filter(pk=zona.pk).update(activo=False)
    _cargar()
    form = OrganizacionForm(
        data=_datos_con_proyecto(provincia, region.pk, zona.pk),
        instance=organizacion,
    )
    assert form.is_valid(), form.errors
    # Una organización nueva no ofrece la región dada de baja.
    nuevas = {fila["id"] for fila in OrganizacionForm().regiones_abordaje}
    assert region.pk not in nuevas
    assert not OrganizacionForm(
        data=_datos_con_proyecto(provincia, region.pk)
    ).is_valid()


@pytest.mark.django_db
def test_formulario_limita_subzonas_a_region_y_rechaza_combinacion_ajena():
    _cargar()
    region = RegionAbordajeComunitario.objects.get(nombre="AGBA")
    propia = SubzonaAbordajeComunitario.objects.get(nombre="NOROESTE")
    ajena = SubzonaAbordajeComunitario.objects.get(nombre="CORDOBA")
    provincia = Provincia.objects.create(nombre="Provincia de prueba")

    form = OrganizacionForm(data=_datos_con_proyecto(provincia, region.pk, propia.pk))
    assert form.is_valid(), form.errors
    assert len(form.subzonas_abordaje) == 28
    assert not OrganizacionForm(
        data=_datos_con_proyecto(provincia, region.pk, ajena.pk)
    ).is_valid()
    assert not OrganizacionForm(
        data=_datos_con_proyecto(provincia, "", propia.pk)
    ).is_valid()
    assert OrganizacionForm(data=_datos_con_proyecto(provincia, "", "")).is_valid()


def _migracion_0027():
    return import_module("organizaciones.migrations.0027_proyecto_region_subzona")


@pytest.mark.django_db
def test_migracion_agrega_amba_en_region_y_subzona_sin_duplicar():
    migracion = _migracion_0027()
    editor = SimpleNamespace(connection=connection)
    migracion.cargar_amba(apps, editor)
    migracion.cargar_amba(apps, editor)

    amba = RegionAbordajeComunitario.objects.get(nombre="AMBA")
    assert amba.activo
    assert list(amba.subzonas.values_list("nombre", flat=True)) == ["AMBA"]
    assert {fila["nombre"] for fila in OrganizacionForm().regiones_abordaje} >= {"AMBA"}


@pytest.mark.django_db
def test_migracion_copia_la_region_de_la_organizacion_sin_pisar_datos():
    _cargar()
    agba = RegionAbordajeComunitario.objects.get(nombre="AGBA")
    noroeste = SubzonaAbordajeComunitario.objects.get(nombre="NOROESTE")
    centro = RegionAbordajeComunitario.objects.get(nombre="CENTRO")
    cordoba = SubzonaAbordajeComunitario.objects.get(nombre="CORDOBA")
    provincia = Provincia.objects.create(nombre="Provincia de prueba")
    con_region = Organizacion.objects.create(
        nombre="Con región",
        provincia=provincia,
        sin_vencimiento=True,
        region_abordaje=agba,
        subzona_abordaje=noroeste,
    )
    sin_region = Organizacion.objects.create(
        nombre="Sin región", provincia=provincia, sin_vencimiento=True
    )
    vacio = ProyectoOrganizacion.objects.create(organizacion=con_region, codigo="A")
    quitado = ProyectoOrganizacion.objects.create(
        organizacion=con_region, codigo="B", activo=False
    )
    propio = ProyectoOrganizacion.objects.create(
        organizacion=con_region,
        codigo="C",
        region_abordaje=centro,
        subzona_abordaje=cordoba,
    )
    ajeno = ProyectoOrganizacion.objects.create(organizacion=sin_region, codigo="D")

    _migracion_0027().copiar_region_a_proyectos(
        apps, SimpleNamespace(connection=connection)
    )

    for proyecto in (vacio, quitado, propio, ajeno, con_region):
        proyecto.refresh_from_db()
    assert (vacio.region_abordaje, vacio.subzona_abordaje) == (agba, noroeste)
    assert (quitado.region_abordaje, quitado.subzona_abordaje) == (agba, noroeste)
    # No pisa lo que el proyecto ya tenía ni inventa datos.
    assert (propio.region_abordaje, propio.subzona_abordaje) == (centro, cordoba)
    assert (ajeno.region_abordaje, ajeno.subzona_abordaje) == (None, None)
    # El dato de la organización se conserva.
    assert (con_region.region_abordaje, con_region.subzona_abordaje) == (
        agba,
        noroeste,
    )
