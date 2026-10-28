"""Lotes de importación de usuarios y de envío de credenciales (issue #2789).

Los modelos viven en el kernel (``users``) pero sus services son del core
(``usuarios``): se registran desde acá para que el kernel no importe el core y
solo existan en el proceso que corre los workers.
"""

from django.contrib import admin
from unfold.contrib.filters.admin import (
    AutocompleteSelectFilter,
    ChoicesDropdownFilter,
    RangeDateTimeFilter,
)

from core.admin_base import SisocModelAdmin
from core.admin_operaciones import Operacion, OperacionesAdminMixin
from users.models import (
    BulkCredentialsJob,
    BulkCredentialsJobRow,
    UserImportJob,
    UserImportJobRow,
)
from usuarios.services_bulk_credentials_jobs import (
    request_resume_bulk_credentials_job,
)
from usuarios.services_user_import_jobs import request_resume_user_import_job

DESCRIPCION_REANUDAR = (
    "Vuelve el lote a pendiente para que el worker siga desde la última fila "
    "procesada. Solo aplica a lotes fallidos."
)


def _reanudar_importacion_usuarios(job, _usuario, _datos):
    return request_resume_user_import_job(job=job)


def _reanudar_envio_credenciales(job, _usuario, _datos):
    return request_resume_bulk_credentials_job(job=job)


class LoteSoloLecturaAdmin(OperacionesAdminMixin, SisocModelAdmin):
    """Lote de un worker: se consulta y se opera, no se edita a mano."""

    list_select_related = ("requested_by",)
    search_fields = ("original_filename", "requested_by__username")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        # Sin edición del registro: el formulario queda de solo lectura. El
        # permiso a nivel modelo (obj=None) habilita las operaciones.
        return obj is None and super().has_change_permission(request)


class FilaSoloLecturaAdmin(SisocModelAdmin):
    """Filas procesadas de un lote: historial de solo lectura."""

    list_select_related = ("job",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(UserImportJob)
class UserImportJobAdmin(LoteSoloLecturaAdmin):
    list_display = (
        "id",
        "requested_by",
        "original_filename",
        "status",
        "is_pwa_import",
        "total_rows",
        "processed_rows",
        "failed_rows",
        "requested_at",
    )
    list_filter = (
        ("status", ChoicesDropdownFilter),
        "is_pwa_import",
        "send_credentials",
        ("requested_at", RangeDateTimeFilter),
    )
    operaciones = (
        Operacion(
            slug="reanudar",
            titulo="Reanudar lote fallido",
            descripcion=DESCRIPCION_REANUDAR,
            ejecutar=_reanudar_importacion_usuarios,
            campo_estado="status",
            icono="replay",
        ),
    )


@admin.register(UserImportJobRow)
class UserImportJobRowAdmin(FilaSoloLecturaAdmin):
    list_display = ("job", "fila", "email", "apellido", "nombre", "status")
    list_filter = (
        ("job", AutocompleteSelectFilter),
        ("status", ChoicesDropdownFilter),
        ("processed_at", RangeDateTimeFilter),
    )
    search_fields = ("email", "apellido", "nombre")


@admin.register(BulkCredentialsJob)
class BulkCredentialsJobAdmin(LoteSoloLecturaAdmin):
    list_display = (
        "id",
        "requested_by",
        "original_filename",
        "send_type",
        "status",
        "total_rows",
        "processed_rows",
        "rejected_rows",
        "requested_at",
    )
    list_filter = (
        ("status", ChoicesDropdownFilter),
        "send_type",
        ("requested_at", RangeDateTimeFilter),
    )
    operaciones = (
        Operacion(
            slug="reanudar",
            titulo="Reanudar lote fallido",
            descripcion=DESCRIPCION_REANUDAR,
            ejecutar=_reanudar_envio_credenciales,
            campo_estado="status",
            icono="replay",
        ),
    )


@admin.register(BulkCredentialsJobRow)
class BulkCredentialsJobRowAdmin(FilaSoloLecturaAdmin):
    list_display = ("job", "fila", "usuario", "mail_destino", "status")
    list_filter = (
        ("job", AutocompleteSelectFilter),
        ("status", ChoicesDropdownFilter),
        ("processed_at", RangeDateTimeFilter),
    )
    search_fields = ("usuario", "mail_destino")
