"""Catálogo de escuelas, asignaciones de la jornada y ficha con visitas de hoy."""

from django.db.models import Q

from inspecciones.models import Acta, AsignacionEscuela, Escuela, Inspeccion
from inspecciones.services.errores import NoEncontrado
from inspecciones.services.formato import hoy, iso

MIN_BUSQUEDA = 3
MAX_RESULTADOS = 20


def serializar_escuela(escuela):
    return {
        "id": escuela.codigo,
        "nombre": escuela.nombre,
        "cue": escuela.cue,
        "distrito": escuela.distrito,
        "localidad": escuela.localidad,
        "domicilio": escuela.domicilio,
        "nivel": escuela.nivel,
    }


def escuelas_asignadas(user):
    """Escuelas de la jornada de hoy con el estado propio de cada una.

    ``finalizada``: hay un acta propia de hoy; ``borrador``: hay un borrador
    propio sin cerrar; ``pendiente``: ninguna de las dos.
    """
    jornada = hoy()
    asignaciones = (
        AsignacionEscuela.objects.filter(
            inspector=user, fecha=jornada, escuela__deleted_at__isnull=True
        )
        .select_related("escuela")
        .order_by("escuela__nombre")
    )
    escuela_ids = [a.escuela_id for a in asignaciones]
    finalizadas = set(
        Acta.objects.filter(
            inspector=user,
            escuela_id__in=escuela_ids,
            fecha_visita=jornada,
            estado=Acta.Estado.FINALIZADA,
        ).values_list("escuela_id", flat=True)
    )
    con_borrador = set(
        Inspeccion.objects.filter(
            inspector=user,
            escuela_id__in=escuela_ids,
            estado=Inspeccion.Estado.BORRADOR,
            revision__gt=0,
        ).values_list("escuela_id", flat=True)
    )
    resultado = []
    for asignacion in asignaciones:
        escuela_id = asignacion.escuela_id
        if escuela_id in finalizadas:
            estado = "finalizada"
        elif escuela_id in con_borrador:
            estado = "borrador"
        else:
            estado = "pendiente"
        resultado.append({**serializar_escuela(asignacion.escuela), "estado": estado})
    return resultado


def buscar_escuelas(texto):
    """Por nombre, CUE, domicilio o localidad: mínimo 3 caracteres, hasta 20."""
    texto = (texto or "").strip()
    if len(texto) < MIN_BUSQUEDA:
        return []
    filtro = (
        Q(nombre__icontains=texto)
        | Q(cue__icontains=texto)
        | Q(domicilio__icontains=texto)
        | Q(localidad__icontains=texto)
    )
    escuelas = Escuela.objects.filter(filtro).order_by("nombre")[:MAX_RESULTADOS]
    return [serializar_escuela(escuela) for escuela in escuelas]


def obtener_escuela(codigo):
    escuela = Escuela.objects.filter(codigo=codigo).first()
    if escuela is None:
        raise NoEncontrado()
    return escuela


def visitas_de_hoy(escuela, user, *, jornada=None, excluir_inspeccion_id=None):
    """Actas válidas de la escuela en la jornada (de cualquier inspector)."""
    actas = Acta.objects.filter(
        escuela=escuela,
        fecha_visita=jornada or hoy(),
        estado=Acta.Estado.FINALIZADA,
    ).order_by("cerrada_at")
    if excluir_inspeccion_id:
        actas = actas.exclude(inspeccion_id=excluir_inspeccion_id)
    return [
        {
            "turno": acta.turno,
            "numero": acta.numero,
            "cerrada_at": iso(acta.cerrada_at),
            "propia": acta.inspector_id == user.pk,
        }
        for acta in actas
    ]


def ficha_escuela(codigo, user):
    escuela = obtener_escuela(codigo)
    return {
        **serializar_escuela(escuela),
        "visitas_hoy": visitas_de_hoy(escuela, user),
    }
