"""Web API (G1 v1) de vouchers y parametrías de VAT (V01.01) para React.

``/api/web/vat/vouchers/`` corre las vistas nativas ``VoucherListView``,
``VoucherDetailView`` y ``VoucherParametriaListView`` y proyecta su contexto a
JSON. Solo lectura: la recarga y la cancelación siguen siendo los POST nativos
(``vat_voucher_recargar``, ``vat_voucher_cancelar``) que el formulario de React
envía a su URL de siempre. Acceso: ``VAT.view_voucher`` (la regla de la ruta).
"""

from django.urls import reverse
from rest_framework.response import Response

from VAT.views.voucher import VoucherDetailView, VoucherListView
from VAT.views.voucher_parametria import VoucherParametriaListView
from VAT.web_api_common import VatNativeReadView, mensajes_pendientes, texto

CODIGOS = ["VAT.view_voucher"]
_FECHA = "{{ v|date:'d/m/Y' }}"
_FECHA_HORA = "{{ v|date:'d/m/Y H:i' }}"
_DEFECTO = "{{ v|default:'—' }}"
_BARRA = "{% widthratio d i 100 %}"


def _fecha(valor):
    return texto(_FECHA, v=valor)


def fila_voucher(v):
    """Una fila de ``voucher_list.html``."""
    return {
        "id": v.pk,
        "ciudadano": v.ciudadano.nombre_completo,
        "documento": texto("{{ v }}", v=v.ciudadano.documento),
        "programa": str(v.programa),
        "disponible": v.cantidad_disponible,
        "inicial": v.cantidad_inicial,
        "vencimiento": _fecha(v.fecha_vencimiento),
        "estado": v.estado,
        "estado_label": v.get_estado_display(),
        "detail_url": reverse("vat_voucher_detail", args=[v.pk]),
    }


def fila_parametria(p):
    """Una fila de ``parametria_list.html``."""
    return {
        "id": p.pk,
        "nombre": p.nombre,
        "programa": str(p.programa),
        "cantidad_inicial": p.cantidad_inicial,
        "vencimiento": _fecha(p.fecha_vencimiento),
        "activa": bool(p.activa),
        "vouchers": p.vouchers.count(),
        "detail_url": reverse("vat_voucher_parametria_detail", args=[p.pk]),
    }


def _campo_recarga(campo):
    """Atributos que el widget nativo de ``VoucherRecargaForm`` imprime."""
    es_select = hasattr(campo.field.widget, "choices")
    return {
        "name": campo.name,
        "id": campo.id_for_label,
        "label": str(campo.label),
        "required": campo.field.required,
        "tag": "select" if es_select else "input",
        "min": getattr(campo.field, "min_value", None),
        "choices": (
            [
                {"value": str(valor), "label": str(etiqueta)}
                for valor, etiqueta in campo.field.choices
            ]
            if es_select
            else []
        ),
    }


class VoucherListWebView(VatNativeReadView):
    """``GET .../vouchers/``: ``voucher_list.html`` con su queryset nativo."""

    native_class = VoucherListView
    codigos = CODIGOS

    def get(self, request):
        return self.lista(
            lambda context, _request: {
                "results": [fila_voucher(v) for v in context["vouchers"]],
                "busqueda": request.GET.get("busqueda", ""),
                "urls": {
                    "list": reverse("vat_voucher_list"),
                    "create": reverse("vat_voucher_create"),
                },
            }
        )


class VoucherParametriaListWebView(VatNativeReadView):
    """``GET .../vouchers/parametrias/``: ``parametria_list.html``."""

    native_class = VoucherParametriaListView
    codigos = CODIGOS

    def get(self, request):
        return self.lista(
            lambda context, _request: {
                "results": [fila_parametria(p) for p in context["parametrias"]],
                "busqueda": request.GET.get("busqueda", ""),
                "urls": {
                    "list": reverse("vat_voucher_parametria_list"),
                    "create": reverse("vat_voucher_parametria_create"),
                },
            }
        )


class VoucherDetailWebView(VatNativeReadView):
    """``GET .../vouchers/<pk>/``: ``voucher_detail.html`` (acciones de crédito nativas)."""

    native_class = VoucherDetailView
    codigos = CODIGOS

    def get(self, request, pk):
        vista, context = self.detalle(pk)
        v = vista.object
        django_request = request._request  # pylint: disable=protected-access
        puede_cambiar = django_request.user.has_perm("VAT.change_voucher")
        return Response(
            {
                "id": v.pk,
                "ciudadano": v.ciudadano.nombre_completo,
                "documento": texto("{{ v }}", v=v.ciudadano.documento),
                "programa": str(v.programa),
                "estado": v.estado,
                "estado_label": v.get_estado_display(),
                "disponible": v.cantidad_disponible,
                "inicial": v.cantidad_inicial,
                "porcentaje": texto(
                    _BARRA, d=v.cantidad_disponible, i=v.cantidad_inicial
                ),
                "asignado_por": texto(_DEFECTO, v=v.asignado_por),
                "fecha_asignacion": _fecha(v.fecha_asignacion),
                "vencimiento": _fecha(v.fecha_vencimiento),
                "dias_para_vencer": context["estado_info"]["dias_para_vencer"],
                "usos": [
                    {
                        "fecha": texto(_FECHA, v=u.fecha_uso),
                        "oferta": str(u.inscripcion_oferta.oferta),
                        "cantidad": u.cantidad_usada,
                    }
                    for u in context["usos"]
                ],
                "recargas": [
                    {
                        "fecha": texto(_FECHA, v=r.fecha_recarga),
                        "motivo": texto(_DEFECTO, v=r.motivo),
                        "por": texto(_DEFECTO, v=r.autorizado_por),
                        "cantidad": r.cantidad,
                    }
                    for r in context["recargas"]
                ],
                "logs": [
                    {
                        "tipo_evento": log.tipo_evento,
                        "fecha": texto(_FECHA_HORA, v=log.fecha_evento),
                    }
                    for log in context["logs"]
                ],
                "acciones": {
                    "recargar": puede_cambiar and v.estado in ("activo", "agotado"),
                    "cancelar": puede_cambiar and v.estado != "cancelado",
                    "recargar_url": reverse("vat_voucher_recargar", args=[v.pk]),
                    "cancelar_url": reverse("vat_voucher_cancelar", args=[v.pk]),
                    "campos": [_campo_recarga(c) for c in context["recarga_form"]],
                },
                "messages": mensajes_pendientes(django_request),
            }
        )
