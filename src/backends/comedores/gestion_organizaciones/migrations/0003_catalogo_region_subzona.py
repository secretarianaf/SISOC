"""Catálogo de Región y Aglomerado/Subzona de Abordaje Comunitario (#2745).

Listado confirmado por el área usuaria el 20/10/2026 (Anexo A del plan
``docs/plans/2026-T4/2026-10-20-2745-legajo-organizacion-por-programa.md``):
5 regiones y 28 subzonas.

Idempotente: solo agrega lo que falta y no modifica filas existentes. La
reversa no borra nada, para no perder catálogos ya usados o editados desde el
admin (plan, sección 2.1).
"""

from django.db import migrations

REGIONES = {
    "AGBA": ["CABA NORTE y OTROS", "NOROESTE", "SUR ESTE", "OESTE (LM)"],
    "CENTRO": ["CONCORDIA", "CORDOBA", "PARANA", "ROSARIO", "SANTA FE"],
    "CUYO PATAGONIA BAI": [
        "BARILOCHE",
        "LA PLATA",
        "MAR DEL PLATA",
        "MENDOZA",
        "SAN JUAN",
        "NEUQUEN",
        "RIO NEGRO",
        "LA PAMPA",
        "SAN LUIS",
    ],
    "NEA": ["CORRIENTES", "FORMOSA", "MISIONES", "CHACO"],
    "NOA": [
        "CATAMARCA",
        "JUJUY",
        "SALTA",
        "SANTIAGO DEL ESTERO",
        "TUCUMAN",
        "LA RIOJA",
    ],
}


def cargar_catalogo(apps, schema_editor):
    del schema_editor
    region_model = apps.get_model("gestion_organizaciones", "RegionAbordaje")
    subzona_model = apps.get_model("gestion_organizaciones", "SubzonaAbordaje")
    for nombre_region, subzonas in REGIONES.items():
        region, _ = region_model.objects.get_or_create(nombre=nombre_region)
        for nombre_subzona in subzonas:
            subzona_model.objects.get_or_create(region=region, nombre=nombre_subzona)


class Migration(migrations.Migration):

    dependencies = [
        ("gestion_organizaciones", "0002_datos_por_programa"),
    ]

    operations = [
        migrations.RunPython(cargar_catalogo, migrations.RunPython.noop),
    ]
