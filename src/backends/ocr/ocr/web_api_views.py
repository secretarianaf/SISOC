"""Web API (G1 v1) of the OCR upload and batch screens: ``/api/web/ocr/``.

Same access as the native routes of ``ocr/urls.py``: G1 first
(``WebGatePermission``), then the rule of ``AdminRequiredMixin`` (superuser or
``ocr.use_ocr``). Reads reuse the native view's context and lookup; the upload
shares the native form and ``create_ocr_job``. Processing stays on the OCR
worker; the text download stays the native GET
``ocr/documentos/<doc_pk>/descargar/``, which the screen only links.
"""

from django.conf import settings
from django.contrib import messages
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import BasePermission
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from core.web_gate import WebGatePermission
from ocr import web_api_serializers as proyectar
from ocr.forms import OCRUploadForm
from ocr.models import OCRJob
from ocr.views import OCR_PERMISSION, OCRUploadView
from ocr.services_ocr_jobs import create_ocr_job

OPTION_FIELDS = ("opt_preprocess", "opt_pdf_text_layer", "opt_auto_orient")


class OcrPermission(BasePermission):
    """``AdminRequiredMixin.test_func`` with ``required_permissions = (ocr.use_ocr,)``."""

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (user.is_superuser or user.has_perm(OCR_PERMISSION))
        )


class OcrWebView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, OcrPermission]
    renderer_classes = [JSONRenderer]


def errors_payload(form):
    """Form errors as the native page prints them: field errors, then non-field ones."""
    return {
        "errors": {
            name: [str(error) for error in errors]
            for name, errors in form.errors.items()
        }
    }


class OcrUploadWebView(OcrWebView):
    """``GET /api/web/ocr/carga/``: the data of ``ocr_upload.html`` (``OCRUploadView``)."""

    http_method_names = ["get", "head"]

    def get(self, request):
        django_request = request._request  # pylint: disable=protected-access
        vista = OCRUploadView()
        vista.setup(django_request)
        form = OCRUploadForm()
        context = vista._context(form)  # pylint: disable=protected-access
        allowed = getattr(
            settings, "OCR_ALLOWED_EXTENSIONS", {"jpg", "jpeg", "png", "pdf"}
        )
        return Response(
            {
                "max_file_size_mb": context["max_file_size_mb"],
                "allowed_extensions": sorted(allowed),
                "options": [
                    {
                        "name": name,
                        "label": form.fields[name].label,
                        "help_text": form.fields[name].help_text,
                        "initial": bool(form.fields[name].initial),
                    }
                    for name in OPTION_FIELDS
                ],
                "recent_jobs": [
                    proyectar.lote_resumen(job) for job in context["recent_jobs"]
                ],
                "messages": proyectar.pending_messages(django_request),
            }
        )


class OcrLoteCrearWebView(OcrWebView):
    """``POST /api/web/ocr/lotes/``: ``OCRUploadView.post`` with a JSON answer."""

    http_method_names = ["post"]
    parser_classes = [MultiPartParser]

    def post(self, request):
        form = OCRUploadForm(request.POST, request.FILES)
        if not form.is_valid():
            return Response(errors_payload(form), status=400)
        job = create_ocr_job(
            requested_by=request.user,
            files=form.cleaned_data["archivos"],
            options=form.get_options(),
        )
        message = (
            f"Lote OCR #{job.id} creado con {job.total_documents} archivo(s). "
            "El procesamiento se ejecuta en segundo plano."
        )
        # The detail screen shows it as the native layout shows ``messages``.
        messages.success(request._request, message)  # pylint: disable=protected-access
        return Response(
            {
                "id": job.pk,
                "message": message,
                "detail_url": reverse("ocr_job_detail", kwargs={"pk": job.pk}),
            },
            status=201,
        )


class OcrLoteDetailWebView(OcrWebView):
    """``GET /api/web/ocr/lotes/<pk>/``: ``OCRJobDetailView`` (own batch; any for a superuser)."""

    http_method_names = ["get", "head"]

    def get(self, request, pk):
        filters = {"pk": pk}
        if not request.user.is_superuser:
            filters["requested_by"] = request.user
        try:
            job = get_object_or_404(OCRJob, **filters)
        except Http404 as exc:
            raise NotFound() from exc
        payload = proyectar.lote_detalle(job, job.documents.order_by("id"))
        payload["messages"] = proyectar.pending_messages(
            request._request  # pylint: disable=protected-access
        )
        return Response(payload)
