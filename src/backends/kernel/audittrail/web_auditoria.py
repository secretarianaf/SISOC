"""Listado global y detalle de un evento de auditoría para React (G1 v1).

``/api/web/auditoria/listado/`` corre ``AuditLogListView`` y ``/api/web/auditoria/evento/<pk>/``
corre ``AuditLogDetailView``, cada una con su ``dispatch`` nativo (login y ``auditlog.view_logentry``:
403; página fuera de rango o evento inexistente: 404). Proyectan el contexto de ``log_list.html`` y
``log_detail.html`` tal como lo imprimen las plantillas. La exportación CSV/JSON no pasa por acá: sigue
siendo el ``GET`` nativo de la propia página (``?export=``), que estas vistas ignoran. Solo lectura.
"""

from urllib.parse import urlsplit

from django.http import Http404
from django.template.defaultfilters import date as date_filter
from django.template.defaultfilters import striptags, truncatechars
from django.urls import reverse
from django.utils.timezone import localtime
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from audittrail.views import AuditLogDetailView, AuditLogListView
from audittrail.web_historial import (
    HistorialInstanciaWebView,
    _valor,
    proyectar,
)

PREVIEW_MAX = 180


def _ruta_listado(parametros):
    """``list_return_path`` de la página nativa (``request.path`` de la API no es el suyo)."""
    ruta = reverse("audittrail:log_list")
    consulta = parametros.urlencode()
    return f"{ruta}?{consulta}" if consulta else ruta


def proyectar_listado(contexto, request, return_path):
    datos = proyectar(contexto, request, return_path)
    for campo in datos["fields"]:
        campo["hidden"] = False  # fuera del modo instancia, modelo e ID se ven
    for fila, entry in zip(datos["filas"], contexto["entries"]):
        fila["modelo_texto"] = (
            f"{entry.content_type.app_label}.{entry.content_type.model}"
        )
        fila["instancia_texto"] = f"#{entry.object_pk}"
    return datos


class AuditoriaListadoWebView(HistorialInstanciaWebView):
    """Listado global: misma proyección que el historial, con modelo e instancia por fila."""

    def get(self, request, **kwargs):
        # pylint: disable-next=protected-access
        django_request = request._request
        parametros = django_request.GET.copy()
        parametros.pop("export", None)
        django_request.GET = parametros
        vista = AuditLogListView()
        vista.setup(django_request, **kwargs)
        try:
            respuesta = vista.dispatch(django_request, **kwargs)
        except Http404 as exc:
            raise NotFound() from exc
        return Response(
            proyectar_listado(
                respuesta.context_data, request, _ruta_listado(parametros)
            )
        )


def _valor_detalle(valor):
    """``change.old``/``change.new`` con el resumen de ``details`` cuando pasa de 180 caracteres."""
    proyeccion = _valor(valor)
    sin_etiquetas = striptags(proyeccion["text"])
    largo = len(sin_etiquetas) > PREVIEW_MAX
    proyeccion["preview"] = truncatechars(sin_etiquetas, PREVIEW_MAX) if largo else None
    return proyeccion


def _volver(url):
    """``back_url`` ya validado por la vista nativa, como ruta interna (mismo host)."""
    partes = urlsplit(url)
    ruta = partes.path or "/"
    return f"{ruta}?{partes.query}" if partes.query else ruta


def proyectar_evento(contexto):
    entry = contexto["entry"]
    marcador = bool(getattr(entry, "ui_bulk_marker", None))
    agrupado = bool(getattr(entry, "ui_bulk_grouped", False))
    if agrupado:
        aviso = f"Evento asociado a acción masiva ({getattr(entry, 'ui_bulk_source_label', '')})"
    elif marcador:
        aviso = "Evento asociado a proceso con correlación"
    else:
        aviso = ""
    lote = (
        str(entry.ui_bulk_value)
        if entry.ui_bulk_source == "batch_key" and entry.ui_bulk_value
        else ""
    )
    cambios = [
        {
            "campo": str(campo),
            "old": _valor_detalle(c["old"]),
            "new": _valor_detalle(c["new"]),
        }
        for campo, c in contexto["changes"].items()
    ]
    return {
        "id": entry.pk,
        "inicio_url": reverse("inicio"),
        "volver_url": _volver(contexto["back_url"]),
        "fecha_texto": date_filter(localtime(entry.timestamp), "Y-m-d H:i:s"),
        "actor_texto": entry.ui_actor_primary or "Sistema",
        "actor_fallback": bool(entry.ui_actor_is_fallback),
        "actor_secundario": str(entry.ui_actor_secondary or ""),
        "modelo_texto": f"{entry.content_type.app_label}.{entry.content_type.model}",
        "instancia_texto": f"#{entry.object_pk}",
        "evento_texto": entry.ui_action_label or entry.get_action_display(),
        "evento_clase": entry.ui_action_badge_class or "bg-secondary",
        "con_diffs": bool(entry.ui_has_diffs),
        "aviso_masivo": aviso,
        "origen_texto": str(entry.ui_source_label or "-"),
        "batch_key": lote,
        "ip_texto": str(entry.remote_addr or "-"),
        "es_eliminacion": bool(entry.ui_action_is_delete),
        "cambios": cambios,
    }


class AuditoriaEventoWebView(HistorialInstanciaWebView):
    """Detalle de un evento: ``AuditLogDetailView`` con su ``next`` validado."""

    def get(self, request, **kwargs):
        # pylint: disable-next=protected-access
        django_request = request._request
        vista = AuditLogDetailView()
        vista.setup(django_request, **kwargs)
        try:
            respuesta = vista.dispatch(django_request, **kwargs)
        except Http404 as exc:
            raise NotFound() from exc
        return Response(proyectar_evento(respuesta.context_data))
