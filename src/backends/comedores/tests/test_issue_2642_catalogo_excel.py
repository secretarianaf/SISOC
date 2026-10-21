"""Catálogo y dependencia Región/Subzona del Excel recibido para #2642."""

from importlib import import_module
from types import SimpleNamespace

import pytest
from django.apps import apps
from django.db import connection

from core.models import Provincia
from gestion_organizaciones.forms import OrganizacionForm
from organizaciones.models import (
    Organizacion,
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


@pytest.mark.django_db
def test_provisorios_se_desactivan_sin_perder_asignaciones():
    region, _ = RegionAbordajeComunitario.objects.update_or_create(
        nombre="Región 1", defaults={"activo": True}
    )
    zona, _ = SubzonaAbordajeComunitario.objects.update_or_create(
        nombre="Zona 1", defaults={"activo": True}
    )
    provincia = Provincia.objects.create(nombre="Provincia de prueba")
    organizacion = Organizacion.objects.create(
        nombre="Legado",
        provincia=provincia,
        sin_vencimiento=True,
        region_abordaje=region,
        subzona_abordaje=zona,
    )
    _cargar()
    organizacion.refresh_from_db()
    assert organizacion.region_abordaje_id == region.pk
    assert organizacion.subzona_abordaje_id == zona.pk
    assert not organizacion.region_abordaje.activo
    assert not organizacion.subzona_abordaje.activo
    form = OrganizacionForm(
        data={
            "nombre": "Legado",
            "provincia": str(provincia.pk),
            "sin_vencimiento": "on",
            "region_abordaje": str(region.pk),
            "subzona_abordaje": str(zona.pk),
        },
        instance=organizacion,
    )
    assert form.is_valid(), form.errors
    assert (
        not OrganizacionForm()
        .fields["region_abordaje"]
        .queryset.filter(pk=region.pk)
        .exists()
    )


@pytest.mark.django_db
def test_formulario_limita_subzonas_a_region_y_rechaza_combinacion_ajena():
    _cargar()
    region = RegionAbordajeComunitario.objects.get(nombre="AGBA")
    propia = SubzonaAbordajeComunitario.objects.get(nombre="NOROESTE")
    ajena = SubzonaAbordajeComunitario.objects.get(nombre="CORDOBA")
    provincia = Provincia.objects.create(nombre="Provincia de prueba")
    datos = {
        "nombre": "Organización",
        "provincia": str(provincia.pk),
        "sin_vencimiento": "on",
        "region_abordaje": str(region.pk),
        "subzona_abordaje": str(propia.pk),
    }
    form = OrganizacionForm(data=datos)
    assert form.is_valid(), form.errors
    assert set(
        form.fields["subzona_abordaje"].queryset.values_list("region_id", flat=True)
    ) == {region.pk}
    assert len(form.subzonas_abordaje) == 28
    datos["subzona_abordaje"] = str(ajena.pk)
    assert "subzona_abordaje" in OrganizacionForm(data=datos).errors
    datos["region_abordaje"] = ""
    assert "subzona_abordaje" in OrganizacionForm(data=datos).errors
    datos["subzona_abordaje"] = ""
    assert OrganizacionForm(data=datos).is_valid()
