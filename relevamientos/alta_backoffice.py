"""Popup "Nuevo acompañamiento territorial" del backoffice.

Las opciones dependen del PROGRAMA del comedor ("FLUJO APP PNUD" §3 / §4.2),
con el mismo criterio que usa la API territorial (``linea_pnud``: nombre
normalizado y, solo si el programa no tiene nombre, el id 3/4):

- Alimentar Comunidad y cualquier otro programa (PAC): inicial, primer
  seguimiento, seguimiento posterior, seguimiento virtual y acta de excepción.
- Abordaje Comunitario - Línea Secos: inicial y FORM-PNUD-SECOS.
- Abordaje Comunitario - Línea Tradicional: inicial y FORM II A / II A.1 /
  II B / II B.1.

El servidor vuelve a validar el tipo contra el programa: nunca se confía en el
``<select>``.
"""

from django.core.exceptions import ValidationError

from comedores.api_views_territorial_pnud import (
    FORMULARIOS_POR_LINEA,
    formulario_permitido,
    linea_pnud,
)
from relevamientos.models import SeguimientoPnud
from relevamientos.service import (
    TERRITORIAL_INVALIDO_ERROR,
    _parse_territorial_payload,
    _territorial_user_id_from_uid,
)
from users.services_pwa import get_territorial_comedor_users_for_provincia

TIPO_RELEVAMIENTO_INICIAL = "relevamiento_inicial"
PREFIJO_PNUD = "pnud_"

OPCION_INICIAL = (TIPO_RELEVAMIENTO_INICIAL, "Acompañamiento territorial inicial")
OPCIONES_SEGUIMIENTO_PAC = (
    ("primer_seguimiento", "Primer seguimiento"),
    ("seguimiento_posterior", "Seguimiento posterior"),
    ("seguimiento_virtual", "Seguimiento virtual"),
    ("acta_excepcion", "Acta de excepción (visita no realizada)"),
)
_ETIQUETAS_PNUD = {
    SeguimientoPnud.FORMULARIO_SECOS: "Seguimiento Puntos de Entrega (SECOS)",
    SeguimientoPnud.FORMULARIO_II_A: "FORM II A — Presencial · Vianda",
    SeguimientoPnud.FORMULARIO_II_A1: "FORM II A.1 — Virtual · Presencial y Vianda",
    SeguimientoPnud.FORMULARIO_II_B: "FORM II B — Presencial · Módulo",
    SeguimientoPnud.FORMULARIO_II_B1: "FORM II B.1 — Virtual · Módulo",
}


def valor_pnud(formulario):
    return f"{PREFIJO_PNUD}{formulario}"


def formulario_de_valor(valor):
    """``"pnud_iia"`` -> ``"iia"``; ``None`` si el valor no es de un PNUD."""
    if not isinstance(valor, str) or not valor.startswith(PREFIJO_PNUD):
        return None
    return valor[len(PREFIJO_PNUD) :]


def opciones_seguimiento_pac(comedor):
    """Instancias PAC que se cuelgan de un relevamiento (vacío en PNUD)."""
    if linea_pnud(comedor) is not None:
        return []
    return list(OPCIONES_SEGUIMIENTO_PAC)


def opciones_alta(comedor):
    """Opciones ``(valor, etiqueta)`` del popup según el programa del comedor."""
    linea = linea_pnud(comedor)
    if linea is None:
        return [OPCION_INICIAL, *OPCIONES_SEGUIMIENTO_PAC]
    return [OPCION_INICIAL] + [
        (valor_pnud(formulario), _ETIQUETAS_PNUD[formulario])
        for formulario in FORMULARIOS_POR_LINEA[linea]
    ]


def valores_permitidos(comedor):
    return {valor for valor, _ in opciones_alta(comedor)}


def territorial_asignable(comedor, raw_territorial_data):
    """Usuario territorial elegido en el popup, con alcance en la provincia del
    comedor (la misma lista que ofrece el autocompletado)."""
    territorial_uid, _ = _parse_territorial_payload(raw_territorial_data)
    user_id = _territorial_user_id_from_uid(territorial_uid)
    usuario = (
        get_territorial_comedor_users_for_provincia(comedor.provincia_id)
        .filter(id=user_id)
        .first()
        if user_id is not None
        else None
    )
    if usuario is None:
        raise ValidationError(TERRITORIAL_INVALIDO_ERROR)
    return usuario


def crear_seguimiento_pnud_asignado(comedor, raw_territorial_data, formulario):
    """Seguimiento PNUD (N22) creado desde SISOC y asignado a un territorial.

    Nace vacío y sin enviar (``estado_validacion=None``), con ``origen=sisoc``:
    la app lo ve en ``GET .../seguimientos-pnud/`` (es del propio técnico) y lo
    completa con el ``PATCH`` de corrección, que lo pasa a "Pendiente
    validación coordinador".
    """
    if not formulario_permitido(comedor, formulario):
        raise ValidationError(
            "El formulario elegido no corresponde al programa del comedor."
        )
    tecnico = territorial_asignable(comedor, raw_territorial_data)
    return SeguimientoPnud.objects.create(
        comedor=comedor,
        tecnico=tecnico,
        formulario=formulario,
        datos={},
        origen=SeguimientoPnud.ORIGEN_SISOC,
        asignado_desde_sisoc=True,
        estado_validacion=None,
    )
