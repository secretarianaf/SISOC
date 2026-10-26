"""Bases comunes de los ModelAdmin de SISOC sobre Django Unfold (issue #2789).

Todo ``admin.py`` del repo hereda de acá en vez de ``django.contrib.admin``:
así el look, los filtros y las acciones de Unfold quedan iguales en todos los
dominios y en todos los runtimes.
"""

from auditlog.models import LogEntry
from django.contrib.contenttypes.models import ContentType
from unfold.admin import ModelAdmin, StackedInline, TabularInline

# Eventos de auditlog que se muestran en el historial de un registro.
MAX_EVENTOS_HISTORIAL = 50


def historial_auditlog(model, object_id) -> dict:
    """Últimos eventos de auditlog de un registro, como tabla de Unfold."""
    eventos = (
        LogEntry.objects.filter(
            content_type=ContentType.objects.get_for_model(model),
            object_pk=str(object_id),
        )
        .select_related("actor")
        .order_by("-timestamp")[:MAX_EVENTOS_HISTORIAL]
    )
    filas = []
    for evento in eventos:
        datos = (
            evento.additional_data if isinstance(evento.additional_data, dict) else {}
        )
        filas.append(
            [
                evento.timestamp.strftime("%d/%m/%Y %H:%M"),
                evento.actor.get_username() if evento.actor else "Sistema",
                datos.get("titulo") or evento.get_action_display(),
                evento.changes_str,
                datos.get("motivo", ""),
            ]
        )
    return {
        "headers": ["Fecha", "Usuario", "Acción", "Cambios", "Motivo"],
        "rows": filas,
    }


class SisocModelAdmin(ModelAdmin):
    """ModelAdmin base del admin de desarrollo y soporte."""

    # Los filtros de Unfold (rangos, dropdowns) se aplican con un botón.
    list_filter_submit = True
    # Evita un COUNT(*) sin filtros por cada listado en tablas grandes de PRD.
    show_full_result_count = False
    # El historial suma los eventos de auditlog al log del admin de Django.
    object_history_template = "admin/sisoc/object_history.html"

    def history_view(self, request, object_id, extra_context=None):
        extra_context = {
            **(extra_context or {}),
            "auditlog_historial": historial_auditlog(self.model, object_id),
        }
        return super().history_view(request, object_id, extra_context)


class SisocTabularInline(TabularInline):
    """Inline tabular con estilo Unfold."""


class SisocStackedInline(StackedInline):
    """Inline apilado con estilo Unfold."""
