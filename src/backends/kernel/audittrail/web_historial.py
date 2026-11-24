"""Historial de auditoría de una instancia para React (C05, G1 v1).

``/api/web/auditoria/<app_label>/<model_name>/<object_pk>/`` lo sirve el core y corre
``AuditLogInstanceView`` con su ``dispatch`` (login y ``auditlog.view_logentry``: 403;
un número de página fuera de rango: 404). Proyecta el contexto de ``log_list.html`` tal
como lo imprime la plantilla: campos del filtro con su valor, filtros activos, filas ya
formateadas (fecha local ``Y-m-d H:i``, actor, evento, lote y los cambios) y
la paginación. La exportación CSV/JSON no pasa por acá: sigue siendo el ``GET`` nativo
de la propia página (``?export=``), que esta vista ignora. Solo lectura.
"""

from urllib.parse import quote

from django.http import Http404
from django.template.defaultfilters import date as date_filter
from django.urls import reverse
from django.utils.cache import patch_cache_control, patch_vary_headers
from django.utils.timezone import localtime
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from audittrail.views import AuditLogInstanceView
from ciudadanos.web_ficha import pending_messages
from core.web_gate import WebGatePermission

NO_CARGADO = "<em>No cargado</em>"
CAMPOS_ORDEN = (
    "keyword",
    "field_name",
    "batch_key",
    "model",
    "object_pk",
    "actor",
    "action",
    "origin",
    "start_date",
    "end_date",
)
OCULTOS = ("model", "object_pk")


def _valor(valor):
    """``{{ change.old }}``: solo «No cargado» llega como HTML seguro."""
    texto = str(valor)
    vacio = texto == NO_CARGADO
    return {"empty": vacio, "text": "" if vacio else texto}


def _campo(form, nombre):
    campo = form.fields[nombre]
    ligado = form[nombre]
    valor = ligado.value()
    con_opciones = hasattr(campo, "choices")
    proyeccion = {
        "name": nombre,
        "label": str(ligado.label),
        "hidden": nombre in OCULTOS,
        "widget": "select" if con_opciones else campo.widget.input_type,
        "value": "" if valor is None else str(valor),
        "attrs": {
            clave: str(atributo)
            for clave, atributo in ligado.build_widget_attrs(
                dict(campo.widget.attrs)
            ).items()
            if clave in ("placeholder", "maxlength", "max")
        },
    }
    if con_opciones:
        proyeccion["choices"] = [
            {"value": str(valor), "label": str(texto)} for valor, texto in campo.choices
        ]
    return proyeccion


def _detalle_url(entry, return_path):
    """``{% url 'audittrail:log_detail' pk %}?next={{ list_return_path|urlencode }}``."""
    url = reverse("audittrail:log_detail", args=[entry.pk])
    return f"{url}?next={quote(return_path, safe='/')}" if return_path else url


def _fila(entry, return_path):
    # ``items|slice:":2"`` de la plantilla no corta un ``dict_items`` (Django devuelve el valor
    # sin cambios ante el ``TypeError``): la página nativa lista todos los cambios y además
    # «+ N más». Se conserva.
    cambios = list(entry.resolved_changes.items())
    return {
        "id": entry.pk,
        "fecha_texto": date_filter(localtime(entry.timestamp), "Y-m-d H:i"),
        "actor_texto": entry.ui_actor_primary or "Sistema",
        "actor_fallback": bool(entry.ui_actor_is_fallback),
        "evento_texto": entry.ui_action_label or entry.get_action_display(),
        "evento_clase": entry.ui_action_badge_class or "bg-secondary",
        "continuacion": bool(entry.ui_bulk_sequence_continuation),
        "masiva": bool(entry.ui_bulk_grouped),
        "masiva_inicio": bool(entry.ui_bulk_sequence_start),
        "masiva_cantidad": entry.ui_bulk_count if entry.ui_bulk_grouped else 0,
        "masiva_origen": str(entry.ui_bulk_source_label or ""),
        "con_diffs": bool(entry.ui_has_diffs),
        "cambios": [
            {"campo": str(campo), "old": _valor(c["old"]), "new": _valor(c["new"])}
            for campo, c in cambios
        ],
        "cambios_total": len(cambios),
        "detalle_url": _detalle_url(entry, return_path),
    }


def _errores(form):
    return {
        "field_errors": [
            {"label": str(campo.label), "message": str(error)}
            for campo in form
            for error in campo.errors
        ],
        "non_field_errors": [str(e) for e in form.non_field_errors()],
    }


def _ruta_del_listado(kwargs, parametros):
    """``list_return_path`` de la página nativa (el ``request.path`` de la API no es el suyo)."""
    ruta = reverse("audittrail:log_instance", kwargs=kwargs)
    consulta = parametros.urlencode()
    return f"{ruta}?{consulta}" if consulta else ruta


def proyectar(contexto, request, return_path):
    form = contexto["filter_form"]
    pagina = contexto["page_obj"]
    return {
        "title": str(contexto["title"]),
        "inicio_url": reverse("inicio"),
        "fields": [_campo(form, nombre) for nombre in CAMPOS_ORDEN],
        **_errores(form),
        "has_errors": bool(form.errors),
        "puede_exportar": request.user.has_perm("audittrail.export_auditlog"),
        "filtros_activos": [
            {"label": str(f["label"]), "value": str(f["value"])}
            for f in contexto["active_filters"]
        ],
        "filas": [_fila(e, return_path) for e in contexto["entries"]],
        "paginacion": {
            "is_paginated": bool(contexto["is_paginated"]),
            "number": pagina.number,
            "num_pages": pagina.paginator.num_pages,
            "previous": pagina.has_previous(),
            "next": pagina.has_next(),
            "querystring": contexto["querystring"],
        },
        "messages": pending_messages(request),
    }


class HistorialInstanciaWebView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission]
    renderer_classes = [JSONRenderer]
    http_method_names = ["get"]

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        patch_cache_control(response, private=True, no_store=True)
        patch_vary_headers(response, ("Cookie",))
        return response

    def get(self, request, **kwargs):
        # pylint: disable-next=protected-access
        django_request = request._request
        # La exportación es el GET nativo de la página; acá solo se lee el listado.
        parametros = django_request.GET.copy()
        parametros.pop("export", None)
        django_request.GET = parametros
        vista = AuditLogInstanceView()
        vista.setup(django_request, **kwargs)
        try:
            respuesta = vista.dispatch(django_request, **kwargs)
        except Http404 as exc:
            raise NotFound() from exc
        return Response(
            proyectar(
                respuesta.context_data,
                request,
                _ruta_del_listado(kwargs, parametros),
            )
        )
