"""Web API (G1 v1) of the mass mailing screens (CM01.01 and CM01.02).

``/api/web/comedores/`` is published by the Comedores backend. After the G1 gate
the native rules apply unchanged: every endpoint needs ``is_admin`` (403
without a message) and any admin reads or resumes any batch (the native
asymmetry: «Últimos lotes de mailing» shows only the own ones).

The upload runs ``MailingUploadView`` itself (form, workbook validation and
``create_mailing_job``) and the resume runs ``MailingJobResumeView``. Nothing
here sends mail or starts a worker: a valid upload only queues a ``pending``
batch for the existing ``process_mailing_jobs`` command. The reads never claim
a batch nor touch ``last_activity_at``. The XLSX template stays a native GET.
"""

from django.core.paginator import Paginator
from django.template.defaultfilters import date as formato_fecha
from django.template.defaultfilters import truncatechars
from django.urls import reverse
from django.utils import timezone
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import PermissionDenied
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from comunicados.permissions import is_admin
from comunicados.services_mailing_jobs import (
    can_resume_mailing_job,
    get_mailing_job_or_404,
)
from comunicados.views import MailingJobResumeView, MailingUploadView
from comunicados.web_api_serializers import pending_messages
from core.web_gate import WebGatePermission

FECHA = "d/m/Y H:i"
VACIO = "-"
FIELD_TYPES = {"asunto": "text", "cuerpo": "textarea", "archivo": "file"}
PAGE_SIZE = 50


def _fecha(valor):
    return formato_fecha(timezone.localtime(valor), FECHA)


def _campo(form, nombre):
    campo = form.fields[nombre]
    valor = form[nombre].value()
    return {
        "name": nombre,
        "label": str(campo.label),
        "help_text": str(campo.help_text or ""),
        "required": campo.required,
        "type": FIELD_TYPES.get(nombre, "files"),
        "accept": campo.widget.attrs.get("accept", ""),
        "value": valor if isinstance(valor, str) else "",
        "errors": [str(e) for e in form.errors.get(nombre, [])],
    }


def _reciente(job):
    return {
        "id": job.id,
        "requested_at": _fecha(job.requested_at),
        "status": job.status,
        "asunto_corto": truncatechars(job.asunto, 30),
        "last_successful_mail": job.last_successful_mail,
        "last_successful_row": job.last_successful_row,
        "last_error_message": job.last_error_message,
        "detail_url": reverse("comunicados_mailing_detalle", args=[job.id]),
    }


def _formulario(contexto, request):
    form = contexto["form"]
    return {
        "form_title": contexto["form_title"],
        "fields": [_campo(form, nombre) for nombre in form.fields],
        "template_download_url": contexto["template_download_url"],
        "gestion_url": reverse("comunicados_gestion"),
        "recent_jobs": [_reciente(job) for job in contexto["recent_jobs"]],
        "messages": pending_messages(request),
    }


class _MailingView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission]
    renderer_classes = [JSONRenderer]
    http_method_names = ["get", "head"]

    @staticmethod
    def native(view_class, request, **kwargs):
        vista = view_class()
        vista.setup(request._request, **kwargs)  # pylint: disable=protected-access
        return vista

    @staticmethod
    def require_admin(request):
        # The native ``dispatch`` raises ``PermissionDenied`` without a message.
        if not is_admin(request.user):
            raise PermissionDenied()


class MailingFormWebView(_MailingView):
    """``GET/POST .../comunicados/mailing/``: ``mailing_form.html``."""

    http_method_names = ["get", "post"]

    def get(self, request):
        vista = self.native(MailingUploadView, request)
        # pylint: disable-next=protected-access
        respuesta = vista.dispatch(request._request)
        return Response(_formulario(respuesta.context_data, request))

    def post(self, request):
        # ``Request.content_type`` keeps the multipart boundary; Django strips it.
        # pylint: disable-next=protected-access
        if request._request.content_type != "multipart/form-data":
            self.require_admin(request)
            return Response({"detail": "Formato de solicitud no admitido."}, status=415)
        vista = self.native(MailingUploadView, request)
        # pylint: disable-next=protected-access
        respuesta = vista.dispatch(request._request)
        if respuesta.status_code == 302:
            return Response({"ok": True, "redirect": respuesta["Location"]})
        return Response(_formulario(respuesta.context_data, request), status=400)


def _ultimo(mail, fila):
    return {"mail": mail, "fila": fila}


class MailingJobWebView(_MailingView):
    """``GET .../comunicados/mailing/jobs/<pk>/?page=``: ``mailing_job_detail.html``."""

    def get(self, request, pk):
        self.require_admin(request)
        job = get_mailing_job_or_404(job_id=pk)
        pagina = Paginator(job.rows.order_by("fila", "id"), PAGE_SIZE).get_page(
            request.GET.get("page")
        )
        return Response(
            {
                "job": {
                    "id": job.id,
                    "original_filename": job.original_filename,
                    "requested_at": _fecha(job.requested_at),
                    "status": job.status,
                    "asunto": job.asunto,
                    "cuerpo": job.cuerpo,
                    "resume_count": job.resume_count,
                    "total_rows": job.total_rows,
                    "processed_rows": job.processed_rows,
                    "sent_rows": job.sent_rows,
                    "rejected_rows": job.rejected_rows,
                    "last_successful": _ultimo(
                        job.last_successful_mail, job.last_successful_row
                    ),
                    "last_attempted": _ultimo(
                        job.last_attempted_mail, job.last_attempted_row
                    ),
                    "last_error_message": job.last_error_message,
                    "last_error_at": (
                        _fecha(job.last_error_at) if job.last_error_at else None
                    ),
                    "attachments": [
                        {"nombre_original": a.nombre_original, "url": a.archivo.url}
                        for a in job.attachments.all()
                    ],
                },
                "rows": [
                    {
                        "fila": fila.fila,
                        "status": fila.status,
                        "mail_destino": fila.mail_destino or VACIO,
                        "attempts": fila.attempts,
                        "mensaje": fila.mensaje or VACIO,
                    }
                    for fila in pagina
                ],
                "page": {
                    "number": pagina.number,
                    "num_pages": pagina.paginator.num_pages,
                    "previous": (
                        pagina.previous_page_number() if pagina.has_previous() else None
                    ),
                    "next": pagina.next_page_number() if pagina.has_next() else None,
                },
                "is_resume_available": can_resume_mailing_job(job),
                "resume_url": reverse("comunicados_mailing_reanudar", args=[job.id]),
                "refresh_url": reverse("comunicados_mailing_detalle", args=[job.id]),
                "upload_url": reverse("comunicados_mailing"),
                "gestion_url": reverse("comunicados_gestion"),
                "messages": pending_messages(request),
            }
        )


class MailingResumeWebView(_MailingView):
    """``POST .../comunicados/mailing/jobs/<pk>/resume/``: ``MailingJobResumeView``.

    Also a 200 when the batch is not failed: the native error stays queued.
    """

    http_method_names = ["post"]

    def post(self, request, pk):
        vista = self.native(MailingJobResumeView, request, pk=pk)
        # pylint: disable-next=protected-access
        respuesta = vista.post(request._request, pk=pk)
        return Response({"ok": True, "redirect": respuesta["Location"]})
