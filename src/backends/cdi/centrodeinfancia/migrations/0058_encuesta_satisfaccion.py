"""Encuesta de satisfacción de CDI (210SatisfaccionCDI): tablas.

Los triggers de inmutabilidad y la vista del área van en la 0059, aparte, para
que estas tablas queden registradas aunque falle la creación de los triggers
(por ejemplo, por privilegios del usuario de la migración) y la 0059 se pueda
reintentar sola.
"""

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("centrodeinfancia", "0057_merge_estado_cdi_nomina_por_edad"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="EncuestaSatisfaccionRechazo",
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
                ("ts", models.DateTimeField(db_index=True)),
                (
                    "motivo",
                    models.PositiveSmallIntegerField(
                        choices=[
                            (1, "Captcha no superado"),
                            (2, "Límite de envíos por IP superado"),
                            (3, "Token inválido, vencido o ya utilizado"),
                            (4, "Error de validación de datos"),
                            (5, "CDI inexistente o dado de baja"),
                        ]
                    ),
                ),
                ("cdi_id", models.PositiveIntegerField(blank=True, null=True)),
                (
                    "canal_ingreso",
                    models.PositiveSmallIntegerField(
                        blank=True,
                        choices=[
                            (1, "QR"),
                            (2, "URL acortada"),
                            (9, "Sin identificar"),
                        ],
                        null=True,
                    ),
                ),
                ("ip_hash", models.CharField(blank=True, max_length=64, null=True)),
                ("detalle", models.CharField(blank=True, max_length=255, null=True)),
            ],
            options={
                "verbose_name": "Encuesta de satisfacción CDI - rechazo",
                "verbose_name_plural": "Encuesta de satisfacción CDI - rechazos",
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(("motivo__in", [1, 2, 3, 4, 5])),
                        name="cdi_encuesta_rechazo_motivo_dominio",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="EncuestaSatisfaccionToken",
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
                ("token_hash", models.CharField(max_length=64, unique=True)),
                ("emitido_en", models.DateTimeField()),
                ("expira_en", models.DateTimeField(db_index=True)),
                ("usado_en", models.DateTimeField(blank=True, null=True)),
                (
                    "canal_ingreso",
                    models.PositiveSmallIntegerField(
                        choices=[(1, "QR"), (2, "URL acortada"), (9, "Sin identificar")]
                    ),
                ),
                ("ip_hash", models.CharField(blank=True, max_length=64, null=True)),
            ],
            options={
                "verbose_name": "Encuesta de satisfacción CDI - token",
                "verbose_name_plural": "Encuesta de satisfacción CDI - tokens",
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(("canal_ingreso__in", [1, 2, 9])),
                        name="cdi_encuesta_token_canal_dominio",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="EncuestaSatisfaccionRespuesta",
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
                    "uuid_respuesta",
                    models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
                ),
                ("version_instrumento", models.CharField(max_length=10)),
                (
                    "canal_ingreso",
                    models.PositiveSmallIntegerField(
                        choices=[(1, "QR"), (2, "URL acortada"), (9, "Sin identificar")]
                    ),
                ),
                ("jurisdiccion", models.CharField(max_length=100)),
                ("departamento", models.CharField(max_length=100)),
                ("institucion", models.CharField(max_length=255)),
                ("codigo_institucion", models.CharField(max_length=32)),
                (
                    "sala",
                    models.PositiveSmallIntegerField(
                        choices=[
                            (1, "Menos de un año"),
                            (2, "1 año"),
                            (3, "2 años"),
                            (4, "3 años"),
                            (5, "4 años"),
                            (6, "Multiedad"),
                        ]
                    ),
                ),
                (
                    "sala_origen",
                    models.PositiveSmallIntegerField(
                        choices=[
                            (1, "Salas de la nómina del CDI"),
                            (2, "Lista completa (CDI sin nómina activa)"),
                        ]
                    ),
                ),
                ("fecha_carga", models.DateTimeField()),
                (
                    "p01_informacion_avances",
                    models.PositiveSmallIntegerField(
                        choices=[
                            (1, "Nunca"),
                            (2, "Casi nunca"),
                            (3, "A veces"),
                            (4, "Casi siempre"),
                            (5, "Siempre"),
                            (9, "No brinda alimentación"),
                        ],
                        verbose_name="P01. Información sobre los avances",
                    ),
                ),
                (
                    "p02_recomendaciones_hogar",
                    models.PositiveSmallIntegerField(
                        choices=[
                            (1, "Nunca"),
                            (2, "Casi nunca"),
                            (3, "A veces"),
                            (4, "Casi siempre"),
                            (5, "Siempre"),
                            (9, "No brinda alimentación"),
                        ],
                        verbose_name="P02. Recomendaciones para el hogar",
                    ),
                ),
                (
                    "p03_escucha_respeto",
                    models.PositiveSmallIntegerField(
                        choices=[
                            (1, "Nunca"),
                            (2, "Casi nunca"),
                            (3, "A veces"),
                            (4, "Casi siempre"),
                            (5, "Siempre"),
                            (9, "No brinda alimentación"),
                        ],
                        verbose_name="P03. Escucha y respeto",
                    ),
                ),
                (
                    "p04_respeto_cultura",
                    models.PositiveSmallIntegerField(
                        choices=[
                            (1, "Nunca"),
                            (2, "Casi nunca"),
                            (3, "A veces"),
                            (4, "Casi siempre"),
                            (5, "Siempre"),
                            (9, "No brinda alimentación"),
                        ],
                        verbose_name="P04. Respeto por la cultura familiar",
                    ),
                ),
                (
                    "p05_comodidad_dudas",
                    models.PositiveSmallIntegerField(
                        choices=[
                            (1, "Nunca"),
                            (2, "Casi nunca"),
                            (3, "A veces"),
                            (4, "Casi siempre"),
                            (5, "Siempre"),
                            (9, "No brinda alimentación"),
                        ],
                        verbose_name="P05. Comodidad para consultar dudas",
                    ),
                ),
                (
                    "p06_ingreso_alegria",
                    models.PositiveSmallIntegerField(
                        choices=[
                            (1, "Nunca"),
                            (2, "Casi nunca"),
                            (3, "A veces"),
                            (4, "Casi siempre"),
                            (5, "Siempre"),
                            (9, "No brinda alimentación"),
                        ],
                        verbose_name="P06. Ingreso con alegría",
                    ),
                ),
                (
                    "p07_deteccion_malestar",
                    models.PositiveSmallIntegerField(
                        choices=[
                            (1, "Nunca"),
                            (2, "Casi nunca"),
                            (3, "A veces"),
                            (4, "Casi siempre"),
                            (5, "Siempre"),
                            (9, "No brinda alimentación"),
                        ],
                        verbose_name="P07. Detección de malestar",
                    ),
                ),
                (
                    "p08_seguridad_proteccion",
                    models.PositiveSmallIntegerField(
                        choices=[
                            (1, "Nunca"),
                            (2, "Casi nunca"),
                            (3, "A veces"),
                            (4, "Casi siempre"),
                            (5, "Siempre"),
                            (9, "No brinda alimentación"),
                        ],
                        verbose_name="P08. Seguridad y protección",
                    ),
                ),
                (
                    "p09_confianza_educadora",
                    models.PositiveSmallIntegerField(
                        choices=[
                            (1, "Nunca"),
                            (2, "Casi nunca"),
                            (3, "A veces"),
                            (4, "Casi siempre"),
                            (5, "Siempre"),
                            (9, "No brinda alimentación"),
                        ],
                        verbose_name="P09. Confianza con la educadora",
                    ),
                ),
                (
                    "p10_participacion_juegos",
                    models.PositiveSmallIntegerField(
                        choices=[
                            (1, "Nunca"),
                            (2, "Casi nunca"),
                            (3, "A veces"),
                            (4, "Casi siempre"),
                            (5, "Siempre"),
                            (9, "No brinda alimentación"),
                        ],
                        verbose_name="P10. Participación en los juegos",
                    ),
                ),
                (
                    "p11_materiales_adecuados",
                    models.PositiveSmallIntegerField(
                        choices=[
                            (1, "Nunca"),
                            (2, "Casi nunca"),
                            (3, "A veces"),
                            (4, "Casi siempre"),
                            (5, "Siempre"),
                            (9, "No brinda alimentación"),
                        ],
                        verbose_name="P11. Materiales adecuados",
                    ),
                ),
                (
                    "p12_limpieza_orden",
                    models.PositiveSmallIntegerField(
                        choices=[
                            (1, "Nunca"),
                            (2, "Casi nunca"),
                            (3, "A veces"),
                            (4, "Casi siempre"),
                            (5, "Siempre"),
                            (9, "No brinda alimentación"),
                        ],
                        verbose_name="P12. Limpieza y orden",
                    ),
                ),
                (
                    "p13_alimentacion",
                    models.PositiveSmallIntegerField(
                        choices=[
                            (1, "Nunca"),
                            (2, "Casi nunca"),
                            (3, "A veces"),
                            (4, "Casi siempre"),
                            (5, "Siempre"),
                            (9, "No brinda alimentación"),
                        ],
                        verbose_name="P13. Alimentación",
                    ),
                ),
                (
                    "p14_medidas_seguridad",
                    models.PositiveSmallIntegerField(
                        choices=[
                            (1, "Nunca"),
                            (2, "Casi nunca"),
                            (3, "A veces"),
                            (4, "Casi siempre"),
                            (5, "Siempre"),
                            (9, "No brinda alimentación"),
                        ],
                        verbose_name="P14. Medidas de seguridad",
                    ),
                ),
                (
                    "p15_horario_adecuado",
                    models.PositiveSmallIntegerField(
                        choices=[
                            (1, "Nunca"),
                            (2, "Casi nunca"),
                            (3, "A veces"),
                            (4, "Casi siempre"),
                            (5, "Siempre"),
                            (9, "No brinda alimentación"),
                        ],
                        verbose_name="P15. Horario adecuado",
                    ),
                ),
                (
                    "comentarios",
                    models.CharField(blank=True, max_length=1000, null=True),
                ),
                ("ts_inicio", models.DateTimeField()),
                ("ts_envio", models.DateTimeField()),
                ("duracion_seg", models.PositiveIntegerField(blank=True, null=True)),
                ("ip_hash", models.CharField(blank=True, max_length=64, null=True)),
                ("captcha_proveedor", models.CharField(max_length=20)),
                (
                    "captcha_score",
                    models.DecimalField(
                        blank=True, decimal_places=3, max_digits=4, null=True
                    ),
                ),
                (
                    "dispositivo_tipo",
                    models.PositiveSmallIntegerField(
                        choices=[
                            (1, "Móvil"),
                            (2, "Tablet"),
                            (3, "Escritorio"),
                            (9, "Sin identificar"),
                        ]
                    ),
                ),
                ("app_version", models.CharField(max_length=20)),
                (
                    "estado_registro",
                    models.PositiveSmallIntegerField(
                        choices=[(1, "Válido"), (2, "Anulado por auditoría")], default=1
                    ),
                ),
                (
                    "motivo_anulacion",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                ("fecha_anulacion", models.DateTimeField(blank=True, null=True)),
                ("hash_integridad", models.CharField(max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "anulado_por",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "centro",
                    models.ForeignKey(
                        db_column="cdi_id",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="encuestas_satisfaccion",
                        to="centrodeinfancia.centrodeinfancia",
                    ),
                ),
                (
                    "token",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="respuesta",
                        to="centrodeinfancia.encuestasatisfacciontoken",
                    ),
                ),
            ],
            options={
                "verbose_name": "Encuesta de satisfacción CDI - respuesta",
                "verbose_name_plural": "Encuesta de satisfacción CDI - respuestas",
                "indexes": [
                    models.Index(
                        fields=["centro", "fecha_carga"],
                        name="cdi_encuesta_cdi_fecha_idx",
                    ),
                    models.Index(
                        fields=["jurisdiccion", "departamento"],
                        name="cdi_encuesta_juris_depto_idx",
                    ),
                    models.Index(fields=["fecha_carga"], name="cdi_encuesta_fecha_idx"),
                    models.Index(
                        fields=["ip_hash", "ts_envio"], name="cdi_encuesta_ip_idx"
                    ),
                ],
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(
                            ("p01_informacion_avances__in", [1, 2, 3, 4, 5])
                        ),
                        name="cdi_encuesta_p01_dominio",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            ("p02_recomendaciones_hogar__in", [1, 2, 3, 4, 5])
                        ),
                        name="cdi_encuesta_p02_dominio",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            ("p03_escucha_respeto__in", [1, 2, 3, 4, 5])
                        ),
                        name="cdi_encuesta_p03_dominio",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            ("p04_respeto_cultura__in", [1, 2, 3, 4, 5])
                        ),
                        name="cdi_encuesta_p04_dominio",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            ("p05_comodidad_dudas__in", [1, 2, 3, 4, 5])
                        ),
                        name="cdi_encuesta_p05_dominio",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            ("p06_ingreso_alegria__in", [1, 2, 3, 4, 5])
                        ),
                        name="cdi_encuesta_p06_dominio",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            ("p07_deteccion_malestar__in", [1, 2, 3, 4, 5])
                        ),
                        name="cdi_encuesta_p07_dominio",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            ("p08_seguridad_proteccion__in", [1, 2, 3, 4, 5])
                        ),
                        name="cdi_encuesta_p08_dominio",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            ("p09_confianza_educadora__in", [1, 2, 3, 4, 5])
                        ),
                        name="cdi_encuesta_p09_dominio",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            ("p10_participacion_juegos__in", [1, 2, 3, 4, 5])
                        ),
                        name="cdi_encuesta_p10_dominio",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            ("p11_materiales_adecuados__in", [1, 2, 3, 4, 5])
                        ),
                        name="cdi_encuesta_p11_dominio",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(("p12_limpieza_orden__in", [1, 2, 3, 4, 5])),
                        name="cdi_encuesta_p12_dominio",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            ("p13_alimentacion__in", [1, 2, 3, 4, 5, 9])
                        ),
                        name="cdi_encuesta_p13_dominio",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            ("p14_medidas_seguridad__in", [1, 2, 3, 4, 5])
                        ),
                        name="cdi_encuesta_p14_dominio",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            ("p15_horario_adecuado__in", [1, 2, 3, 4, 5])
                        ),
                        name="cdi_encuesta_p15_dominio",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(("canal_ingreso__in", [1, 2, 9])),
                        name="cdi_encuesta_canal_dominio",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(("sala__in", [1, 2, 3, 4, 5, 6])),
                        name="cdi_encuesta_sala_dominio",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(("sala_origen__in", [1, 2])),
                        name="cdi_encuesta_sala_origen_dominio",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(("dispositivo_tipo__in", [1, 2, 3, 9])),
                        name="cdi_encuesta_dispositivo_dominio",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(("estado_registro__in", [1, 2])),
                        name="cdi_encuesta_estado_dominio",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(("ts_envio__gte", models.F("ts_inicio"))),
                        name="cdi_encuesta_tiempos",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            ("estado_registro", 1),
                            models.Q(
                                ("anulado_por__isnull", False),
                                ("fecha_anulacion__isnull", False),
                                ("motivo_anulacion__isnull", False),
                            ),
                            _connector="OR",
                        ),
                        name="cdi_encuesta_anulacion_completa",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            ("captcha_score__isnull", True),
                            models.Q(
                                ("captcha_score__gte", 0), ("captcha_score__lte", 1)
                            ),
                            _connector="OR",
                        ),
                        name="cdi_encuesta_captcha_score",
                    ),
                ],
            },
        ),
    ]
