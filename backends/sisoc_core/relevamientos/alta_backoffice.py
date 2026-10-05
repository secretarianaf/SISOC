"""Popup "Nuevo acompañamiento territorial" del backoffice.

Las opciones dependen del PROGRAMA del comedor ("FLUJO APP PNUD" §3 / §4.2),
con el mismo criterio que usa la API territorial (``linea_pnud``: nombre
normalizado y, solo si el programa no tiene nombre, el id 3/4):

- Alimentar Comunidad y cualquier otro programa (PAC): inicial, primer
  seguimiento, seguimiento posterior, seguimiento virtual y acta
  complementaria extraordinaria.
- Abordaje Comunitario - Línea Secos: inicial y FORM-PNUD-SECOS.
- Abordaje Comunitario - Línea Tradicional: inicial y FORM II A / II A.1 /
  II B / II B.1.

El servidor vuelve a validar el tipo contra el programa: nunca se confía en el
``<select>``.
"""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q

from comedores.api_views_territorial_pnud import (
    FORMULARIOS_POR_LINEA,
    formulario_permitido,
    linea_pnud,
)
from comedores.models import Comedor
from relevamientos.models import ActaComplementaria, SeguimientoPnud
from relevamientos.service import (
    TERRITORIAL_INVALIDO_ERROR,
    _parse_territorial_payload,
    _territorial_user_id_from_uid,
)
from pwa.services.accesos import get_territorial_comedor_users_for_provincia

TIPO_RELEVAMIENTO_INICIAL = "relevamiento_inicial"
PREFIJO_PNUD = "pnud_"

OPCION_INICIAL = (TIPO_RELEVAMIENTO_INICIAL, "Acompañamiento territorial inicial")
OPCIONES_SEGUIMIENTO_PAC = (
    ("primer_seguimiento", "Primer seguimiento"),
    ("seguimiento_posterior", "Seguimiento posterior"),
    ("seguimiento_virtual", "Seguimiento virtual"),
)
TIPO_ACTA_COMPLEMENTARIA = "acta_complementaria"
# El acta de excepción ya no se ofrece en el popup (H5): la visita no realizada
# se registra dentro de cada formulario de la app. En su lugar va el acta
# complementaria extraordinaria (§12), que es de Alimentar Comunidad.
OPCION_ACTA_COMPLEMENTARIA = (
    TIPO_ACTA_COMPLEMENTARIA,
    "Acta complementaria extraordinaria",
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
        return [OPCION_INICIAL, *OPCIONES_SEGUIMIENTO_PAC, OPCION_ACTA_COMPLEMENTARIA]
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


# Un registro "sin terminar" (sin cargar o enviado y todavía sin revisar)
# bloquea una segunda asignación igual: "A subsanar" y "Validado" no.
_SIN_TERMINAR = Q(estado_validacion__isnull=True) | Q(
    estado_validacion=SeguimientoPnud.ESTADO_VALIDACION_PENDIENTE
)


def _bloquear_comedor(comedor):
    """Serializa las asignaciones concurrentes sobre el mismo comedor."""
    list(Comedor.objects.select_for_update().filter(pk=comedor.pk).values("pk"))


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
    with transaction.atomic():
        _bloquear_comedor(comedor)
        if (
            SeguimientoPnud.objects.filter(
                comedor=comedor, tecnico=tecnico, formulario=formulario
            )
            .filter(_SIN_TERMINAR)
            .exists()
        ):
            raise ValidationError(
                "El territorial ya tiene este formulario asignado en este comedor "
                "sin terminar (sin cargar o pendiente de validación)."
            )
        return _crear_pnud(comedor, tecnico, formulario)


def _crear_pnud(comedor, tecnico, formulario):
    return SeguimientoPnud.objects.create(
        comedor=comedor,
        tecnico=tecnico,
        formulario=formulario,
        datos={},
        origen=SeguimientoPnud.ORIGEN_SISOC,
        asignado_desde_sisoc=True,
        estado_validacion=None,
    )


def crear_acta_complementaria_asignada(comedor, raw_territorial_data):
    """Acta complementaria extraordinaria creada desde SISOC y asignada a un
    territorial (H5). Nace sin prestaciones ni envío: el territorial la
    completa desde la app."""
    tecnico = territorial_asignable(comedor, raw_territorial_data)
    with transaction.atomic():
        _bloquear_comedor(comedor)
        if (
            ActaComplementaria.objects.filter(comedor=comedor, tecnico=tecnico)
            .filter(_SIN_TERMINAR)
            .exists()
        ):
            raise ValidationError(
                "El territorial ya tiene un acta complementaria de este comedor "
                "sin terminar (sin cargar o pendiente de validación)."
            )
        return ActaComplementaria.objects.create(
            comedor=comedor,
            tecnico=tecnico,
            origen=ActaComplementaria.ORIGEN_SISOC,
            asignado_desde_sisoc=True,
        )
