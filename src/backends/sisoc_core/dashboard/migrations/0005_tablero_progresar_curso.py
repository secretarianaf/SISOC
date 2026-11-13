"""Tablero Becas Progresar · Curso obligatorio.

Modelos de solo lectura (managed=False) sobre dos tablas `bi_` que mantiene el equipo
de Datos: esta migración NO crea ni modifica tablas. Solo registra los modelos y las
llaves `dashboard.view_tablero_progresar_curso` (ver el tablero, recortado a las
provincias del usuario) y `dashboard.view_tablero_progresar_curso_nacional` (todo el país).
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_squashed_0007"),
        ("dashboard", "0004_tablero_ruta_interna"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProgresarCursoResumen",
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
                    "provincia_codigo",
                    models.PositiveSmallIntegerField(
                        help_text="Código INDEC de la provincia."
                    ),
                ),
                ("linea", models.CharField(max_length=30)),
                ("estado_curso", models.CharField(max_length=25)),
                ("genero_codigo", models.CharField(max_length=1, null=True)),
                ("rango_edad", models.CharField(max_length=10)),
                ("tramo_inactividad", models.CharField(max_length=10, null=True)),
                ("tramo_aprobacion", models.CharField(max_length=15, null=True)),
                ("titulares", models.PositiveIntegerField()),
                ("suma_edad", models.PositiveIntegerField(null=True)),
                ("casos_edad", models.PositiveIntegerField()),
                ("fecha_carga", models.DateTimeField()),
                (
                    "provincia",
                    models.ForeignKey(
                        db_constraint=False,
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to="core.provincia",
                    ),
                ),
            ],
            options={
                "verbose_name": "resumen del tablero Progresar curso obligatorio",
                "db_table": "bi_progresar_curso_obligatorio_resumen",
                "permissions": [
                    (
                        "view_tablero_progresar_curso",
                        "Puede ver el Tablero Becas Progresar · Curso obligatorio",
                    ),
                    (
                        "view_tablero_progresar_curso_nacional",
                        "Puede ver todo el país en el Tablero Becas Progresar · Curso obligatorio",
                    ),
                ],
                "managed": False,
                "default_permissions": (),
            },
        ),
        migrations.CreateModel(
            name="ProgresarCursoEvolucion",
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
                ("fecha", models.DateField()),
                (
                    "provincia_codigo",
                    models.PositiveSmallIntegerField(
                        help_text="Código INDEC de la provincia."
                    ),
                ),
                ("linea", models.CharField(max_length=30)),
                ("genero_codigo", models.CharField(max_length=1, null=True)),
                ("inscriptos", models.PositiveIntegerField()),
                ("aprobados", models.PositiveIntegerField()),
                ("fecha_carga", models.DateTimeField()),
                (
                    "provincia",
                    models.ForeignKey(
                        db_constraint=False,
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to="core.provincia",
                    ),
                ),
            ],
            options={
                "verbose_name": "evolución del tablero Progresar curso obligatorio",
                "db_table": "bi_progresar_curso_obligatorio_evolucion",
                "managed": False,
                "default_permissions": (),
            },
        ),
    ]
