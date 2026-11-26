"""Estructura de datos de salida PAS (planilla "ESTRUCTURA DE DATOS SALIDA").

La usa la nómina de pago para BNA. Los campos que PAS todavía no registra
(retroactivos, tarea, observación, fuente y ticket) salen vacíos. La
exportación a SINTyS usa su propio formato de envío (``cruces_service``).
"""

from decimal import Decimal

PROGRAMA = "PAS"
MONTO_ASIGNACION_MENSUAL = Decimal("78000.00")

COLUMNAS_SALIDA = (
    "idPersona",
    "Programa",
    "Apellidos",
    "Nombres",
    "DNI",
    "CUIT",
    "Provincia",
    "Municipio",
    "MES CURSO",
    "RETRO 1",
    "RETRO 2",
    "TAREA",
    "OBSERVACION",
    "FUENTE",
    "NRO TICKET",
)


def formato_moneda(monto):
    """Formato MONEDA de la planilla: dos decimales con punto, sin separador de miles."""

    if monto is None or monto == "":
        return ""
    return f"{Decimal(monto):.2f}"


def fila_salida(persona, monto=None):
    """Fila de la estructura de salida para un titular, en el orden de las columnas.

    ``persona`` debe traer ``provincia`` y ``municipio`` (select_related).
    """

    return (
        persona.id_persona,
        PROGRAMA,
        persona.apellidos,
        persona.nombres,
        persona.dni,
        persona.cuit or "",
        persona.provincia.nombre if persona.provincia_id else "",
        persona.municipio.nombre if persona.municipio_id else "",
        formato_moneda(monto),
        "",
        "",
        "",
        "",
        "",
        "",
    )
