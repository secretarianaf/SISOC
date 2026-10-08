"""Accesos PWA: los 4 modelos pasan de ``users`` (kernel) a ``pwa`` (core).

Solo cambia el estado de Django: las tablas siguen siendo ``users_*``
(``Meta.db_table``) y los índices, constraints y tablas M2M conservan sus
nombres. No hay DDL ni copia de datos. Los content types se reasignan a
``pwa`` para que permisos de grupos y auditoría sigan apuntando al mismo
registro. Ver docs/registro/decisiones/2026-09-30-monorepo-kernel-backends.md.
"""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


MODELOS = (
    "accesocomedorpwa",
    "accesoorganizacionpwa",
    "auditaccesocomedorpwa",
    "coordinadorequipotecnicopwa",
)


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


def content_types_a_pwa(apps, schema_editor):
    del schema_editor
    _mover_content_types(apps, "users", "pwa")


def content_types_a_users(apps, schema_editor):
    del schema_editor
    _mover_content_types(apps, "pwa", "users")


class Migration(migrations.Migration):

    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        ("users", "0057_merge_usuarios_secciones_y_roles_territoriales"),
        ("comedores", "0063_merge_subido_por_responsable_tarjeta"),
        ("duplas", "0001_squashed_0003"),
        ("organizaciones", "0022_issue_2445_territoriales_abordaje_comunitario"),
        ("pwa", "0024_backfill_representantes_pwa_permissions"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="AccesoComedorPWA",
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
                            "rol",
                            models.CharField(
                                choices=[
                                    ("representante", "Representante"),
                                    ("operador", "Operador"),
                                ],
                                max_length=20,
                            ),
                        ),
                        (
                            "tipo_asociacion",
                            models.CharField(
                                choices=[
                                    ("organizacion", "Organización"),
                                    ("espacio", "Espacio"),
                                ],
                                default="espacio",
                                max_length=20,
                            ),
                        ),
                        ("activo", models.BooleanField(default=True)),
                        ("fecha_creacion", models.DateTimeField(auto_now_add=True)),
                        ("fecha_baja", models.DateTimeField(blank=True, null=True)),
                        ("fecha_actualizacion", models.DateTimeField(auto_now=True)),
                        (
                            "comedor",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="accesos_pwa",
                                to="comedores.comedor",
                            ),
                        ),
                        (
                            "creado_por",
                            models.ForeignKey(
                                blank=True,
                                null=True,
                                on_delete=django.db.models.deletion.SET_NULL,
                                related_name="accesos_pwa_creados",
                                to=settings.AUTH_USER_MODEL,
                            ),
                        ),
                        (
                            "organizacion",
                            models.ForeignKey(
                                blank=True,
                                null=True,
                                on_delete=django.db.models.deletion.PROTECT,
                                related_name="accesos_pwa",
                                to="organizaciones.organizacion",
                            ),
                        ),
                        (
                            "user",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="accesos_pwa",
                                to=settings.AUTH_USER_MODEL,
                            ),
                        ),
                    ],
                    options={
                        "verbose_name": "Acceso PWA a comedor",
                        "verbose_name_plural": "Accesos PWA a comedor",
                        "db_table": "users_accesocomedorpwa",
                    },
                ),
                migrations.CreateModel(
                    name="AccesoOrganizacionPWA",
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
                        ("activo", models.BooleanField(default=True)),
                        ("fecha_creacion", models.DateTimeField(auto_now_add=True)),
                        ("fecha_baja", models.DateTimeField(blank=True, null=True)),
                        ("fecha_actualizacion", models.DateTimeField(auto_now=True)),
                        (
                            "creado_por",
                            models.ForeignKey(
                                blank=True,
                                null=True,
                                on_delete=django.db.models.deletion.SET_NULL,
                                related_name="accesos_organizacion_pwa_creados",
                                to=settings.AUTH_USER_MODEL,
                            ),
                        ),
                        (
                            "organizacion",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.PROTECT,
                                related_name="accesos_organizacion_pwa",
                                to="organizaciones.organizacion",
                            ),
                        ),
                        (
                            "user",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="accesos_organizacion_pwa",
                                to=settings.AUTH_USER_MODEL,
                            ),
                        ),
                    ],
                    options={
                        "verbose_name": "Acceso PWA a organización",
                        "verbose_name_plural": "Accesos PWA a organización",
                        "db_table": "users_accesoorganizacionpwa",
                    },
                ),
                migrations.CreateModel(
                    name="AuditAccesoComedorPWA",
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
                            "accion",
                            models.CharField(
                                choices=[
                                    ("create", "Alta"),
                                    ("reactivate", "Reactivación"),
                                    ("deactivate", "Baja"),
                                    ("update_permissions", "Edicion de permisos"),
                                ],
                                db_index=True,
                                max_length=20,
                            ),
                        ),
                        (
                            "fecha_evento",
                            models.DateTimeField(auto_now_add=True, db_index=True),
                        ),
                        ("metadata", models.JSONField(blank=True, default=dict)),
                        (
                            "acceso",
                            models.ForeignKey(
                                blank=True,
                                null=True,
                                on_delete=django.db.models.deletion.SET_NULL,
                                related_name="audit_logs",
                                to="pwa.accesocomedorpwa",
                            ),
                        ),
                        (
                            "actor",
                            models.ForeignKey(
                                blank=True,
                                null=True,
                                on_delete=django.db.models.deletion.SET_NULL,
                                related_name="accesos_pwa_audit_eventos",
                                to=settings.AUTH_USER_MODEL,
                            ),
                        ),
                        (
                            "comedor",
                            models.ForeignKey(
                                blank=True,
                                null=True,
                                on_delete=django.db.models.deletion.SET_NULL,
                                related_name="accesos_pwa_audit_logs",
                                to="comedores.comedor",
                            ),
                        ),
                        (
                            "organizacion",
                            models.ForeignKey(
                                blank=True,
                                null=True,
                                on_delete=django.db.models.deletion.SET_NULL,
                                related_name="accesos_pwa_audit_logs",
                                to="organizaciones.organizacion",
                            ),
                        ),
                        (
                            "user",
                            models.ForeignKey(
                                blank=True,
                                null=True,
                                on_delete=django.db.models.deletion.SET_NULL,
                                related_name="accesos_pwa_audit_logs",
                                to=settings.AUTH_USER_MODEL,
                            ),
                        ),
                    ],
                    options={
                        "verbose_name": "Auditoría de acceso PWA",
                        "verbose_name_plural": "Auditorías de accesos PWA",
                        "db_table": "users_auditaccesocomedorpwa",
                        "ordering": ["-fecha_evento", "-id"],
                    },
                ),
                migrations.CreateModel(
                    name="CoordinadorEquipoTecnicoPWA",
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
                        ("activo", models.BooleanField(default=True)),
                        ("fecha_creacion", models.DateTimeField(auto_now_add=True)),
                        ("fecha_actualizacion", models.DateTimeField(auto_now=True)),
                        (
                            "comedores_adicionales",
                            models.ManyToManyField(
                                blank=True,
                                related_name="coordinadores_pwa_adicionales",
                                to="comedores.comedor",
                                verbose_name="Comedores adicionales",
                            ),
                        ),
                        (
                            "duplas",
                            models.ManyToManyField(
                                blank=True,
                                related_name="coordinadores_pwa",
                                to="duplas.dupla",
                                verbose_name="Equipos técnicos",
                            ),
                        ),
                        (
                            "user",
                            models.OneToOneField(
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="coordinador_equipo_tecnico_pwa",
                                to=settings.AUTH_USER_MODEL,
                            ),
                        ),
                    ],
                    options={
                        "verbose_name": "Coordinador de equipo técnico PWA",
                        "verbose_name_plural": "Coordinadores de equipo técnico PWA",
                        "db_table": "users_coordinadorequipotecnicopwa",
                    },
                ),
                migrations.AddIndex(
                    model_name="accesocomedorpwa",
                    index=models.Index(
                        fields=["user", "activo"], name="users_acces_user_id_509e83_idx"
                    ),
                ),
                migrations.AddIndex(
                    model_name="accesocomedorpwa",
                    index=models.Index(
                        fields=["comedor", "rol", "activo"],
                        name="users_acces_comedor_e0726d_idx",
                    ),
                ),
                migrations.AddIndex(
                    model_name="accesocomedorpwa",
                    index=models.Index(
                        fields=["organizacion", "activo"],
                        name="users_acces_organiz_e9365d_idx",
                    ),
                ),
                migrations.AddIndex(
                    model_name="accesocomedorpwa",
                    index=models.Index(
                        fields=["creado_por", "activo"],
                        name="users_acces_creado__c110ef_idx",
                    ),
                ),
                migrations.AddConstraint(
                    model_name="accesocomedorpwa",
                    constraint=models.UniqueConstraint(
                        fields=("user", "comedor"), name="unique_pwa_user_comedor"
                    ),
                ),
                migrations.AddIndex(
                    model_name="accesoorganizacionpwa",
                    index=models.Index(
                        fields=["user", "activo"], name="users_acces_user_id_9d9d81_idx"
                    ),
                ),
                migrations.AddIndex(
                    model_name="accesoorganizacionpwa",
                    index=models.Index(
                        fields=["organizacion", "activo"],
                        name="users_acces_organiz_e0504d_idx",
                    ),
                ),
                migrations.AddConstraint(
                    model_name="accesoorganizacionpwa",
                    constraint=models.UniqueConstraint(
                        fields=("user", "organizacion"),
                        name="unique_pwa_user_organizacion",
                    ),
                ),
                migrations.AddIndex(
                    model_name="auditaccesocomedorpwa",
                    index=models.Index(
                        fields=["user", "fecha_evento"],
                        name="users_audit_user_id_0e2825_idx",
                    ),
                ),
                migrations.AddIndex(
                    model_name="auditaccesocomedorpwa",
                    index=models.Index(
                        fields=["comedor", "fecha_evento"],
                        name="users_audit_comedor_fa16b0_idx",
                    ),
                ),
                migrations.AddIndex(
                    model_name="auditaccesocomedorpwa",
                    index=models.Index(
                        fields=["accion", "fecha_evento"],
                        name="users_audit_accion_71bafe_idx",
                    ),
                ),
                migrations.AddIndex(
                    model_name="coordinadorequipotecnicopwa",
                    index=models.Index(
                        fields=["user", "activo"], name="users_coord_user_id_b87430_idx"
                    ),
                ),
            ],
            database_operations=[],
        ),
        migrations.RunPython(content_types_a_pwa, content_types_a_users),
    ]
