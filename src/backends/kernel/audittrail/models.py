"""Modelos auxiliares de auditoría propios de SISOC."""

import uuid

from django.conf import settings
from django.db import models

AUDITLOG_LOGENTRY_MODEL = getattr(
    settings, "AUDITLOG_LOGENTRY_MODEL", "auditlog.LogEntry"
)


class AuditEntryMeta(models.Model):
    """
    Metadata complementaria para `auditlog.LogEntry`.

    Se almacena fuera de django-auditlog para mantener compatibilidad con la
    librería y permitir evolucionar trazabilidad (batch/source/snapshots) sin
    tocar el esquema de terceros.
    """

    log_entry = models.OneToOneField(
        AUDITLOG_LOGENTRY_MODEL,
        on_delete=models.CASCADE,
        related_name="audittrail_meta",
    )
    actor_username_snapshot = models.CharField(max_length=150, blank=True, default="")
    actor_full_name_snapshot = models.CharField(max_length=255, blank=True, default="")
    actor_display_snapshot = models.CharField(max_length=255, blank=True, default="")
    source = models.CharField(max_length=64, blank=True, default="", db_index=True)
    batch_key = models.CharField(max_length=255, blank=True, default="", db_index=True)
    extra = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Metadata de auditoría"
        verbose_name_plural = "Metadatas de auditoría"
        permissions = (("export_auditlog", "Puede exportar resultados de auditoría"),)

    def __str__(self):
        return f"AuditEntryMeta(log_entry_id={self.log_entry_id})"


class AuditoriaSesionPWA(models.Model):
    """Auditoría de eventos de autenticación/uso de API PWA."""

    EVENTO_LOGIN_OK = "login_ok"
    EVENTO_LOGIN_ERROR = "login_error"
    EVENTO_LOGOUT = "logout"
    EVENTO_TOKEN_INVALIDO = "token_invalido"
    EVENTO_ME_OK = "me_ok"

    RESULTADO_OK = "ok"
    RESULTADO_ERROR = "error"

    EVENTO_CHOICES = (
        (EVENTO_LOGIN_OK, "Login exitoso"),
        (EVENTO_LOGIN_ERROR, "Login fallido"),
        (EVENTO_LOGOUT, "Logout"),
        (EVENTO_TOKEN_INVALIDO, "Token inválido"),
        (EVENTO_ME_OK, "Consulta de contexto"),
    )
    RESULTADO_CHOICES = (
        (RESULTADO_OK, "OK"),
        (RESULTADO_ERROR, "Error"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="auditorias_pwa",
    )
    username_intentado = models.CharField(max_length=150, null=True, blank=True)
    evento = models.CharField(max_length=30, choices=EVENTO_CHOICES)
    resultado = models.CharField(max_length=10, choices=RESULTADO_CHOICES)
    fecha_evento = models.DateTimeField(auto_now_add=True, db_index=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=512, null=True, blank=True)
    path = models.CharField(max_length=255)
    metodo_http = models.CharField(max_length=10)
    codigo_respuesta = models.PositiveSmallIntegerField(null=True, blank=True)
    motivo_error = models.CharField(max_length=255, null=True, blank=True)
    session_id = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True)
    rol_pwa_snapshot = models.JSONField(default=list, blank=True)
    comedor_ids_snapshot = models.JSONField(default=list, blank=True)
    app_version = models.CharField(max_length=50, null=True, blank=True)
    platform = models.CharField(max_length=30, null=True, blank=True)
    is_standalone = models.BooleanField(null=True, blank=True)

    class Meta:
        db_table = "pwa_auditoriasesionpwa"
        verbose_name = "Auditoría sesión PWA"
        verbose_name_plural = "Auditorías sesiones PWA"
        indexes = [
            models.Index(
                fields=["user", "fecha_evento"], name="pwa_auditor_user_id_951231_idx"
            ),
            models.Index(
                fields=["evento", "fecha_evento"], name="pwa_auditor_evento_5c0ad0_idx"
            ),
            models.Index(
                fields=["resultado", "fecha_evento"],
                name="pwa_auditor_resulta_ae14a4_idx",
            ),
        ]

    def __str__(self):
        username = (
            self.user.username if self.user_id else self.username_intentado or "-"
        )
        return f"{self.evento} - {username} - {self.fecha_evento:%Y-%m-%d %H:%M:%S}"
