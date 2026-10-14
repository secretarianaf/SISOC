"""Eventos de auditoría (especificación §10: actor y fecha de cada acción)."""

from django.utils import timezone

from inspecciones.models import EventoInspeccion
from inspecciones.services.formato import nombre_actor

# Las que se muestran en el historial del acta. ``editada`` se registra por
# cada revisión aceptada, pero sólo sirve para auditoría: en el detalle sería ruido.
ACCIONES_VISIBLES = (
    EventoInspeccion.Accion.CREADA,
    EventoInspeccion.Accion.FIRMADA,
    EventoInspeccion.Accion.EXCEPCION_FIRMA,
    EventoInspeccion.Accion.FINALIZADA,
    EventoInspeccion.Accion.PDF_SUBIDO,
    EventoInspeccion.Accion.NOTIFICACION_CARGADA,
    EventoInspeccion.Accion.NOTIFICACION_CORREGIDA,
    EventoInspeccion.Accion.ANULADA,
)


def registrar_evento(  # pylint: disable=too-many-arguments
    *, inspeccion, accion, actor, at=None, acta=None, actor_nombre=None, detalle=None
):
    return EventoInspeccion.objects.create(
        inspeccion=inspeccion,
        acta=acta,
        actor=actor,
        actor_nombre=actor_nombre if actor_nombre is not None else nombre_actor(actor),
        accion=accion,
        at=at or timezone.now(),
        detalle=detalle or {},
    )
