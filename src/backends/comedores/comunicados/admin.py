from django.contrib import admin
from django.core.exceptions import ValidationError
from unfold.contrib.filters.admin import RangeDateTimeFilter

from core.admin_base import SisocModelAdmin, SisocTabularInline
from core.admin_operaciones import Operacion, OperacionesAdminMixin
from .models import Comunicado, ComunicadoAdjunto, EstadoComunicado, MailingJob
from .services_mailing_jobs import request_resume_mailing_job


class ComunicadoAdjuntoInline(SisocTabularInline):
    model = ComunicadoAdjunto
    extra = 1


def publicar_comunicado(comunicado, usuario, _datos):
    """Mismas guardas que ``ComunicadoPublicarView``."""
    if comunicado.estado == EstadoComunicado.PUBLICADO:
        raise ValidationError("El comunicado ya está publicado.")
    if comunicado.estado == EstadoComunicado.ARCHIVADO:
        raise ValidationError("No se puede publicar un comunicado archivado.")
    comunicado.publicar(usuario)


def archivar_comunicado(comunicado, usuario, _datos):
    """Mismas guardas que ``ComunicadoArchivarView``."""
    if comunicado.estado == EstadoComunicado.ARCHIVADO:
        raise ValidationError("El comunicado ya está archivado.")
    comunicado.archivar(usuario)


@admin.register(Comunicado)
class ComunicadoAdmin(OperacionesAdminMixin, SisocModelAdmin):
    operaciones = (
        Operacion(
            slug="publicar",
            titulo="Publicar comunicado",
            descripcion="Queda visible para sus destinatarios.",
            ejecutar=publicar_comunicado,
            campo_estado="estado",
            icono="publish",
        ),
        Operacion(
            slug="archivar",
            titulo="Archivar comunicado",
            descripcion="Deja de mostrarse y pierde el destacado.",
            ejecutar=archivar_comunicado,
            campo_estado="estado",
            icono="archive",
        ),
    )
    list_display = [
        "titulo",
        "estado",
        "tipo",
        "destacado",
        "fecha_publicacion",
        "usuario_creador",
    ]
    list_select_related = ["usuario_creador"]
    list_filter = [
        "estado",
        "tipo",
        "subtipo",
        "destacado",
        ("fecha_publicacion", RangeDateTimeFilter),
        ("fecha_vencimiento", RangeDateTimeFilter),
    ]
    search_fields = ["titulo", "cuerpo"]
    readonly_fields = ["fecha_creacion", "fecha_publicacion"]
    autocomplete_fields = [
        "usuario_creador",
        "usuario_ultima_modificacion",
        "comedores",
    ]
    raw_id_fields = ["organizaciones"]
    inlines = [ComunicadoAdjuntoInline]


@admin.register(ComunicadoAdjunto)
class ComunicadoAdjuntoAdmin(SisocModelAdmin):
    list_display = ["nombre_original", "comunicado", "fecha_subida"]
    list_select_related = ["comunicado"]
    list_filter = [("fecha_subida", RangeDateTimeFilter)]
    search_fields = ["nombre_original", "comunicado__titulo"]
    autocomplete_fields = ["comunicado"]


def reanudar_mailing_job(job, _usuario, _datos):
    return request_resume_mailing_job(job=job)


@admin.register(MailingJob)
class MailingJobAdmin(OperacionesAdminMixin, SisocModelAdmin):
    """Lotes de mailing: solo lectura, salvo reanudar un lote fallido."""

    operaciones = (
        Operacion(
            slug="reanudar",
            titulo="Reanudar lote de mailing",
            descripcion=(
                "Solo lotes fallidos: vuelve a Pendiente y el worker retoma el "
                "envío de mails desde la última fila procesada."
            ),
            ejecutar=reanudar_mailing_job,
            campo_estado="status",
            icono="replay",
        ),
    )
    list_display = [
        "id",
        "asunto",
        "status",
        "requested_by",
        "total_rows",
        "sent_rows",
        "rejected_rows",
        "resume_count",
        "requested_at",
        "finished_at",
    ]
    list_select_related = ["requested_by"]
    list_filter = [
        "status",
        ("requested_at", RangeDateTimeFilter),
        ("finished_at", RangeDateTimeFilter),
    ]
    search_fields = [
        "asunto",
        "original_filename",
        "requested_by__username",
        "last_error_message",
    ]
    # El permiso de cambio se mantiene para la operación; los campos no se editan.
    readonly_fields = [field.name for field in MailingJob._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
