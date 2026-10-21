"""Opciones provisorias acordadas para Región y Subzona (#2642)."""
# pylint: disable=invalid-name

from django.db import migrations


def cargar_catalogos_provisorios(apps, schema_editor):
    for modelo, nombres in (
        ("RegionAbordajeComunitario", ("Región 1", "Región 2")),
        ("SubzonaAbordajeComunitario", ("Zona 1", "Zona 2")),
    ):
        catalogo = apps.get_model("organizaciones", modelo)
        for nombre in nombres:
            catalogo.objects.using(schema_editor.connection.alias).get_or_create(
                nombre=nombre
            )


class Migration(migrations.Migration):
    dependencies = [
        ("organizaciones", "0024_issue_2642_abordaje_comunitario"),
    ]

    operations = [
        # No borrar opciones al revertir: pueden estar asignadas o renombradas.
        migrations.RunPython(cargar_catalogos_provisorios, migrations.RunPython.noop),
    ]
