"""Catálogo de REGIONES_Y_ZONAS.xlsx, Hoja2, recibido el 21/10/2026."""

# pylint: disable=invalid-name

import django.db.models.deletion
from django.db import migrations, models


REGIONES_SUBZONAS = {
    "AGBA": ("CABA NORTE y OTROS", "NOROESTE", "SUR ESTE", "OESTE (LM)"),
    "CENTRO": ("CONCORDIA", "CORDOBA", "PARANA", "ROSARIO", "SANTA FE"),
    "CUYO PATAGONIA BAI": (
        "BARILOCHE",
        "LA PLATA",
        "MAR DEL PLATA",
        "MENDOZA",
        "SAN JUAN",
        "NEUQUEN",
        "RIO NEGRO",
        "LA PAMPA",
        "SAN LUIS",
    ),
    "NEA": ("CORRIENTES", "FORMOSA", "MISIONES", "CHACO"),
    "NOA": (
        "CATAMARCA",
        "JUJUY",
        "SALTA",
        "SANTIAGO DEL ESTERO",
        "TUCUMAN",
        "LA RIOJA",
    ),
}


def cargar_catalogo_excel(apps, schema_editor):
    alias = schema_editor.connection.alias
    regiones = apps.get_model(
        "organizaciones", "RegionAbordajeComunitario"
    ).objects.using(alias)
    subzonas = apps.get_model(
        "organizaciones", "SubzonaAbordajeComunitario"
    ).objects.using(alias)
    for nombre, zonas in REGIONES_SUBZONAS.items():
        region, _ = regiones.update_or_create(nombre=nombre, defaults={"activo": True})
        for zona in zonas:
            subzonas.update_or_create(
                nombre=zona, defaults={"region_id": region.pk, "activo": True}
            )


class Migration(migrations.Migration):
    dependencies = [("organizaciones", "0024_issue_2642_abordaje_comunitario")]

    operations = [
        migrations.AddField(
            model_name="subzonaabordajecomunitario",
            name="region",
            field=models.ForeignKey(
                to="organizaciones.regionabordajecomunitario",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="subzonas",
                null=True,
                blank=True,
                verbose_name="Región",
            ),
        ),
        migrations.RunPython(cargar_catalogo_excel, migrations.RunPython.noop),
    ]
