"""Importación masiva de ciudadanos para React (C01.01 y C01.02; G1 v1).

``/api/web/ciudadanos/importacion-masiva/`` lo sirve el core y corre las vistas
nativas con su ``dispatch``: permiso ``ciudadanos.add_ciudadano`` (403) y, en el lote,
el 404 del lote inexistente. El ``GET`` proyecta lo que imprimen los templates; el
``POST`` multipart de la carga crea el lote con ``form_valid`` (la API no llama a
RENAPER: el lote lo procesa el worker) y el de ``reanudar`` corre la vista nativa.
La plantilla y el Excel del lote son descargas nativas y no pasan por esta API.
"""

from django.template.defaultfilters import date as formato_fecha
from django.urls import reverse
from django.utils import timezone
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from ciudadanos.views_importacion_masiva import (
    CiudadanosImportJobDetailView,
    CiudadanosImportJobResumeView,
    CiudadanosImportUploadView,
)
from ciudadanos.web_ficha import pending_messages
from ciudadanos.web_gestion_despacho import VistaNativaWebView

VACIO = "-"
FECHA = "d/m/Y H:i"


def _fecha(valor):
    return formato_fecha(timezone.localtime(valor), FECHA)


def _lote_reciente(job):
    return {
        "id": job.id,
        "fecha_texto": _fecha(job.requested_at),
        "usuario_texto": str(job.requested_by) or VACIO,
        "estado": job.status,
        "creados": job.created_rows,
        "existentes": job.existing_rows,
        "fallidos": job.failed_rows,
        "pendientes": job.pending_rows,
        "detalle_url": reverse("ciudadanos_importacion_masiva_lote", args=[job.id]),
    }


def _formulario(contexto, request):
    form = contexto["form"]
    campo = form["archivo"]
    return {
        "campo": {
            "label": str(campo.label),
            "accept": campo.field.widget.attrs["accept"],
        },
        "errors": {
            nombre: [str(e) for e in errores] for nombre, errores in form.errors.items()
        },
        "plantilla_url": contexto["template_download_url"],
        "volver_url": contexto["volver_url"],
        "lotes": [_lote_reciente(job) for job in contexto["recent_jobs"]],
        "messages": pending_messages(request),
    }


class CiudadanoImportacionWebView(VistaNativaWebView):
    """``GET/POST /api/web/ciudadanos/importacion-masiva/``."""

    parser_classes = [MultiPartParser, FormParser]
    http_method_names = ["get", "post"]
    vista_nativa = CiudadanosImportUploadView

    def get(self, request):
        respuesta = self.despachar(request)
        return Response(_formulario(respuesta.context_data, request))

    def post(self, request):
        respuesta = self.despachar(request)
        if respuesta.status_code != 302:
            return Response(_formulario(respuesta.context_data, request), status=400)
        return Response({"ok": True, "redirect": respuesta["Location"]})


def _fila(fila):
    return {
        "fila": fila.fila,
        "documento": fila.documento_raw or VACIO,
        "dni": fila.dni or VACIO,
        "sexo": fila.sexo or VACIO,
        "estado": fila.status,
        "sexos_intentados": fila.sexos_intentados or VACIO,
        "intentos": fila.attempts,
        "mensaje": fila.mensaje or VACIO,
        "error_tipo": fila.error_type,
        "ciudadano_url": (
            reverse("ciudadanos_ver", args=[fila.ciudadano_id])
            if fila.ciudadano_id
            else None
        ),
    }


def _ultimo(documento, fila):
    return {"documento": documento, "fila_texto": str(fila or VACIO)}


def _lote(contexto, request):
    job = contexto["job"]
    pagina = contexto["rows_page"]
    return {
        "id": job.id,
        "archivo": job.original_filename,
        "fecha_texto": _fecha(job.requested_at),
        "estado": job.status,
        "reanudaciones": job.resume_count,
        "totales": job.total_rows,
        "procesadas": job.processed_rows,
        "creados": job.created_rows,
        "existentes": job.existing_rows,
        "fallidos": job.failed_rows,
        "pendientes": job.pending_rows,
        "ultimo_correcto": _ultimo(
            job.last_successful_documento, job.last_successful_row
        ),
        "ultimo_intentado": _ultimo(
            job.last_attempted_documento, job.last_attempted_row
        ),
        "error_mensaje": job.last_error_message,
        "error_tipo": job.last_error_type,
        "puede_reanudar": contexto["can_resume"],
        "filas": [_fila(fila) for fila in pagina],
        "paginacion": {
            "number": pagina.number,
            "num_pages": pagina.paginator.num_pages,
            "previous": pagina.has_previous(),
            "next": pagina.has_next(),
        },
        "volver_url": contexto["volver_url"],
        "lista_url": reverse("ciudadanos"),
        "lote_url": reverse("ciudadanos_importacion_masiva_lote", args=[job.id]),
        "exportar_url": reverse(
            "ciudadanos_importacion_masiva_lote_exportar", args=[job.id]
        ),
        "reanudar_url": reverse(
            "ciudadanos_importacion_masiva_reanudar", args=[job.id]
        ),
        "messages": pending_messages(request),
    }


class CiudadanoImportacionLoteWebView(VistaNativaWebView):
    """``GET /api/web/ciudadanos/importacion-masiva/lotes/<pk>/?page=``."""

    http_method_names = ["get"]
    vista_nativa = CiudadanosImportJobDetailView

    def get(self, request, pk):
        respuesta = self.despachar(request, pk=pk)
        return Response(_lote(respuesta.context_data, request))


class CiudadanoImportacionReanudarWebView(VistaNativaWebView):
    """``POST .../lotes/<pk>/reanudar/``: corre la vista nativa y vuelve al lote."""

    http_method_names = ["post"]
    vista_nativa = CiudadanosImportJobResumeView

    def post(self, request, pk):
        respuesta = self.despachar(request, pk=pk)
        return Response({"ok": True, "redirect": respuesta["Location"]})
