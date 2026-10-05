"""Catálogos de intervenciones pasan de ``intervenciones`` a ``catalogo_intervenciones`` (kernel).

Solo estado: las tablas siguen siendo ``intervenciones_*``. Los content types
se reasignan conservando sus ids. Los usa Centro de Infancia, que corre en su
propio backend y no puede instalar ``intervenciones`` (FKs a comedores).
"""

import django.db.models.deletion
from django.db import migrations, models


MODELOS = ("tipointervencion", "subintervencion", "tipodestinatario", "tipocontacto")


def _mover_content_types(apps, origen, destino):
    content_type = apps.get_model("contenttypes", "ContentType")
    for modelo in MODELOS:
        if content_type.objects.filter(app_label=destino, model=modelo).exists():
            if content_type.objects.filter(app_label=origen, model=modelo).exists():
                raise RuntimeError(
                    f"Existen content types {origen}.{modelo} y {destino}.{modelo}: "
                    "resolver a mano antes de migrar para no perder permisos."
                )
            continue
        content_type.objects.filter(app_label=origen, model=modelo).update(
            app_label=destino
        )


def content_types_a_kernel(apps, schema_editor):
    del schema_editor
    _mover_content_types(apps, "intervenciones", "catalogo_intervenciones")


def content_types_a_intervenciones(apps, schema_editor):
    del schema_editor
    _mover_content_types(apps, "catalogo_intervenciones", "intervenciones")


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("intervenciones", "0007_intervencion_admision_backfill"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="TipoContacto",
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
                        ("nombre", models.CharField(max_length=255)),
                    ],
                    options={
                        "verbose_name": "Tipo de Contacto",
                        "verbose_name_plural": "Tipos de Contacto",
                        "db_table": "intervenciones_tipocontacto",
                        "ordering": ["id"],
                    },
                ),
                migrations.CreateModel(
                    name="TipoDestinatario",
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
                        ("nombre", models.CharField(max_length=255)),
                    ],
                    options={
                        "verbose_name": "Destinatario",
                        "verbose_name_plural": "Destinatarios",
                        "db_table": "intervenciones_tipodestinatario",
                        "ordering": ["id"],
                    },
                ),
                migrations.CreateModel(
                    name="TipoIntervencion",
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
                        ("nombre", models.CharField(max_length=255)),
                        (
                            "programa",
                            models.CharField(
                                blank=True,
                                db_index=True,
                                help_text="Texto libre para segmentar tipos por módulo (ej: comedores, cdi).",
                                max_length=100,
                                null=True,
                                verbose_name="Programa",
                            ),
                        ),
                    ],
                    options={
                        "verbose_name": "Tipo de Intervención",
                        "verbose_name_plural": "Tipos de Intervención",
                        "db_table": "intervenciones_tipointervencion",
                        "ordering": ["id"],
                    },
                ),
                migrations.CreateModel(
                    name="SubIntervencion",
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
                        ("nombre", models.CharField(max_length=255)),
                        (
                            "tipo_intervencion",
                            models.ForeignKey(
                                blank=True,
                                null=True,
                                on_delete=django.db.models.deletion.SET_NULL,
                                related_name="subintervenciones",
                                to="catalogo_intervenciones.tipointervencion",
                                verbose_name="Tipo de Intervención asociada",
                            ),
                        ),
                    ],
                    options={
                        "verbose_name": "Sub-Intervención",
                        "verbose_name_plural": "Sub-Intervenciones",
                        "db_table": "intervenciones_subintervencion",
                        "ordering": ["tipo_intervencion", "nombre"],
                    },
                ),
            ],
            database_operations=[],
        ),
        migrations.RunPython(content_types_a_kernel, content_types_a_intervenciones),
    ]
