"""JSON projections of the OCR screens served by React (``ocr.web_api_views``).

Each function returns what ``ocr_upload.html`` and ``ocr_job_detail.html``
print: dates with the template formats in local time, sizes with
``filesizeformat`` and URLs from ``reverse``. Nothing here queries or
recalculates domain data.
"""

from datetime import datetime

from django.contrib import messages
from django.template.defaultfilters import filesizeformat
from django.urls import reverse
from django.utils import dateformat, timezone

MESSAGE_LEVELS = {
    messages.DEBUG: "info",
    messages.INFO: "info",
    messages.SUCCESS: "success",
    messages.WARNING: "warning",
    messages.ERROR: "error",
}


def _local(value, fmt):
    if not value:
        return ""
    if isinstance(value, datetime) and timezone.is_aware(value):
        value = timezone.localtime(value)
    return dateformat.format(value, fmt)


def fecha_hora(value):
    """``value|date:"d/m/Y H:i"``."""
    return _local(value, "d/m/Y H:i")


def fecha_hora_segundos(value):
    """``value|date:"d/m/Y H:i:s"``."""
    return _local(value, "d/m/Y H:i:s")


def pending_messages(request):
    """Consume the queued Django messages exactly as the native layout would."""
    return [
        {"message": str(m), "level": MESSAGE_LEVELS.get(m.level, "info")}
        for m in messages.get_messages(request)
    ]


def lote_resumen(job):
    """One row of «Últimos lotes»."""
    return {
        "id": job.pk,
        "requested_at": fecha_hora(job.requested_at),
        "status": job.status,
        "processed_documents": job.processed_documents,
        "total_documents": job.total_documents,
        "detail_url": reverse("ocr_job_detail", kwargs={"pk": job.pk}),
    }


def documento(doc):
    """One card of «Resultados por archivo»; the link only where the button shows."""
    descargable = doc.status == "completed" and bool(doc.extracted_text)
    return {
        "id": doc.pk,
        "original_filename": doc.original_filename,
        "status": doc.status,
        "page_count": doc.page_count,
        "file_size_label": filesizeformat(doc.file_size) if doc.file_size else "",
        "extracted_text": doc.extracted_text,
        "error_message": doc.error_message,
        "processed_at": fecha_hora_segundos(doc.processed_at),
        "download_url": (
            reverse("ocr_document_download", kwargs={"doc_pk": doc.pk})
            if descargable
            else None
        ),
    }


def lote_detalle(job, documents):
    return {
        "id": job.pk,
        "requested_at": fecha_hora(job.requested_at),
        "status": job.status,
        "total_documents": job.total_documents,
        "processed_documents": job.processed_documents,
        "failed_documents": job.failed_documents,
        "last_error_message": job.last_error_message,
        "options": {
            "preprocess": job.opt_preprocess,
            "pdf_text_layer": job.opt_pdf_text_layer,
            "auto_orient": job.opt_auto_orient,
        },
        "documents": [documento(doc) for doc in documents],
        "upload_url": reverse("ocr_upload"),
    }
