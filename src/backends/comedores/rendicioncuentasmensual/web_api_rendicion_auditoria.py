"""Web API (G1 v1) of the monthly rendición audit screens served by React (RM01.03).

``/api/web/comedores/rendicioncuentasmensual/auditoria/`` keeps the permission of the
native URLs (``rendicioncuentasmensual.manage_auditoria_stage``, superuser bypass
included) and runs the native ``RendicionAuditoriaView`` itself:

* ``auditoria/``: the search page (``AuditoriaBusquedaForm``, ``AuditoriaService.buscar``
  and the 20-row paginator, through the view's ``_contexto_busqueda``).
* ``auditoria/<pk>/``: the audit form and its documentation summaries. GET and POST are
  the view's own ``get`` and ``post`` (``AuditoriaForm``, ``AuditoriaService.guardar``
  with its locks and the success message); a redirect becomes
  ``{"ok": true, "redirect": ...}`` and a rejected form 400 with the page's form data.

The native ``?rendicion=<id>`` redirect of the search URL stays native (the preview entry
answers it before serving React). The page's JavaScript
(``rendicioncuentasmensual_auditoria.js``) lives in the React module.
"""

from django.http import Http404
from django.template.defaultfilters import date as date_filter
from django.template.defaultfilters import urlencode, yesno
from django.urls import reverse
from django.utils.formats import localize
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from core.pagination import build_compact_page_range
from core.web_gate import WebGatePermission
from intervenciones.web_api import NativeWebView, pending_messages, requires_any
from rendicioncuentasmensual.views import RendicionAuditoriaView
from rendicioncuentasmensual.web_api_rendicion_detalle import _resumen
from rendicioncuentasmensual.web_api_rendicion_form import (
    FORMATOS,
    _campo,
    _errores,
)

PERMISO_AUDITORIA = ["rendicioncuentasmensual.manage_auditoria_stage"]
DATE = "d/m/Y"


class _Contexto:
    """What the overridden ``_render`` hands back instead of a rendered page."""

    status_code = 200

    def __init__(self, context_data):
        self.context_data = context_data


class _VistaAuditoria(RendicionAuditoriaView):
    """The native view, with its page render replaced by its template context."""

    def _render(self, request, rendicion, form):
        return _Contexto(self._contexto(request, rendicion, form))


def _texto(valor):
    """``{{ valor }}`` of a template: ``None`` prints as ``None``."""
    return str(valor)


def _numero(rendicion):
    """``{{ x.numero_rendicion|default:x.pk }}`` (localized)."""
    return localize(rendicion.numero_rendicion or rendicion.pk)


def _periodo(rendicion):
    return (
        f"{date_filter(rendicion.periodo_inicio, DATE)} al "
        f"{date_filter(rendicion.periodo_fin, DATE)}"
    )


def _fila(item):
    proyecto = item.proyecto
    comedor = item.comedor
    codigo_comedor = comedor.codigo_de_proyecto if comedor else ""
    organizacion = (
        proyecto.organizacion.nombre if proyecto and proyecto.organizacion else ""
    )
    if not proyecto:
        organizacion = (
            comedor.organizacion.nombre if comedor and comedor.organizacion else ""
        ) or "Sin organización"
    codigo = proyecto.codigo if proyecto else (codigo_comedor or "Sin proyecto")
    codigo_aria = (
        proyecto.codigo if proyecto else (_texto(codigo_comedor) if comedor else "")
    )
    return {
        "id": item.pk,
        "proyecto": codigo,
        "organizacion": organizacion,
        "convenio_numero": f"{item.convenio or 'Sin convenio'} · {_numero(item)}",
        "periodo": _periodo(item),
        "validada": yesno(item.validada, "Sí,No,No"),
        "gestionar_url": (
            reverse("rendicioncuentasmensual_auditoria", args=[item.pk])
            + "?origen=busqueda"
        ),
        "aria_label": (
            f"Gestionar auditoría de la rendición {_numero(item)}, "
            f"convenio {_texto(item.convenio)}, proyecto {codigo_aria}"
        ),
    }


def _query_prefix(request, busqueda):
    """Prefix of every ``components/pagination.html`` link (``page`` appended)."""
    base = f"busqueda={urlencode(busqueda)}&" if busqueda else ""
    return base + "".join(
        f"{clave}={urlencode(valor)}&"
        for clave, valor in request.GET.items()
        if clave not in ("page", "busqueda")
    )


def _pagina(contexto, request, busqueda):
    page = contexto["page_obj"]
    return {
        "is_paginated": contexto["is_paginated"],
        "number": page.number,
        "count": page.paginator.count,
        "previous": page.previous_page_number() if page.has_previous() else None,
        "next": page.next_page_number() if page.has_next() else None,
        "range": [
            "…" if numero in ("...", "…") else numero
            for numero in build_compact_page_range(page)
        ],
        "query_prefix": _query_prefix(request, busqueda),
    }


def _mensajes(campo):
    return [str(error) for error in campo.errors]


class AuditoriaBusquedaWebView(NativeWebView):
    """``GET .../rendicioncuentasmensual/auditoria/``: the search page."""

    permission_classes = [WebGatePermission, requires_any(PERMISO_AUDITORIA)]

    def get(self, request):
        vista = self.native(_VistaAuditoria, request)
        # pylint: disable-next=protected-access
        contexto = vista._contexto_busqueda(request._request)
        form = contexto["busqueda_form"]
        busqueda = form["busqueda"].value() or ""
        filtro = form["filtro"]
        return Response(
            {
                "filtro": {
                    "value": filtro.value() or "",
                    "choices": [
                        {"value": str(valor), "label": str(etiqueta)}
                        for valor, etiqueta in filtro.field.choices
                    ],
                    "errors": _mensajes(filtro),
                },
                "busqueda": {
                    "value": str(busqueda),
                    "maxlength": form.fields["busqueda"].max_length,
                    "errors": _mensajes(form["busqueda"]),
                },
                "busqueda_realizada": contexto["busqueda_realizada"],
                "busqueda_valida": contexto["busqueda_valida"],
                "filas": [_fila(item) for item in contexto["disponibles"]],
                "page": _pagina(contexto, request, busqueda),
                "urls": {
                    "listado": reverse("rendicioncuentasmensual_global_list"),
                    "limpiar": reverse("rendicioncuentasmensual_auditoria_nueva"),
                    "volver": contexto["volver_url"],
                },
                "messages": pending_messages(request),
            }
        )


def _opcion(opcion):
    incluida = opcion.data["value"].instance
    return {
        "value": str(opcion.data["value"].value),
        "id": opcion.id_for_label,
        "checked": bool(opcion.data["selected"]),
        "numero": _numero(incluida),
        "convenio": incluida.convenio or "Sin convenio",
        "periodo": _periodo(incluida),
        "linea": incluida.get_linea_programatica_display(),
    }


def _formulario(form):
    errores = _errores(form)
    return {
        "ya_validada": bool(form.ya_validada),
        "validada": {
            "checked": bool(form["validada"].value()),
            "errors": [e["message"] for e in errores.get("validada", [])],
        },
        "genera_acta_auditoria": _campo(form, "genera_acta_auditoria"),
        "rendiciones_incluidas": {
            "errors": [e["message"] for e in errores.get("rendiciones_incluidas", [])],
            "opciones": [_opcion(o) for o in form["rendiciones_incluidas"]],
        },
        "acta_auditoria": _campo(form, "acta_auditoria"),
        "resultado": _campo(form, "resultado"),
        "observaciones": _campo(form, "observaciones"),
        "documento_regularizacion": _campo(form, "documento_regularizacion"),
        "errors": errores,
        "non_field_errors": [str(e) for e in form.non_field_errors()],
    }


def _gestion(request, contexto):
    rendicion = contexto["rendicion"]
    scope = contexto["scope_proyecto"]
    organizacion = scope["organizacion"]
    return {
        "rendicion": {
            "id": rendicion.pk,
            "numero": _numero(rendicion),
            "convenio": rendicion.convenio or "Sin convenio",
            "periodo": _periodo(rendicion),
            "organizacion": (organizacion.nombre if organizacion else None)
            or "Sin organización",
            "proyecto": scope["proyecto_codigo"] or "Sin proyecto",
            "convenio_dato": rendicion.convenio or "Sin dato",
            "linea_programatica": rendicion.get_linea_programatica_display(),
        },
        "form": _formulario(contexto["form"]),
        "resumenes": [_resumen(r, rendicion) for r in contexto["resumenes"]],
        "urls": {
            "listado": reverse("rendicioncuentasmensual_global_list"),
            "volver": contexto["volver_url"],
        },
        "volver_a_busqueda": bool(contexto["volver_a_busqueda"]),
        "messages": pending_messages(request),
    }


class AuditoriaGestionWebView(NativeWebView):
    """``.../rendicioncuentasmensual/auditoria/<pk>/``: the audit form."""

    permission_classes = [WebGatePermission, requires_any(PERMISO_AUDITORIA)]
    http_method_names = ["get", "post", "head"]

    def get(self, request, pk):
        vista = self.native(_VistaAuditoria, request, pk=pk)
        try:
            # pylint: disable-next=protected-access
            respuesta = vista.get(request._request, pk=pk)
        except Http404 as exc:
            raise NotFound() from exc
        return Response(_gestion(request, respuesta.context_data))

    def post(self, request, pk):
        # ``Request.content_type`` keeps the multipart boundary; Django strips it.
        # pylint: disable-next=protected-access
        if request._request.content_type not in FORMATOS:
            return Response({"detail": "Formato de solicitud no admitido."}, status=415)
        vista = self.native(_VistaAuditoria, request, pk=pk)
        try:
            # pylint: disable-next=protected-access
            respuesta = vista.post(request._request, pk=pk)
        except Http404 as exc:
            raise NotFound() from exc
        if respuesta.status_code == 302:
            return Response({"ok": True, "redirect": respuesta["Location"]})
        return Response(_gestion(request, respuesta.context_data), status=400)
