"""Borradores: upsert idempotente por ``uuid`` y ``revision``.

La app sube el borrador en cada cambio. El servidor guarda la mayor revisión:
una revisión menor o igual (reintento o llegada fuera de orden) responde 200
con la guardada y no cambia nada. Un borrador finalizado no se modifica (409).
"""

from django.db import IntegrityError, transaction
from django.utils import timezone

from inspecciones.models import Escuela, EventoInspeccion, Inspeccion
from inspecciones.services.auditoria import registrar_evento
from inspecciones.services.errores import Conflicto, DatosInvalidos, NoEncontrado
from inspecciones.services.formato import (
    fecha_desde_texto,
    fecha_hora_desde_texto,
    iso,
)
from inspecciones.services.formularios import VERSION_ACTUAL

MENSAJE_FINALIZADA = "La inspección ya está finalizada."


def revision_del_payload(payload):
    if not isinstance(payload, dict):
        raise DatosInvalidos("El cuerpo debe ser un objeto JSON.")
    revision = payload.get("revision")
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
        raise DatosInvalidos(
            "La revisión debe ser un entero mayor a cero.",
            errores={"revision": "Entero mayor a cero."},
        )
    return revision


def _texto(valor):
    return valor.strip() if isinstance(valor, str) else ""


def aplicar_payload(inspeccion, payload, revision):
    """Guarda el cuerpo tal cual llegó y desnormaliza lo que sirve para buscar."""
    escuela = payload.get("escuela") if isinstance(payload.get("escuela"), dict) else {}
    respuestas = (
        payload.get("respuestas") if isinstance(payload.get("respuestas"), dict) else {}
    )
    catalogo_id = _texto(escuela.get("catalogo_id"))
    inspeccion.payload = {k: v for k, v in payload.items() if k != "uuid"}
    inspeccion.revision = revision
    inspeccion.formulario_version = (
        _texto(payload.get("formulario_version")) or VERSION_ACTUAL
    )[:20]
    inspeccion.escuela = (
        Escuela.objects.filter(codigo=catalogo_id).first() if catalogo_id else None
    )
    inspeccion.escuela_carga_manual = escuela.get("carga_manual") is True or (
        inspeccion.escuela is None
    )
    inspeccion.fecha_visita = fecha_desde_texto(payload.get("fecha_visita"))
    inspeccion.turno = _texto(payload.get("turno"))[:20]
    inspeccion.resultado = _texto(respuestas.get("resultado"))[:20]
    inspeccion.creada_cliente_at = fecha_hora_desde_texto(payload.get("creada_at"))
    inspeccion.actualizada_cliente_at = fecha_hora_desde_texto(
        payload.get("actualizada_at")
    )
    inspeccion.guardada_at = timezone.now()


def asegurar_inspeccion(user, inspeccion_uuid):
    """Fila de la inspección (vacía, revisión 0, si todavía no existe).

    Se crea en su propia transacción corta: la operación que sigue bloquea la
    fila con ``select_for_update``. Dos pedidos simultáneos con el mismo uuid
    terminan en la misma fila (el segundo recibe ``IntegrityError`` y la lee).
    """
    existente = Inspeccion.all_objects.filter(uuid=inspeccion_uuid).first()
    if existente is not None:
        return existente
    try:
        with transaction.atomic():
            return Inspeccion.objects.create(uuid=inspeccion_uuid, inspector=user)
    except IntegrityError:
        return Inspeccion.all_objects.get(uuid=inspeccion_uuid)


def bloquear_propia(user, inspeccion_uuid):
    """Inspección propia bloqueada para escribir (ajena: 404)."""
    inspeccion = (
        Inspeccion.all_objects.select_for_update().filter(uuid=inspeccion_uuid).first()
    )
    if inspeccion is None or inspeccion.inspector_id != user.pk:
        raise NoEncontrado()
    return inspeccion


def numero_de_acta(inspeccion):
    acta = getattr(inspeccion, "acta", None)
    return acta.numero if acta else None


def rechazar_si_finalizada(inspeccion):
    if inspeccion.estado == Inspeccion.Estado.FINALIZADA:
        raise Conflicto(MENSAJE_FINALIZADA, numero=numero_de_acta(inspeccion))


def _respuesta(inspeccion):
    return {
        "uuid": str(inspeccion.uuid),
        "revision": inspeccion.revision,
        "guardado_at": iso(inspeccion.guardada_at),
    }


def guardar_borrador(user, inspeccion_uuid, payload):
    revision = revision_del_payload(payload)
    asegurar_inspeccion(user, inspeccion_uuid)
    with transaction.atomic():
        inspeccion = bloquear_propia(user, inspeccion_uuid)
        rechazar_si_finalizada(inspeccion)
        if revision <= inspeccion.revision:
            # Reintento repetido o fuera de orden: no pisa una revisión más nueva.
            return _respuesta(inspeccion)
        es_nueva = inspeccion.revision == 0
        aplicar_payload(inspeccion, payload, revision)
        inspeccion.deleted_at = None
        inspeccion.deleted_by = None
        inspeccion.save()
        registrar_evento(
            inspeccion=inspeccion,
            accion=(
                EventoInspeccion.Accion.CREADA
                if es_nueva
                else EventoInspeccion.Accion.EDITADA
            ),
            actor=user,
            at=(inspeccion.creada_cliente_at if es_nueva else None),
            detalle={"revision": revision},
        )
    return _respuesta(inspeccion)


def representar_borrador(inspeccion):
    """Mismo cuerpo del PUT más ``uuid`` (y la revisión guardada)."""
    return {
        **inspeccion.payload,
        "uuid": str(inspeccion.uuid),
        "revision": inspeccion.revision,
    }


def listar_borradores(user):
    """Borradores propios sin cerrar, para recuperarlos en otro dispositivo."""
    borradores = Inspeccion.objects.filter(
        inspector=user, estado=Inspeccion.Estado.BORRADOR, revision__gt=0
    ).order_by("-guardada_at")
    return [representar_borrador(inspeccion) for inspeccion in borradores]


def descartar_borrador(user, inspeccion_uuid):
    """Baja lógica de un borrador propio. Repetirla no es error."""
    with transaction.atomic():
        inspeccion = (
            Inspeccion.all_objects.select_for_update()
            .filter(uuid=inspeccion_uuid)
            .first()
        )
        if inspeccion is None:
            return
        if inspeccion.inspector_id != user.pk:
            raise NoEncontrado()
        rechazar_si_finalizada(inspeccion)
        if inspeccion.deleted_at is not None:
            return
        inspeccion.delete(user=user, cascade=False)
        registrar_evento(
            inspeccion=inspeccion,
            accion=EventoInspeccion.Accion.DESCARTADA,
            actor=user,
        )
