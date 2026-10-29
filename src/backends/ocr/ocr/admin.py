from django.contrib import admin
from unfold.contrib.filters.admin import ChoicesDropdownFilter, RangeDateTimeFilter

from core.admin_base import SisocModelAdmin, SisocTabularInline
from ocr.models import OCRJob, OCRJobDocument


class OCRJobDocumentInline(SisocTabularInline):
    model = OCRJobDocument
    extra = 0
    readonly_fields = (
        "original_filename",
        "file_size",
        "status",
        "page_count",
        "error_message",
        "processed_at",
    )
    fields = (
        "original_filename",
        "file_size",
        "status",
        "page_count",
        "error_message",
        "processed_at",
    )
    can_delete = False


@admin.register(OCRJob)
class OCRJobAdmin(SisocModelAdmin):
    list_display = (
        "id",
        "requested_by",
        "status",
        "total_documents",
        "processed_documents",
        "failed_documents",
        "requested_at",
        "finished_at",
    )
    # Sin operaciones: reanudar o reintentar un lote no tiene service propio
    # (pendiente, issue #2789).
    list_filter = (
        ("status", ChoicesDropdownFilter),
        ("requested_at", RangeDateTimeFilter),
        ("finished_at", RangeDateTimeFilter),
    )
    list_select_related = ("requested_by",)
    search_fields = ("=id", "requested_by__username", "last_error_message")
    readonly_fields = (
        "requested_by",
        "status",
        "total_documents",
        "processed_documents",
        "failed_documents",
        "last_error_message",
        "requested_at",
        "started_at",
        "finished_at",
        "last_activity_at",
    )
    inlines = [OCRJobDocumentInline]


@admin.register(OCRJobDocument)
class OCRJobDocumentAdmin(SisocModelAdmin):
    list_display = (
        "id",
        "job",
        "original_filename",
        "status",
        "page_count",
        "processed_at",
    )
    list_filter = (
        ("status", ChoicesDropdownFilter),
        ("processed_at", RangeDateTimeFilter),
    )
    list_select_related = ("job",)
    search_fields = ("=id", "=job__id", "original_filename", "error_message")
    readonly_fields = (
        "job",
        "original_filename",
        "file_size",
        "status",
        "page_count",
        "error_message",
        "processed_at",
    )
