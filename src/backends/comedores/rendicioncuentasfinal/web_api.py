"""Web API (G1 v1) of the final rendición de cuentas screens (RF01.01).

``/api/web/comedores/`` is published by the Comedores backend (``url_prefixes``
in ``src/backends/config/backends.json``). In a split deploy the core checks the
session and the web prerequisites and signs each request; the runtime only
serves requests its ``WebGateMiddleware`` verified. In the monolith
``WebGatePermission`` evaluates the same policy locally. After that the web
endpoints require ``view_rendicioncuentasfinal`` (the permission the native
screens already demand), see
``docs/registro/decisiones/2026-11-10-2785-brechas-acceso-conservadas.md``.

The detail endpoint runs ``RendicionCuentasFinalDetailView`` itself (the
comedor lookup with its 404, the ``get_or_create`` of the rendición, the
documents and the history); the list endpoint runs the native
``RendicionCuentasFinalService.filter_documentos_por_area`` through
``DocumentosRendicionCuentasFinalListView`` and the AJAX paginator. This module
only projects those results to JSON; React never formats dates or states.
"""

from django.contrib import messages
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import date as date_filter
from django.template.defaultfilters import slugify
from django.urls import reverse
from django.utils import timezone
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import BasePermission
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

# The exact predicate of ``permissions_any_required``, the native URL guard.
from core.decorators import _has_any_permissions
from core.pagination import build_compact_page_range
from core.web_gate import WebGatePermission
from historial.services.historial_service import HistorialService
from rendicioncuentasfinal.models import (
    DocumentoRendicionFinal,
    EstadoDocumentoRendicionFinal,
    RendicionCuentasFinal,
)
from rendicioncuentasfinal.rendicion_cuentas_final_service import (
    RendicionCuentasFinalService,
)
from rendicioncuentasfinal.urls import _RENDICION_FINAL_PERM
from rendicioncuentasfinal.views import (
    DocumentosRendicionCuentasFinalListView,
    RendicionCuentasFinalDetailView,
)

PAGE_SIZE = 25
DATE_FORMAT = "d/m/Y H:i"
EN_ANALISIS = "En análisis"
MESSAGE_LEVELS = {
    messages.DEBUG: "info",
    messages.INFO: "info",
    messages.SUCCESS: "success",
    messages.WARNING: "warning",
    messages.ERROR: "error",
}


class RendicionFinalAccess(BasePermission):
    """Same rule as the native ``permissions_any_required(_RENDICION_FINAL_PERM)``."""

    def has_permission(self, request, view):
        return _has_any_permissions(request.user, _RENDICION_FINAL_PERM)


def fecha(value):
    """``|date:"d/m/Y H:i"`` of the native templates (local time); ``None`` for ``|default:"-"``."""
    if not value:
        return None
    if timezone.is_aware(value):
        value = timezone.localtime(value)
    return date_filter(value, DATE_FORMAT)


def archivo_url(documento):
    """``documento.documento.url``: the native storage URL, ``None`` without a file."""
    return documento.documento.url if documento.documento else None


def pending_messages(request):
    """Consume queued Django messages exactly as the native page would."""
    return [
        {"message": str(m), "level": MESSAGE_LEVELS.get(m.level, "info")}
        for m in messages.get_messages(request)
    ]


class RendicionFinalWebView(APIView):
    """Common base: session auth, G1 gate, then the screen permission."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, RendicionFinalAccess]
    renderer_classes = [JSONRenderer]
    http_method_names = ["get", "head"]


def _documento_detalle(documento):
    tipo = documento.tipo  # nullable: the native template shows blanks
    return {
        "id": documento.pk,
        "tipo_nombre": tipo.nombre if tipo else "",
        "estado": documento.estado.nombre,
        "validador": tipo.validador if tipo else "",
        "observaciones": documento.observaciones or None,
        "fecha_modificacion": fecha(documento.fecha_modificacion),
        "archivo_url": archivo_url(documento),
        "editable": documento.editable,
        "validable": bool(tipo) and documento.validable,
        "eliminable": documento.eliminable,
    }


def _historial(registro):
    """Type, action, user and date of one history row of the native detail."""
    objeto = registro.objeto
    usuario = registro.usuario
    if not objeto:
        tipo_nombre = None  # «No disponible»
    else:
        tipo_nombre = getattr(objeto.tipo, "nombre", None) or "Desconocido"
    return {
        "tipo_nombre": tipo_nombre,
        "accion": registro.accion,
        "usuario": (usuario.get_full_name() or usuario.username) if usuario else "",
        "fecha": fecha(registro.fecha),
    }


class RendicionFinalDetalleWebView(RendicionFinalWebView):
    """``GET .../rendicion_cuentas_final/comedor/<pk>/``: ``rendicion_cuentas_final_detail.html``."""

    def get(self, request, pk):
        vista = RendicionCuentasFinalDetailView()
        vista.setup(request._request, pk=pk)  # pylint: disable=protected-access
        try:
            # Keeps the native ``get_or_create`` (a GET may create the rendición).
            vista.object = vista.get_object()
        except Http404 as exc:
            raise NotFound() from exc
        context = vista.get_context_data()
        rendicion = context["rendicion"]
        return Response(
            {
                "rendicion": {
                    "id": rendicion.pk,
                    "fisicamente_presentada": context["fisicamente_presentada"],
                },
                "comedor": {
                    "id": context["comedor_id"],
                    "nombre": context["comedor_nombre"],
                },
                "urls": {
                    "comedores": reverse("comedores"),
                    "comedor": reverse("comedor_detalle", args=[context["comedor_id"]]),
                },
                "documentos": [_documento_detalle(d) for d in context["documentos"]],
                "historial": [_historial(r) for r in context["historial"]],
                "messages": pending_messages(request),
            }
        )


def _fila(documento):
    return {
        "id": documento.pk,
        "tipo_nombre": documento.tipo.nombre if documento.tipo else "",
        "comedor_nombre": documento.rendicion_final.comedor.nombre,
        "fecha_modificacion": fecha(documento.fecha_modificacion),
        "estado": documento.estado.nombre,
        "estado_slug": slugify(documento.estado.nombre.lower()),
        "archivo_url": archivo_url(documento),
        "accionable": documento.estado.nombre == EN_ANALISIS,
    }


def _pagina(page_obj):
    return {
        "count": page_obj.paginator.count,
        "page": page_obj.number,
        "page_size": PAGE_SIZE,
        "pages": page_obj.paginator.num_pages,
        "previous": (
            page_obj.previous_page_number() if page_obj.has_previous() else None
        ),
        "next": page_obj.next_page_number() if page_obj.has_next() else None,
        "range": [
            "…" if n in ("...", "…") else n for n in build_compact_page_range(page_obj)
        ],
        "results": [_fila(d) for d in page_obj],
    }


class RendicionFinalDocumentosWebView(RendicionFinalWebView):
    """``GET .../rendicion_cuentas_final/documentos/``: the native list and its AJAX."""

    def get(self, request):
        vista = DocumentosRendicionCuentasFinalListView()
        vista.setup(request._request)  # pylint: disable=protected-access
        queryset = vista.get_queryset()
        if "busqueda" not in request.GET and "page" not in request.GET:
            # ``ListView`` without ``paginate_by``: every row, no paginator.
            filas = [_fila(d) for d in queryset]
            datos = {
                "count": len(filas),
                "page": 1,
                "page_size": None,
                "pages": 1,
                "previous": None,
                "next": None,
                "range": [],
                "results": filas,
            }
        else:
            paginator = Paginator(queryset, PAGE_SIZE)
            datos = _pagina(paginator.get_page(request.GET.get("page", 1)))
        return Response(
            {
                **datos,
                "has_previous": datos["previous"] is not None,
                "has_next": datos["next"] is not None,
                "filters": {"busqueda": request.GET.get("busqueda", "")},
                "messages": pending_messages(request),
            }
        )


class RendicionFinalAccionWebView(RendicionFinalWebView):
    """Common base of the POST actions: CSRF from ``SessionAuthentication``, no state guard
    (the native views have none either)."""

    parser_classes = [MultiPartParser, FormParser]
    http_method_names = ["post", "options"]


def _documento_estado(documento):
    return {
        "id": documento.pk,
        "estado": documento.estado.nombre,
        "fecha_modificacion": fecha(documento.fecha_modificacion),
    }


def _cambiar_estado(documento, estado, accion):
    """The native ``validar``/``subsanar`` write: state, timestamp and history."""
    documento.estado = EstadoDocumentoRendicionFinal.objects.get(nombre=estado)
    documento.fecha_modificacion = timezone.now()
    documento.save()
    HistorialService.registrar_historial(accion=accion, instancia=documento)


class ValidarWebView(RendicionFinalAccionWebView):
    """``POST .../documentos/<id>/validar/``: ``validar_documento_rendicion_cuentas_final``."""

    def post(self, request, documento_id):
        documento = get_object_or_404(DocumentoRendicionFinal, id=documento_id)
        _cambiar_estado(documento, "Validado", "Validar documento")
        return Response(
            {
                "ok": True,
                "message": "Documento validado correctamente.",
                "documento": _documento_estado(documento),
            }
        )


class SubsanarWebView(RendicionFinalAccionWebView):
    """``POST .../documentos/<id>/subsanar/``: ``subsanar_documento_rendicion_cuentas_final``."""

    def post(self, request, documento_id):
        documento = get_object_or_404(DocumentoRendicionFinal, id=documento_id)
        documento.observaciones = request.POST.get("observacion", "")
        _cambiar_estado(documento, "Subsanar", "Enviar a subsanar documento")
        return Response(
            {
                "ok": True,
                "message": "Documento enviado a subsanar correctamente.",
                "documento": _documento_estado(documento),
            }
        )


class EliminarWebView(RendicionFinalAccionWebView):
    """``POST .../documentos/<id>/eliminar/``: ``eliminar_documento_rendicion_cuentas_final``."""

    def post(self, request, documento_id):
        documento = get_object_or_404(DocumentoRendicionFinal, id=documento_id)
        if documento.documento:
            documento.documento.delete(save=False)
        _cambiar_estado(documento, "No presentado", "Documento eliminado")
        return Response(
            {
                "ok": True,
                "message": "Documento eliminado correctamente.",
                "documento": _documento_estado(documento),
            }
        )


class AdjuntarWebView(RendicionFinalAccionWebView):
    """``POST .../documentos/adjuntar/``: ``adjuntar_documento_rendicion_cuenta_final``."""

    def post(self, request):
        ok, _documento = RendicionCuentasFinalService.adjuntar_archivo_a_documento(
            request.POST.get("documento_id"), request.FILES.get("archivo")
        )
        if not ok:
            return Response(
                {"ok": False, "message": "No se seleccionó ningún archivo."}, status=400
            )
        return Response({"ok": True, "message": "Archivo adjuntado correctamente."})


class CrearWebView(RendicionFinalAccionWebView):
    """``POST .../<rendicion_id>/crear/``: ``crear_documento_rendicion_cuentas_final``."""

    def post(self, request, rendicion_id):
        rendicion = get_object_or_404(RendicionCuentasFinal, id=rendicion_id)
        nombre = request.POST.get("nombre", "").strip()
        archivo = request.FILES.get("archivo")
        documento = rendicion.add_documento_personalizado(nombre)
        if archivo:
            HistorialService.registrar_historial(
                accion="Crear documento personalizado", instancia=documento
            )
            RendicionCuentasFinalService.actualizar_documento_con_archivo(
                documento, archivo
            )
        return Response({"ok": True, "message": None})


class FisicamentePresentadaWebView(RendicionFinalAccionWebView):
    """``POST .../<rendicion_id>/fisicamente_presentada/``: the native switch."""

    def post(self, request, rendicion_id):
        rendicion = get_object_or_404(RendicionCuentasFinal, id=rendicion_id)
        rendicion.fisicamente_presentada = not rendicion.fisicamente_presentada
        rendicion.save()
        return Response(
            {
                "ok": True,
                "message": "Estado de revisión actualizado.",
                "fisicamente_presentada": rendicion.fisicamente_presentada,
            }
        )
