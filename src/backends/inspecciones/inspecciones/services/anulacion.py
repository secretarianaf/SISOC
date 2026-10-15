"""Anulación de actas y marca de acta de prueba (especificación §7 y §9).

La anulación es de coordinación: conserva número, instantánea, PDF,
notificaciones e historial; sólo cambia el estado y deja quién, cuándo y por
qué. Un acta anulada queda fuera de las actas válidas: la escuela vuelve a
"pendiente" en la jornada y se puede registrar otra visita sin pisar la
anterior. La marca de prueba saca el acta de los indicadores de producción.

Quién puede hacerlo lo decide la vista (``puede_gestionar_inspecciones``).
"""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from inspecciones.models import Acta, EventoInspeccion
from inspecciones.services.auditoria import registrar_evento

MIN_MOTIVO = 10

# ``EventoInspeccion.Accion`` no tiene una acción propia para la marca de
# prueba y sumarla exige una migración. Se registra como ``editada`` con el
# campo en el detalle; ``editada`` no se muestra en el historial del acta.
ACCION_MARCA_PRUEBA = EventoInspeccion.Accion.EDITADA


def _bloquear(acta):
    return Acta.objects.select_for_update().select_related("inspeccion").get(pk=acta.pk)


def _validar_motivo(motivo):
    texto = motivo.strip() if isinstance(motivo, str) else ""
    if len(" ".join(texto.split())) < MIN_MOTIVO:
        raise ValidationError(
            f"Indicá el motivo de la anulación (al menos {MIN_MOTIVO} caracteres)."
        )
    return texto


def _rechazar_si_anulada(acta, mensaje):
    if acta.estado == Acta.Estado.ANULADA:
        raise ValidationError(mensaje.format(numero=acta.numero))


def anular_acta(acta, motivo, actor):
    """Anula el acta con motivo. ``ValidationError`` si el motivo es corto o
    el acta ya estaba anulada. Devuelve el acta actualizada."""
    texto = _validar_motivo(motivo)
    with transaction.atomic():
        bloqueada = _bloquear(acta)
        _rechazar_si_anulada(bloqueada, "El acta {numero} ya está anulada.")
        bloqueada.estado = Acta.Estado.ANULADA
        bloqueada.anulada_at = timezone.now()
        bloqueada.anulada_por = actor
        bloqueada.motivo_anulacion = texto
        bloqueada.save(
            update_fields=["estado", "anulada_at", "anulada_por", "motivo_anulacion"]
        )
        registrar_evento(
            inspeccion=bloqueada.inspeccion,
            acta=bloqueada,
            accion=EventoInspeccion.Accion.ANULADA,
            actor=actor,
            at=bloqueada.anulada_at,
            detalle={"numero": bloqueada.numero, "motivo": texto},
        )
    return bloqueada


def marcar_prueba(acta, es_prueba, actor):
    """Marca o desmarca el acta como de prueba. ``ValidationError`` si está
    anulada. Sin cambio de valor no registra evento. Devuelve el acta."""
    es_prueba = bool(es_prueba)
    with transaction.atomic():
        bloqueada = _bloquear(acta)
        _rechazar_si_anulada(
            bloqueada,
            "El acta {numero} está anulada: no se puede cambiar la marca de prueba.",
        )
        if bloqueada.es_prueba == es_prueba:
            return bloqueada
        bloqueada.es_prueba = es_prueba
        bloqueada.save(update_fields=["es_prueba"])
        registrar_evento(
            inspeccion=bloqueada.inspeccion,
            acta=bloqueada,
            accion=ACCION_MARCA_PRUEBA,
            actor=actor,
            detalle={"campo": "es_prueba", "es_prueba": es_prueba},
        )
    return bloqueada
