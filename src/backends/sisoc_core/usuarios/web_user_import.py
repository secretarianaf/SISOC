"""Session transport over the native user-import job views and services.

Importing only enqueues a job: the native Form and ``create_user_import_job``
stay the only writers, and reading a job never starts or retries it.
"""

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.http import HttpResponseRedirect, JsonResponse
from django.template.defaultfilters import date as format_date
from django.urls import reverse
from django.utils.cache import patch_cache_control, patch_vary_headers
from django.utils.decorators import method_decorator
from django.utils.timezone import localtime
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie

from usuarios.forms import UserImportForm
from usuarios.services_user_import import create_user_import_job
from usuarios.services_user_import_jobs import (
    can_resume_user_import_job,
    get_user_import_job_or_404,
)
from usuarios.views_user_import import (
    UserImportJobCreateView,
    UserImportJobDetailView,
    UserImportJobResumeView,
)
from usuarios.web_context import build_legacy_presentation
from usuarios.web_session import resolve_web_access
from users.models import UserImportJobRow

_MESSAGE_LEVELS = {
    messages.ERROR: "error",
    messages.WARNING: "warning",
    messages.SUCCESS: "success",
}


def format_timestamp(value):
    """Same local time, filter and format the native templates use (``d/m/Y H:i``).

    Templates convert aware datetimes to the current time zone before the
    ``date`` filter runs; calling the filter directly must do it explicitly.
    """
    return format_date(localtime(value), "d/m/Y H:i") if value else ""


def pending_messages(request):
    """Consume queued Django messages exactly as the native page would."""
    return [
        {
            "message": str(message),
            "level": _MESSAGE_LEVELS.get(message.level, "info"),
        }
        for message in messages.get_messages(request)
    ]


class WebJobTransportMixin:
    """Prerequisites and action permissions ahead of any job lookup.

    ``required_permissions`` mirrors the native URL guard; a superuser keeps
    the existing bypass through ``has_perms``. A native redirect becomes a
    JSON destination; the queued message waits for the next GET.
    """

    http_method_names = ["get", "head", "post", "options"]
    post_content_type = "application/x-www-form-urlencoded"

    def dispatch(self, request, *args, **kwargs):
        access = resolve_web_access(request)
        if access.state != "ready":
            response = JsonResponse(
                {
                    "detail": "Debe completar el requisito de acceso correspondiente.",
                    "state": access.state,
                    "required_action_url": access.required_action_url,
                },
                status=401 if access.state == "unauthenticated" else 403,
            )
        elif not request.user.has_perms(self.required_permissions):
            response = JsonResponse(
                {"detail": "No tiene permisos para esta acción."}, status=403
            )
        elif request.method.lower() not in self.http_method_names:
            response = self.http_method_not_allowed(request, *args, **kwargs)
        elif (
            request.method == "POST" and request.content_type != self.post_content_type
        ):
            response = JsonResponse(
                {"detail": "Formato de solicitud no admitido."}, status=415
            )
        else:
            response = super().dispatch(request, *args, **kwargs)
            if response.status_code == 302:
                converted = JsonResponse({"ok": True, "redirect": response["Location"]})
                converted.cookies = response.cookies
                response = converted
        patch_cache_control(response, private=True, no_store=True)
        patch_vary_headers(response, ("Cookie",))
        return response


def _form_payload(view, form, status=200):
    context = view._build_context(form=form)  # pylint: disable=protected-access
    archivo = form.fields["archivo"]
    fields = [
        {
            "name": "archivo",
            "label": str(archivo.label),
            "required": archivo.required,
            "help_text": str(archivo.help_text),
            "accept": archivo.widget.attrs.get("accept", ""),
        }
    ]
    for name in ("enviar_credenciales", "es_pwa"):
        field = form.fields[name]
        fields.append(
            {
                "name": name,
                "label": str(field.label),
                "required": field.required,
                "help_text": str(field.help_text),
            }
        )
    return JsonResponse(
        {
            "fields": fields,
            "initial": {
                name: bool(form[name].value())
                for name in ("enviar_credenciales", "es_pwa")
            },
            "errors": form.errors.get_json_data() if form.is_bound else {},
            "template_download_url": context["template_download_url"],
            "recent_jobs": [
                {
                    "id": job.pk,
                    "requested_at": format_timestamp(job.requested_at),
                    "status": job.status,
                    "created_rows": job.created_rows,
                    "skipped_rows": job.skipped_rows,
                    "failed_rows": job.failed_rows,
                    "detail_url": reverse(
                        "usuarios_importar_detalle", kwargs={"pk": job.pk}
                    ),
                }
                for job in context["recent_jobs"]
            ],
            "messages": pending_messages(view.request),
            "presentation": build_legacy_presentation(view.request),
        },
        status=status,
    )


@method_decorator(ensure_csrf_cookie, name="dispatch")
@method_decorator(csrf_protect, name="dispatch")
class WebUserImportView(WebJobTransportMixin, UserImportJobCreateView):
    """Upload form and own recent history; a valid POST only enqueues the job."""

    post_content_type = "multipart/form-data"

    def get(self, request, *args, **kwargs):
        return _form_payload(self, UserImportForm())

    def post(self, request, *args, **kwargs):
        form = UserImportForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                job = create_user_import_job(
                    uploaded_file=form.cleaned_data["archivo"],
                    requested_by=request.user,
                    send_credentials=bool(form.cleaned_data["enviar_credenciales"]),
                    is_pwa_import=bool(form.cleaned_data["es_pwa"]),
                )
            except ValidationError as exc:
                form.add_error("archivo", " ".join(exc.messages))
            else:
                messages.success(
                    request,
                    (
                        f"Lote de importacion creado con {job.total_rows} filas. "
                        "El procesamiento continua en background. "
                        "Puede seguir el estado desde el detalle del lote."
                    ),
                )
                return HttpResponseRedirect(
                    reverse("usuarios_importar_detalle", kwargs={"pk": job.pk})
                )
        return _form_payload(self, form, status=400)


@method_decorator(ensure_csrf_cookie, name="dispatch")
@method_decorator(csrf_protect, name="dispatch")
class WebUserImportJobView(WebJobTransportMixin, UserImportJobDetailView):
    """Read-only job state, 50 rows per page ordered by row and id."""

    http_method_names = ["get", "head", "options"]

    def get(self, request, *args, **kwargs):
        job = get_user_import_job_or_404(job_id=kwargs["pk"])
        rows_qs = job.rows.order_by("fila", "id")
        status_filter = request.GET.get("estado")
        if status_filter:
            rows_qs = rows_qs.filter(status=status_filter)
        page_obj = Paginator(rows_qs, self.paginate_by).get_page(
            request.GET.get("page")
        )
        has_csv = job.rows.filter(
            status=UserImportJobRow.Status.CREATED, created_user__isnull=False
        ).exists()
        return JsonResponse(
            {
                "job": {
                    "id": job.pk,
                    "original_filename": job.original_filename,
                    "requested_at": format_timestamp(job.requested_at),
                    "status": job.status,
                    "send_credentials": job.send_credentials,
                    "resume_count": job.resume_count,
                    "total_rows": job.total_rows,
                    "processed_rows": job.processed_rows,
                    "created_rows": job.created_rows,
                    "skipped_rows": job.skipped_rows,
                    "failed_rows": job.failed_rows,
                    "last_error_message": job.last_error_message,
                    "last_error_at": format_timestamp(job.last_error_at),
                },
                "rows": [
                    {
                        "id": row.pk,
                        "fila": row.fila,
                        "nombre": row.nombre,
                        "apellido": row.apellido,
                        "email": row.email,
                        "status": row.status,
                        "attempts": row.attempts,
                        "mensaje": row.mensaje,
                    }
                    for row in page_obj
                ],
                "page": {
                    "number": page_obj.number,
                    "num_pages": page_obj.paginator.num_pages,
                    "previous": (
                        page_obj.previous_page_number()
                        if page_obj.has_previous()
                        else None
                    ),
                    "next": (
                        page_obj.next_page_number() if page_obj.has_next() else None
                    ),
                },
                "status_filter": status_filter or "",
                "is_resume_available": can_resume_user_import_job(job),
                "csv_url": (
                    reverse("usuarios_importar_descargar_csv", kwargs={"pk": job.pk})
                    if has_csv
                    else None
                ),
                "upload_url": reverse("usuarios_importar"),
                "messages": pending_messages(request),
                "presentation": build_legacy_presentation(request),
            }
        )


@method_decorator(csrf_protect, name="dispatch")
class WebUserImportJobResumeView(WebJobTransportMixin, UserImportJobResumeView):
    """Native resume: only ``failed`` returns to ``pending``; never auto-retried."""

    http_method_names = ["post", "options"]
