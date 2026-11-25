"""Región y Subzona/Aglomerado por proyecto, y opción AMBA en ambos catálogos.

- ``ProyectoOrganizacion`` suma ``region_abordaje`` y ``subzona_abordaje``.
- Cada proyecto (activo o no) que todavía no tenga región ni subzona recibe las
  de su organización. No se pisa ningún dato y no se borra nada: los campos de
  ``Organizacion`` quedan como dato anterior de la organización.
- Se agrega la Región "AMBA" con la Subzona/Aglomerado "AMBA" dentro de ella.

La reversa no deshace la copia: al quitar los campos de proyecto se descartan
solos. AMBA queda en el catálogo (puede estar en uso).
"""

# pylint: disable=invalid-name

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

AMBA = "AMBA"


def cargar_amba(apps, schema_editor):
    alias = schema_editor.connection.alias
    regiones = apps.get_model(
        "organizaciones", "RegionAbordajeComunitario"
    ).objects.using(alias)
    subzonas = apps.get_model(
        "organizaciones", "SubzonaAbordajeComunitario"
    ).objects.using(alias)
    region, _ = regiones.get_or_create(nombre=AMBA, defaults={"activo": True})
    subzona, creada = subzonas.get_or_create(
        nombre=AMBA, defaults={"region_id": region.pk, "activo": True}
    )
    if not creada and subzona.region_id is None:
        subzona.region_id = region.pk
        subzona.save(update_fields=["region"])


def copiar_region_a_proyectos(apps, schema_editor):
    alias = schema_editor.connection.alias
    proyecto_model = apps.get_model("organizaciones", "ProyectoOrganizacion")
    proyectos = proyecto_model._base_manager.using(alias).filter(  # noqa: SLF001
        region_abordaje__isnull=True,
        subzona_abordaje__isnull=True,
    )
    pendientes = proyectos.exclude(
        organizacion__region_abordaje__isnull=True,
        organizacion__subzona_abordaje__isnull=True,
    ).values_list(
        "pk",
        "organizacion__region_abordaje_id",
        "organizacion__subzona_abordaje_id",
    )
    for proyecto_id, region_id, subzona_id in list(pendientes):
        proyecto_model._base_manager.using(alias).filter(  # noqa: SLF001
            pk=proyecto_id
        ).update(region_abordaje_id=region_id, subzona_abordaje_id=subzona_id)


class Migration(migrations.Migration):

    dependencies = [
        ("organizaciones", "0026_issue_2642_regiones_zonas_excel"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="subzonaabordajecomunitario",
            options={
                "ordering": ["nombre"],
                "verbose_name": "Subzona/Aglomerado de Abordaje Comunitario",
                "verbose_name_plural": "Subzonas/Aglomerados de Abordaje Comunitario",
            },
        ),
        migrations.AddField(
            model_name="proyectoorganizacion",
            name="region_abordaje",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="proyectos",
                to="organizaciones.regionabordajecomunitario",
                verbose_name="Región",
            ),
        ),
        migrations.AddField(
            model_name="proyectoorganizacion",
            name="subzona_abordaje",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="proyectos",
                to="organizaciones.subzonaabordajecomunitario",
                verbose_name="Subzona/Aglomerado",
            ),
        ),
        migrations.AlterField(
            model_name="organizacion",
            name="subzona_abordaje",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to="organizaciones.subzonaabordajecomunitario",
                verbose_name="Subzona/Aglomerado",
            ),
        ),
        migrations.AlterField(
            model_name="organizacion",
            name="territoriales_abordaje_comunitario",
            field=models.ManyToManyField(
                blank=True,
                related_name="organizaciones_territorial_abordaje",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Territorial/Supervisor Asignado Abordaje Comunitario",
            ),
        ),
        migrations.AlterField(
            model_name="proyectoorganizacion",
            name="territoriales",
            field=models.ManyToManyField(
                blank=True,
                related_name="proyectos_abordaje",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Territoriales/Supervisores asignados",
            ),
        ),
        migrations.RunPython(cargar_amba, migrations.RunPython.noop),
        migrations.RunPython(copiar_region_a_proyectos, migrations.RunPython.noop),
    ]
