"""Transactions and execution-month cards of the comedor ficha (CO07.01): ``tablero`` keys.

Projects the two cards ``comedor_detail.html`` includes between the details row
and the card-holder card (``comedor_transacciones_card.html`` and
``comedor_mes_ejecucion_card.html``). A card is ``None`` when the template does
not draw it (``puede_ver_dw_transacciones`` / ``mostrar_mes_ejecucion``), so React
never draws a control the page does not show. Every value is rendered with the
template's own expression (``default`` / ``monto_sin_decimales``).
"""

import html

from django.urls import reverse

from comedores.web_api_comedor_ficha_datos import _render

SIN_INFO = "Sin informaci&oacute;n"


def _txt(source, **context):
    """A template expression whose literals carry HTML entities (``&oacute;``)."""
    return html.unescape(_render(source, **context))


def _transacciones(context, comedor):
    if not context.get("puede_ver_dw_transacciones"):
        return None
    resumen = context.get("resumen_dw_transacciones")

    def valor(campo):
        return _txt(
            "{{ r." + campo + '|default:"' + SIN_INFO + '" }}',
            r=resumen,
        )

    return {
        "periodo": valor("periodo_display"),
        "movimientos": valor("cantidad_debitos"),
        "transferido": valor("transferido_display"),
        "gastado": valor("gastado_display"),
        "saldo": valor("saldo_display"),
        "detalle": reverse("comedor_transacciones_detalle", args=[comedor.pk]),
    }


def _mes_ejecucion(context, comedor):
    if not context.get("mostrar_mes_ejecucion"):
        return None
    resumen = context.get("mes_ejecucion_resumen") or {}
    expediente = resumen.get("expediente")

    def valor(expresion, **datos):
        return _txt(expresion, e=expediente, r=resumen, **datos)

    return {
        "expediente": (
            {
                "convenio": valor(
                    '{{ e.expediente_convenio|default:"' + SIN_INFO + '" }}'
                ),
                "pago": valor('{{ e.expediente_pago|default:"' + SIN_INFO + '" }}'),
                "prestaciones": valor('{{ r.cantidad_prestaciones|default:"0" }}'),
                "monto": valor("${{ r.monto_total|monto_sin_decimales }}"),
                "mes_pago": valor('{{ e.mes_pago|default:"' + SIN_INFO + '" }}'),
                "ano": valor('{{ e.ano|default:"' + SIN_INFO + '" }}'),
                "mes_ejecucion": valor(
                    '{{ r.mes_ejecucion|default_if_none:"' + SIN_INFO + '" }}'
                ),
            }
            if expediente
            else None
        ),
        "ver_mas": reverse("expedientespagos_list", args=[comedor.pk]),
    }


def tarjetas(context, comedor):
    """The ``transacciones`` and ``mes_ejecucion`` keys of ``tablero``."""
    return {
        "transacciones": _transacciones(context, comedor),
        "mes_ejecucion": _mes_ejecucion(context, comedor),
    }
