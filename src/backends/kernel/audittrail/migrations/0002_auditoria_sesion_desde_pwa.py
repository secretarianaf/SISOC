"""Traslado de estado; conserva tabla, content type y permisos existentes."""

import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def mover_content_type(apps, schema_editor, origen, destino):
    content_types = apps.get_model("contenttypes", "ContentType").objects.using(
        schema_editor.connection.alias
    )
    source = content_types.filter(app_label=origen, model="auditoriasesionpwa")
    destination = content_types.filter(app_label=destino, model="auditoriasesionpwa")
    if source.exists() and destination.exists():
        raise RuntimeError(
            "Existen ambos content types de AuditoriaSesionPWA; resolver "
            "antes de migrar para preservar permisos y asignaciones."
        )
    source.update(app_label=destino)


def forwards(apps, schema_editor):
    mover_content_type(apps, schema_editor, "pwa", "audittrail")


def backwards(apps, schema_editor):
    mover_content_type(apps, schema_editor, "audittrail", "pwa")


class Migration(migrations.Migration):
    dependencies = [
        ("audittrail", "0001_squashed_0003"),
        ("pwa", "0026_inicializar_acceso_web"),
        ("contenttypes", "0002_remove_content_type_name"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name="AuditoriaSesionPWA",
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
                            "username_intentado",
                            models.CharField(blank=True, max_length=150, null=True),
                        ),
                        (
                            "evento",
                            models.CharField(
                                choices=[
                                    ("login_ok", "Login exitoso"),
                                    ("login_error", "Login fallido"),
                                    ("logout", "Logout"),
                                    ("token_invalido", "Token inválido"),
                                    ("me_ok", "Consulta de contexto"),
                                ],
                                max_length=30,
                            ),
                        ),
                        (
                            "resultado",
                            models.CharField(
                                choices=[("ok", "OK"), ("error", "Error")],
                                max_length=10,
                            ),
                        ),
                        (
                            "fecha_evento",
                            models.DateTimeField(auto_now_add=True, db_index=True),
                        ),
                        ("ip", models.GenericIPAddressField(blank=True, null=True)),
                        (
                            "user_agent",
                            models.CharField(blank=True, max_length=512, null=True),
                        ),
                        ("path", models.CharField(max_length=255)),
                        ("metodo_http", models.CharField(max_length=10)),
                        (
                            "codigo_respuesta",
                            models.PositiveSmallIntegerField(blank=True, null=True),
                        ),
                        (
                            "motivo_error",
                            models.CharField(blank=True, max_length=255, null=True),
                        ),
                        (
                            "session_id",
                            models.UUIDField(
                                db_index=True, default=uuid.uuid4, editable=False
                            ),
                        ),
                        (
                            "rol_pwa_snapshot",
                            models.JSONField(blank=True, default=list),
                        ),
                        (
                            "comedor_ids_snapshot",
                            models.JSONField(blank=True, default=list),
                        ),
                        (
                            "app_version",
                            models.CharField(blank=True, max_length=50, null=True),
                        ),
                        (
                            "platform",
                            models.CharField(blank=True, max_length=30, null=True),
                        ),
                        ("is_standalone", models.BooleanField(blank=True, null=True)),
                        (
                            "user",
                            models.ForeignKey(
                                blank=True,
                                null=True,
                                on_delete=django.db.models.deletion.SET_NULL,
                                related_name="auditorias_pwa",
                                to=settings.AUTH_USER_MODEL,
                            ),
                        ),
                    ],
                    options={
                        "db_table": "pwa_auditoriasesionpwa",
                        "verbose_name": "Auditoría sesión PWA",
                        "verbose_name_plural": "Auditorías sesiones PWA",
                        "indexes": [
                            models.Index(
                                fields=["user", "fecha_evento"],
                                name="pwa_auditor_user_id_951231_idx",
                            ),
                            models.Index(
                                fields=["evento", "fecha_evento"],
                                name="pwa_auditor_evento_5c0ad0_idx",
                            ),
                            models.Index(
                                fields=["resultado", "fecha_evento"],
                                name="pwa_auditor_resulta_ae14a4_idx",
                            ),
                        ],
                    },
                ),
            ],
        ),
        migrations.RunPython(forwards, backwards),
    ]
