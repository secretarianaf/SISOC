"""Session transport over the native bulk-credentials job views and services.

The native views stay the only writers: the upload Form enqueues the job with
``create_bulk_credentials_job`` and resume uses the native view. Reading a job
never starts or retries it, and no password reaches the DTO.
"""

from django.http import JsonResponse
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie

from usuarios.views import (
    BulkCredentialsJobDetailView,
    BulkCredentialsJobResumeView,
    BulkCredentialsUploadView,
)
from usuarios.web_context import build_legacy_presentation
from usuarios.web_user_import import (
    WebJobTransportMixin,
    format_timestamp,
    pending_messages,
)


def _page_payload(page_obj):
    return {
        "number": page_obj.number,
        "num_pages": page_obj.paginator.num_pages,
        "previous": (
            page_obj.previous_page_number() if page_obj.has_previous() else None
        ),
        "next": page_obj.next_page_number() if page_obj.has_next() else None,
    }


@method_decorator(ensure_csrf_cookie, name="dispatch")
@method_decorator(csrf_protect, name="dispatch")
class WebBulkCredentialsView(WebJobTransportMixin, BulkCredentialsUploadView):
    """Upload form and own recent history; a valid POST only enqueues the job.

    ``form_valid`` stays native (service call, message and redirect); only the
    rendering of the unbound and invalid form becomes JSON.
    """

    post_content_type = "multipart/form-data"

    def get(self, request, *args, **kwargs):
        return self._payload(self.get_form())

    def form_invalid(self, form):
        return self._payload(form, status=400)

    def _payload(self, form, status=200):
        context = self.get_context_data(form=form)
        tipo, archivo = form.fields["tipo_envio"], form.fields["archivo"]
        return JsonResponse(
            {
                "form_title": context["form_title"],
                "fields": [
                    {
                        "name": "tipo_envio",
                        "label": str(tipo.label),
                        "required": tipo.required,
                        "help_text": str(tipo.help_text),
                        "choices": [
                            {"value": value, "label": str(label)}
                            for value, label in tipo.choices
                        ],
                    },
                    {
                        "name": "archivo",
                        "label": str(archivo.label),
                        "required": archivo.required,
                        "help_text": str(archivo.help_text),
                        "accept": archivo.widget.attrs.get("accept", ""),
                    },
                ],
                "values": {"tipo_envio": str(form["tipo_envio"].value() or "")},
                "errors": form.errors.get_json_data() if form.is_bound else {},
                "template_download_url": context["template_download_url"],
                "send_type_options": [
                    {
                        "key": option["key"],
                        "label": str(option["label"]),
                        "description": str(option["description"]),
                        "required_columns": [
                            str(column) for column in option["required_columns"]
                        ],
                    }
                    for option in context["send_type_options"]
                ],
                "recent_jobs": [
                    {
                        "id": job.pk,
                        "requested_at": format_timestamp(job.requested_at),
                        "status": job.status,
                        "send_type": job.send_type.upper(),
                        "last_successful_username": job.last_successful_username,
                        "last_successful_row": job.last_successful_row,
                        "last_error_message": job.last_error_message,
                        "detail_url": reverse(
                            "usuarios_credenciales_masivas_detalle",
                            kwargs={"pk": job.pk},
                        ),
                    }
                    for job in context["recent_jobs"]
                ],
                "messages": pending_messages(self.request),
                "presentation": build_legacy_presentation(self.request),
            },
            status=status,
        )


@method_decorator(ensure_csrf_cookie, name="dispatch")
@method_decorator(csrf_protect, name="dispatch")
class WebBulkCredentialsJobView(WebJobTransportMixin, BulkCredentialsJobDetailView):
    """Native detail context (50 rows by row and id) rendered as JSON."""

    http_method_names = ["get", "head", "options"]

    def render_to_response(self, context):
        job, page_obj = context["job"], context["page_obj"]
        return JsonResponse(
            {
                "job": {
                    "id": job.pk,
                    "original_filename": job.original_filename,
                    "requested_at": format_timestamp(job.requested_at),
                    "status": job.status,
                    "send_type": job.send_type.upper(),
                    "resume_count": job.resume_count,
                    "total_rows": job.total_rows,
                    "processed_rows": job.processed_rows,
                    "sent_rows": job.sent_rows,
                    "rejected_rows": job.rejected_rows,
                    "last_successful_username": job.last_successful_username,
                    "last_successful_row": job.last_successful_row,
                    "last_attempted_username": job.last_attempted_username,
                    "last_attempted_row": job.last_attempted_row,
                    "last_error_message": job.last_error_message,
                    "last_error_at": format_timestamp(job.last_error_at),
                },
                "rows": [
                    {
                        "id": row.pk,
                        "fila": row.fila,
                        "usuario": row.usuario,
                        "status": row.status,
                        "mail_destino": row.mail_destino,
                        "attempts": row.attempts,
                        "mensaje": row.mensaje,
                    }
                    for row in page_obj
                ],
                "page": _page_payload(page_obj),
                "is_resume_available": context["is_resume_available"],
                "upload_url": context["upload_url"],
                "messages": pending_messages(self.request),
                "presentation": build_legacy_presentation(self.request),
            }
        )


@method_decorator(csrf_protect, name="dispatch")
class WebBulkCredentialsJobResumeView(
    WebJobTransportMixin, BulkCredentialsJobResumeView
):
    """Native resume: only ``failed`` returns to ``pending``; never auto-retried."""

    http_method_names = ["post", "options"]
