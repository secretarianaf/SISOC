"""Web API (G1 v1) of the monthly rendición detail (RM01.01).

``GET /api/web/comedores/rendicioncuentasmensual/<pk>/`` runs the native
``RendicionCuentaMensualDetailView`` itself (``get_object`` with its 404, the
documentation by category, the project scope and every capability of
``get_context_data``) and projects that context to JSON. Access is the native
one, with no object scope (kept on purpose, see
``docs/registro/decisiones/2026-11-10-2785-brechas-acceso-conservadas.md``):
superuser or any of the five codes of ``rendicioncuentasmensual/urls.py``.

The page keeps posting to the native URL (stage actions, document review and
missing-document requests) and keeps the native PDF and document downloads, so
this module is read-only. Dates, numbers and labels are formatted here with the
same filters the template uses; React never formats them.
"""

from datetime import datetime

from django.contrib import messages
from django.http import Http404
from django.template.defaultfilters import date as date_filter
from django.template.defaultfilters import yesno
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import localize
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound
from rest_framework.permissions import BasePermission
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

# The exact predicate of ``permissions_any_required``, the native URL guard.
from core.decorators import _has_any_permissions
from core.web_gate import WebGatePermission
from rendicioncuentasmensual.models import RendicionCuentaMensual
from rendicioncuentasmensual.urls import _RENDICION_ACCESS_PERMS
from rendicioncuentasmensual.views import RendicionCuentaMensualDetailView

DATE_TIME = "d/m/Y H:i"
DATE = "d/m/Y"
# ``categoria.codigo == 'comprobantes' or 'otros'`` of the native template.
CATEGORIAS_HISTORIAL_PLANO = ("comprobantes", "otros")
MESSAGE_LEVELS = {
    messages.DEBUG: "info",
    messages.INFO: "info",
    messages.SUCCESS: "success",
    messages.WARNING: "warning",
    messages.ERROR: "error",
}
CAPABILITIES = (
    "puede_revisar_documentos",
    "puede_solicitar_faltantes",
    "puede_revision_territorial",
    "puede_revision_auditoria",
    "puede_auditoria",
    "puede_regularizacion",
    "puede_editar_datos",
    "puede_gestionar_auditoria",
    "mostrar_acciones_proceso",
    "mostrar_documentacion_auditoria",
    "puede_descargar_pdf",
)


class RendicionAccess(BasePermission):
    """Same rule as the native ``permissions_any_required(_RENDICION_ACCESS_PERMS)``."""

    def has_permission(self, request, view):
        return _has_any_permissions(request.user, _RENDICION_ACCESS_PERMS)


def _fecha(value, formato=DATE_TIME):
    """``|date:"..."`` of the native template (local time); ``""`` without a value."""
    if not value:
        return ""
    if isinstance(value, datetime) and timezone.is_aware(value):
        value = timezone.localtime(value)
    return date_filter(value, formato)


def _nombre_usuario(usuario):
    """``usuario.get_full_name|default:usuario.username``, ``Sin dato`` without a user."""
    if not usuario:
        return "Sin dato"
    return usuario.get_full_name() or usuario.username


def _badge_estado(archivo):
    """Badge class and text the native table draws for one document state."""
    if archivo.get_estado_visual() == "subsanado":
        return "pendiente", archivo.get_estado_visual_display()
    if archivo.estado == "validado":
        return "validado", archivo.get_estado_display()
    if archivo.estado == "subsanar":
        return "no-validado", archivo.get_estado_display()
    return "pendiente", archivo.get_estado_display()


def _archivo(archivo):
    badge, texto = _badge_estado(archivo)
    return {
        "id": archivo.pk,
        "nombre": archivo.nombre,
        "estado": archivo.estado,
        "badge": badge,
        "estado_text": texto,
        "observaciones": archivo.observaciones or "",
        "fecha": _fecha(archivo.fecha_creacion),
        "visualizado": bool(getattr(archivo, "visualizacion_confirmada", False)),
        "visualizacion_title": (
            f"Por {archivo.visualizacion_usuario} el "
            f"{_fecha(archivo.visualizacion_fecha)}"
        ),
        "ver_url": reverse("rendicioncuentasmensual_documento_ver", args=[archivo.pk]),
    }


def _categoria(categoria):
    solicitud = categoria["solicitud_faltante"]
    archivos = []
    for archivo in categoria["archivos"]:
        datos = _archivo(archivo)
        datos["subsanaciones"] = [
            _archivo(item) for item in (archivo.subsanaciones_historial or [])
        ]
        archivos.append(datos)
    return {
        "codigo": categoria["codigo"],
        "label": str(categoria["label"]),
        "required": bool(categoria["required"]),
        "historial_plano": categoria["codigo"] in CATEGORIAS_HISTORIAL_PLANO,
        "solicitud_faltante": (
            {"observaciones": solicitud.observaciones or ""} if solicitud else None
        ),
        "archivos": archivos,
    }


def _resumen(resumen, actual):
    rendicion = resumen["rendicion"]
    return {
        "id": rendicion.pk,
        "actual": rendicion.pk == actual.pk,
        "titulo": (
            f"Rendición {rendicion.numero_rendicion or rendicion.pk} · "
            f"{rendicion.convenio or 'Sin convenio'} · "
            f"{_fecha(rendicion.periodo_inicio, DATE)} al "
            f"{_fecha(rendicion.periodo_fin, DATE)}"
        ),
        "documentos": [
            {
                "categoria": str(categoria["label"]),
                "nombre": archivo.nombre,
                "estado_text": archivo.get_estado_display(),
                "ver_url": reverse(
                    "rendicioncuentasmensual_documento_ver", args=[archivo.pk]
                ),
            }
            for categoria in resumen["categorias"]
            for archivo in categoria["archivos"]
        ],
    }


def _url_archivo(campo):
    """``campo.url``: the native storage URL, ``None`` without a file."""
    return campo.url if campo else None


def _pending_messages(request):
    return [
        {"message": str(m), "level": MESSAGE_LEVELS.get(m.level, "info")}
        for m in messages.get_messages(request)
    ]


def _resultado_auditoria(rendicion):
    if rendicion.etapa_proceso == RendicionCuentaMensual.ETAPA_REGULARIZACION:
        return "Finalizada con Observaciones"
    return rendicion.estado_proceso_display


def _datos(rendicion, scope):
    organizacion = scope["organizacion"]
    return {
        "id": rendicion.pk,
        "numero": localize(rendicion.numero_rendicion or rendicion.pk),
        "nombre": rendicion.nombre or "Sin dato",
        "proyecto": scope["proyecto_codigo"] or "Sin proyecto",
        "organizacion": (organizacion.nombre if organizacion else None)
        or "Sin organizacion",
        "convenio": rendicion.convenio or "Sin dato",
        "linea_programatica": rendicion.get_linea_programatica_display(),
        "mes_anio": f"{localize(rendicion.mes)} / {localize(rendicion.anio)}",
        "periodo": (
            f"{_fecha(rendicion.periodo_inicio, DATE)} - "
            f"{_fecha(rendicion.periodo_fin, DATE)}"
            if rendicion.periodo_inicio and rendicion.periodo_fin
            else "Sin dato"
        ),
        "fecha_creacion": _fecha(rendicion.fecha_creacion),
        "ultima_modificacion": _fecha(rendicion.ultima_modificacion),
        "comedores_relacionados": [
            comedor.nombre for comedor in scope["comedores_relacionados"]
        ],
        "usuario_creador": _nombre_usuario(rendicion.usuario_creador),
        "usuario_ultima_modificacion": _nombre_usuario(
            rendicion.usuario_ultima_modificacion
        ),
        "observaciones": rendicion.observaciones or "",
        "etapa_proceso": rendicion.etapa_proceso,
        "subestado_proceso": rendicion.subestado_proceso,
        "estado_proceso_display": rendicion.estado_proceso_display,
        "validada": yesno(rendicion.validada, "Sí,No,No"),
        "genera_acta": bool(rendicion.genera_acta_auditoria),
        "genera_acta_text": yesno(rendicion.genera_acta_auditoria, "Sí,No,Sin definir"),
        "resultado_auditoria": _resultado_auditoria(rendicion),
        "acta_auditoria_url": _url_archivo(rendicion.acta_auditoria),
        "documento_regularizacion_url": _url_archivo(
            rendicion.documento_regularizacion
        ),
    }


class RendicionDetalleWebView(APIView):
    """``GET .../rendicioncuentasmensual/<pk>/``: ``rendicioncuentasmensual_detail.html``."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, RendicionAccess]
    renderer_classes = [JSONRenderer]
    http_method_names = ["get", "head"]

    def get(self, request, pk):
        vista = RendicionCuentaMensualDetailView()
        vista.setup(request._request, pk=pk)  # pylint: disable=protected-access
        try:
            vista.object = vista.get_object()
            context = vista.get_context_data()
        except Http404 as exc:
            raise NotFound() from exc
        rendicion = context["rendicion"]
        return Response(
            {
                "rendicion": _datos(rendicion, context["scope_proyecto"]),
                "capabilities": {
                    nombre: bool(context[nombre]) for nombre in CAPABILITIES
                },
                "documentacion": [
                    _categoria(c) for c in context["documentacion_por_categoria"]
                ],
                "resumenes": [
                    _resumen(r, rendicion) for r in context.get("resumenes", [])
                ],
                "urls": {
                    "volver": context["volver_url"],
                    "update": reverse(
                        "rendicioncuentasmensual_update", args=[rendicion.pk]
                    ),
                    "auditoria": reverse(
                        "rendicioncuentasmensual_auditoria", args=[rendicion.pk]
                    ),
                    "pdf_solicitar": reverse(
                        "rendicioncuentasmensual_download_pdf_solicitar",
                        args=[rendicion.pk],
                    ),
                    "pdf_estado": reverse(
                        "rendicioncuentasmensual_download_pdf_estado",
                        args=[rendicion.pk],
                    ),
                },
                "messages": _pending_messages(request),
            }
        )
