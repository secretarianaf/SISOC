"""Gestión de los usuarios de un CDI: suspender, reactivar, dar de baja y responsable.

El referente responsable (el vigente en la ficha del CDI) y quien gestiona
referentes en el territorio administran los demás accesos del centro. Al cambiar
el referente en la ficha no se da de baja al anterior: solo el responsable nuevo
decide si sigue, se suspende o se da de baja.
"""

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from centrodeinfancia.access import puede_administrar_usuarios_cdi
from centrodeinfancia.models import AccesoCDI, CentroDeInfancia

Estado = AccesoCDI.Estado

ACCION_SUSPENDER = "suspender"
ACCION_REACTIVAR = "reactivar"
ACCION_BAJA = "baja"

# acción -> (estado destino, estados de origen permitidos, requiere motivo)
TRANSICIONES = {
    ACCION_SUSPENDER: (Estado.SUSPENDIDO, {Estado.ACTIVO}, True),
    ACCION_REACTIVAR: (Estado.ACTIVO, {Estado.SUSPENDIDO}, False),
    ACCION_BAJA: (Estado.BAJA, {Estado.ACTIVO, Estado.SUSPENDIDO}, True),
}
MOTIVO_MAX_LENGTH = 500


def cambiar_estado_acceso(*, actor, acceso, accion, motivo=""):
    """Aplica una transición de estado sobre el acceso de otro usuario del CDI.

    Raises:
        PermissionDenied: el actor no administra los usuarios del CDI.
        ValidationError: transición no permitida (propio acceso, responsable,
            estado de origen inválido o motivo faltante).
    """
    if accion not in TRANSICIONES:
        raise ValidationError("Acción no válida.")
    if not puede_administrar_usuarios_cdi(actor, acceso.centro):
        raise PermissionDenied("No puede administrar los usuarios de este centro.")
    destino, origenes, requiere_motivo = TRANSICIONES[accion]
    motivo = (motivo or "").strip()
    if requiere_motivo and not motivo:
        raise ValidationError("Indicá el motivo.")
    if len(motivo) > MOTIVO_MAX_LENGTH:
        raise ValidationError(
            f"El motivo no puede superar los {MOTIVO_MAX_LENGTH} caracteres."
        )

    with transaction.atomic():
        acceso = AccesoCDI.objects.select_for_update().get(pk=acceso.pk)
        if acceso.user_id == actor.pk:
            raise ValidationError("No podés cambiar el estado de tu propio usuario.")
        if acceso.es_responsable:
            # El CDI no puede quedar sin responsable: se reemplaza cambiando el
            # referente en la ficha, y el anterior queda como referente común.
            raise ValidationError(
                "El responsable del centro no se puede suspender ni dar de baja. "
                "Para reemplazarlo, cambiá el referente en la ficha del CDI."
            )
        if acceso.estado not in origenes:
            raise ValidationError(
                f"No se puede {accion} un usuario en estado "
                f"«{acceso.get_estado_display()}»."
            )
        acceso.estado = destino
        acceso.motivo_estado = motivo
        acceso.fecha_baja = timezone.now() if destino == Estado.BAJA else None
        acceso.save(update_fields=["estado", "motivo_estado", "fecha_baja"])
    return acceso


def asignar_responsable(acceso):
    """Marca el acceso como responsable del CDI y lo activa.

    El responsable anterior queda como referente común, con su acceso tal cual.
    """
    with transaction.atomic():
        # Serializa todas las asignaciones del CDI, incluso cuando todavía no
        # tiene responsable. Bloquear solo los accesos actuales no alcanza.
        CentroDeInfancia.objects.select_for_update().get(pk=acceso.centro_id)
        # Uno por uno y no con ``update()``: así el cambio queda en la auditoría.
        anteriores = AccesoCDI.objects.filter(
            centro_id=acceso.centro_id, es_responsable=True
        ).exclude(pk=acceso.pk)
        for anterior in anteriores:
            anterior.es_responsable = False
            anterior.save(update_fields=["es_responsable"])
        acceso.es_responsable = True
        acceso.estado = Estado.ACTIVO
        acceso.motivo_estado = ""
        acceso.fecha_baja = None
        acceso.save(
            update_fields=["es_responsable", "estado", "motivo_estado", "fecha_baja"]
        )
    return acceso
