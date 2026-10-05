"""Firmante pasa de ``organizaciones`` (kernel) a ``gestion_organizaciones`` (core).

Solo estado: la tabla sigue siendo ``organizaciones_firmante``. El content type
se reasigna conservando su id (permisos y auditoría). Firmante se relaciona con
``comedores.Programas``, por eso no puede quedar en el kernel.
"""

import core.soft_delete.base
import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def _mover_content_type(apps, origen, destino):
    content_type = apps.get_model("contenttypes", "ContentType")
    if content_type.objects.filter(app_label=destino, model="firmante").exists():
        if content_type.objects.filter(app_label=origen, model="firmante").exists():
            raise RuntimeError(
                f"Existen content types {origen}.firmante y {destino}.firmante: "
                "resolver a mano antes de migrar para no perder permisos."
            )
        return
    content_type.objects.filter(app_label=origen, model="firmante").update(
        app_label=destino
    )


def content_type_a_gestion(apps, schema_editor):
    del schema_editor
    _mover_content_type(apps, "organizaciones", "gestion_organizaciones")


def content_type_a_organizaciones(apps, schema_editor):
    del schema_editor
    _mover_content_type(apps, "gestion_organizaciones", "organizaciones")


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("comedores", "0063_merge_subido_por_responsable_tarjeta"),
        ("contenttypes", "0002_remove_content_type_name"),
        ("organizaciones", "0022_issue_2445_territoriales_abordaje_comunitario"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="Firmante",
                    fields=[
                        (
                            "id",
                            models.BigAutoField(
                                auto_created=True,
                                primary_key=True,
                                serialize=False,
                                verbose_name="ID",
                            ),
                        ),
                        (
                            "deleted_at",
                            models.DateTimeField(blank=True, db_index=True, null=True),
                        ),
                        ("nombre", models.CharField(max_length=255)),
                        (
                            "cuit",
                            models.BigIntegerField(
                                blank=True,
                                null=True,
                                validators=[
                                    django.core.validators.MinValueValidator(0),
                                    django.core.validators.MaxValueValidator(
                                        99999999999
                                    ),
                                ],
                            ),
                        ),
                        (
                            "deleted_by",
                            models.ForeignKey(
                                blank=True,
                                null=True,
                                on_delete=django.db.models.deletion.SET_NULL,
                                related_name="+",
                                to=settings.AUTH_USER_MODEL,
                            ),
                        ),
                        (
                            "organizacion",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="firmantes",
                                to="organizaciones.organizacion",
                            ),
                        ),
                        (
                            "programa",
                            models.ForeignKey(
                                blank=True,
                                null=True,
                                on_delete=django.db.models.deletion.PROTECT,
                                related_name="firmantes_organizacion",
                                to="comedores.programas",
                            ),
                        ),
                        (
                            "rol",
                            models.ForeignKey(
                                blank=True,
                                null=True,
                                on_delete=django.db.models.deletion.PROTECT,
                                related_name="firmantes",
                                to="organizaciones.rolfirmante",
                            ),
                        ),
                    ],
                    options={
                        "db_table": "organizaciones_firmante",
                    },
                    managers=[
                        ("objects", core.soft_delete.base.SoftDeleteManager()),
                        (
                            "all_objects",
                            core.soft_delete.base.SoftDeleteManager(
                                include_deleted=True
                            ),
                        ),
                    ],
                ),
            ],
            database_operations=[],
        ),
        migrations.RunPython(content_type_a_gestion, content_type_a_organizaciones),
    ]
