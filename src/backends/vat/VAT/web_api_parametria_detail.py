"""Web API (G1 v1) del detalle de parametría de voucher y sus asignaciones (V01.03).

``GET /api/web/vat/vouchers/parametrias/<pk>/`` corre ``VoucherParametriaDetailView``
(estadísticas, vouchers paginados y métricas) y proyecta su contexto. ``POST .../asignar/``
y ``.../asignar-masivo/`` corren ``VoucherParametriaAsignarView`` y
``VoucherParametriaAsignarMasivoView`` (``_asignar_desde_parametria``, servicio y mensajes
nativos) y responden ``{"ok": true, "redirect": <detalle>}``, como la redirección nativa.
Acceso: ``VAT.view_voucher`` para el detalle y ``VAT.add_voucher`` para asignar.
"""

from html import unescape

from django.http import Http404
from django.template import Context, Template
from django.urls import reverse
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from core.pagination import build_compact_page_range
from VAT.views.voucher_parametria import (
    VoucherParametriaAsignarMasivoView,
    VoucherParametriaAsignarView,
    VoucherParametriaDetailView,
)
from VAT.web_api_common import VatNativeReadView, mensajes_pendientes, texto

_FECHA = "{{ v|date:'d/m/Y' }}"
_BARRA = "{% widthratio d i 100 %}"
_PORCENTAJE = "{% widthratio n t 100 %}"
_QUERY = Template(
    "{% if query %}busqueda={{ query|urlencode }}&{% endif %}"
    "{% for key, value in request.GET.items %}{% if key != 'vouchers_page' and "
    "key != 'busqueda' %}{{ key }}={{ value|urlencode }}&{% endif %}{% endfor %}"
)


def _porcentaje(n, total):
    return texto(_PORCENTAJE, n=n, t=total)


def _tono_estado(estado):
    if estado == "agotado":
        return "bg-warning text-dark"
    return {"activo": "bg-success", "vencido": "bg-danger"}.get(estado, "bg-secondary")


def _fila(v):
    if v.cantidad_disponible == 0:
        barra = "bg-danger"
    elif v.cantidad_disponible < v.cantidad_inicial:
        barra = "bg-warning"
    else:
        barra = "bg-success"
    return {
        "id": v.pk,
        "ciudadano": v.ciudadano.nombre_completo,
        "documento": texto("{{ v }}", v=v.ciudadano.documento),
        "disponible": v.cantidad_disponible,
        "inicial": v.cantidad_inicial,
        "barra": barra,
        "ancho": texto(_BARRA, d=v.cantidad_disponible, i=v.cantidad_inicial),
        "badge": _tono_estado(v.estado),
        "estado_label": v.get_estado_display(),
        "detail_url": reverse("vat_voucher_detail", args=[v.pk]),
    }


def _ultima(v):
    return {
        "ciudadano": v.ciudadano.nombre_completo,
        "documento": texto("{{ v }}", v=v.ciudadano.documento),
        "fecha": texto(_FECHA, v=v.fecha_asignacion),
        "badge": _tono_estado(v.estado),
        "estado_label": v.get_estado_display(),
    }


def _pagina(context, request):
    page = context["vouchers_page_obj"]
    contexto = Context({"request": request, "query": context["search_query"]})
    return {
        "is_paginated": bool(context["vouchers_is_paginated"]),
        "number": page.number,
        "num_pages": page.paginator.num_pages,
        "count": page.paginator.count,
        "previous": page.previous_page_number() if page.has_previous() else None,
        "next": page.next_page_number() if page.has_next() else None,
        "range": [
            "…" if n in ("...", "…") else n for n in build_compact_page_range(page)
        ],
        "query_prefix": unescape(_QUERY.render(contexto)),
        "shown": len(context["vouchers"]) > 0,
    }


class ParametriaDetailWebView(VatNativeReadView):
    """``GET .../vouchers/parametrias/<pk>/``: ``parametria_detail.html``."""

    native_class = VoucherParametriaDetailView
    codigos = ["VAT.view_voucher"]

    def get(self, request, pk):
        vista, c = self.detalle(pk)
        p = vista.object
        django_request = request._request  # pylint: disable=protected-access
        total = c["total"]
        return Response(
            {
                "id": p.pk,
                "nombre": p.nombre,
                "descripcion": p.descripcion or "",
                "programa": str(p.programa),
                "cantidad_inicial": p.cantidad_inicial,
                "vencimiento": texto(_FECHA, v=p.fecha_vencimiento),
                "renovacion_mensual": bool(p.renovacion_mensual),
                "cantidad_renovacion": p.cantidad_renovacion or None,
                "renovacion_tipo_label": p.get_renovacion_tipo_display(),
                "inscripcion_unica_activa": bool(p.inscripcion_unica_activa),
                "activa": bool(p.activa),
                "total": total,
                "activos": c["activos"],
                "agotados": c["agotados"],
                "vencidos": c["vencidos"],
                "cancelados": c["cancelados"],
                "creditos_emitidos": c["creditos_emitidos"],
                "creditos_usados": c["creditos_usados"],
                "creditos_disponibles": c["creditos_disponibles"],
                "pct_uso": c["pct_uso"],
                "pct_activos": c["pct_activos"],
                "pct_agotados": _porcentaje(c["agotados"], total),
                "pct_vencidos": _porcentaje(c["vencidos"], total),
                "pct_cancelados": _porcentaje(c["cancelados"], total),
                "ultimas": [_ultima(v) for v in c["ultimas"]],
                "vouchers": [_fila(v) for v in c["vouchers"]],
                "vouchers_total_filtrados": c["vouchers_total_filtrados"],
                "search_query": c["search_query"],
                "page": _pagina(c, django_request),
                "permisos": {
                    "asignar": django_request.user.has_perm("VAT.add_voucher")
                },
                "urls": {
                    "list": reverse("vat_voucher_parametria_list"),
                    "detail": reverse("vat_voucher_parametria_detail", args=[p.pk]),
                    "asignar": reverse("vat_voucher_parametria_asignar", args=[p.pk]),
                    "asignar_masivo": reverse(
                        "vat_voucher_parametria_asignar_masivo", args=[p.pk]
                    ),
                },
                "messages": mensajes_pendientes(django_request),
            }
        )


class _AsignarWebView(VatNativeReadView):
    """POST que ejecuta la vista nativa y devuelve su redirección al detalle."""

    http_method_names = ["post"]
    codigos = ["VAT.add_voucher"]

    def post(self, request, pk):
        vista = self.native(pk=pk)
        try:
            respuesta = vista.post(vista.request, pk=pk)
        except Http404 as exc:
            raise NotFound() from exc
        return Response({"ok": True, "redirect": respuesta["Location"]})


class ParametriaAsignarWebView(_AsignarWebView):
    """``POST .../parametrias/<pk>/asignar/``: asignación individual por DNI."""

    native_class = VoucherParametriaAsignarView


class ParametriaAsignarMasivoWebView(_AsignarWebView):
    """``POST .../parametrias/<pk>/asignar-masivo/``: asignación por lista de DNIs."""

    native_class = VoucherParametriaAsignarMasivoView
