"""Asignaciones por jornada en el backoffice: listado con estado, alta y baja.

Estado de cada asignación (escuela + inspector + jornada):

- ``finalizada``: hay un acta válida (no anulada) de ese inspector para esa
  escuela en esa jornada;
- ``en_curso``: hay un borrador con datos de esa visita;
- ``pendiente``: ninguna de las dos.

Una asignación se puede quitar sólo si no tiene acta (ni siquiera anulada):
el acta es evidencia de la visita. La misma escuela puede asignarse el mismo
día a otro inspector (cuenta como otra visita); al mismo inspector, no.
"""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q

from inspecciones.models import Acta, AsignacionEscuela, Inspeccion
from inspecciones.services.formato import iniciales, nombre_actor
from users.services_inspecciones import (
    ROL_INSPECTOR,
    ROLES_INSPECCIONES,
    es_inspector_solo_app,
)

MIN_BUSQUEDA = 3
MAX_RESULTADOS = 20

ESTADO_PENDIENTE = "pendiente"
ESTADO_EN_CURSO = "en_curso"
ESTADO_FINALIZADA = "finalizada"
ESTADOS = (
    (ESTADO_PENDIENTE, "Pendiente"),
    (ESTADO_EN_CURSO, "En curso"),
    (ESTADO_FINALIZADA, "Finalizada"),
)

# Filtro por estado del acta, compartido con el listado de actas.
ESTADO_ACTA_VALIDAS = "validas"
ESTADO_ACTA_ANULADAS = "anuladas"
ESTADO_ACTA_PRUEBA = "prueba"
ESTADOS_ACTA = (
    (ESTADO_ACTA_VALIDAS, "Válidas"),
    (ESTADO_ACTA_ANULADAS, "Anuladas"),
    (ESTADO_ACTA_PRUEBA, "De prueba"),
)


def acta_cumple_estado(acta, estado_acta):
    if not estado_acta:
        return True
    if estado_acta == ESTADO_ACTA_VALIDAS:
        return acta.estado == Acta.Estado.FINALIZADA and not acta.es_prueba
    if estado_acta == ESTADO_ACTA_ANULADAS:
        return acta.estado == Acta.Estado.ANULADA
    if estado_acta == ESTADO_ACTA_PRUEBA:
        return acta.es_prueba
    return True


def es_acta_de_indicadores(acta):
    """Cuenta en los totales: ni anulada ni de prueba."""
    return acta.estado == Acta.Estado.FINALIZADA and not acta.es_prueba


# --- Inspectores ---------------------------------------------------------


def inspectores(*, texto="", solo_inspectores=True):
    """Usuarios activos del programa; por defecto sólo con rol inspector."""
    roles = [ROL_INSPECTOR] if solo_inspectores else sorted(ROLES_INSPECCIONES)
    queryset = get_user_model().objects.filter(
        is_active=True,
        profile__es_inspector_escolar=True,
        profile__inspecciones_rol__in=roles,
    )
    texto = (texto or "").strip()
    if texto:
        filtro = (
            Q(username__icontains=texto)
            | Q(first_name__icontains=texto)
            | Q(last_name__icontains=texto)
        )
        if texto.replace(".", "").isdigit():
            filtro |= Q(profile__dni__startswith=texto.replace(".", ""))
        queryset = queryset.filter(filtro)
    return queryset.select_related("profile").order_by(
        "last_name", "first_name", "username"
    )


def opcion_inspector(user):
    dni = getattr(getattr(user, "profile", None), "dni", "") or ""
    detalle = " · ".join(p for p in (user.get_username(), dni and f"DNI {dni}") if p)
    return {"id": user.pk, "text": nombre_actor(user), "detalle": detalle}


def opcion_inspector_por_id(user_id):
    """Opción ya elegida para precargar el Select2 del filtro, o ``None``."""
    if not user_id:
        return None
    user = get_user_model().objects.select_related("profile").filter(pk=user_id).first()
    return opcion_inspector(user) if user else None


def buscar_inspectores(texto, *, solo_inspectores=True):
    texto = (texto or "").strip()
    if len(texto) < MIN_BUSQUEDA:
        return []
    usuarios = inspectores(texto=texto, solo_inspectores=solo_inspectores)
    return [opcion_inspector(u) for u in usuarios[:MAX_RESULTADOS]]


def es_inspector(user):
    return es_inspector_solo_app(user)


# --- Listado por jornada -------------------------------------------------


def _actas_por_visita(asignaciones, fecha):
    escuelas = {a.escuela_id for a in asignaciones}
    inspectores_ids = {a.inspector_id for a in asignaciones}
    actas = {}
    queryset = Acta.objects.filter(
        fecha_visita=fecha,
        escuela_id__in=escuelas,
        inspector_id__in=inspectores_ids,
    ).order_by("cerrada_at")
    for acta in queryset:
        actas.setdefault((acta.escuela_id, acta.inspector_id), []).append(acta)
    return actas


def _borradores(asignaciones, fecha):
    return set(
        Inspeccion.objects.filter(
            estado=Inspeccion.Estado.BORRADOR,
            revision__gt=0,
            fecha_visita=fecha,
            escuela_id__in={a.escuela_id for a in asignaciones},
            inspector_id__in={a.inspector_id for a in asignaciones},
        ).values_list("escuela_id", "inspector_id")
    )


def _fila(asignacion, actas, en_curso):
    validas = [a for a in actas if a.estado == Acta.Estado.FINALIZADA]
    if validas:
        estado = ESTADO_FINALIZADA
    elif en_curso:
        estado = ESTADO_EN_CURSO
    else:
        estado = ESTADO_PENDIENTE
    inspector = asignacion.inspector
    return {
        "asignacion": asignacion,
        "escuela": asignacion.escuela,
        "inspector": inspector,
        "iniciales": iniciales(inspector.get_full_name() or inspector.get_username()),
        "estado": estado,
        "estado_display": dict(ESTADOS)[estado],
        "actas": actas,
        "se_puede_quitar": not actas,
    }


def asignaciones_de_jornada(
    fecha,
    *,
    inspector_id=None,
    escuela_id=None,
    provincia_id=None,
    estado="",
    estado_acta="",
):
    """``(filas, totales)`` de la jornada; los totales ignoran los estados."""
    queryset = AsignacionEscuela.objects.filter(fecha=fecha).select_related(
        "escuela__provincia", "inspector__profile"
    )
    if inspector_id:
        queryset = queryset.filter(inspector_id=inspector_id)
    if escuela_id:
        queryset = queryset.filter(escuela_id=escuela_id)
    if provincia_id:
        queryset = queryset.filter(escuela__provincia_id=provincia_id)
    asignaciones = list(
        queryset.order_by(
            "inspector__last_name", "inspector__first_name", "escuela__nombre", "id"
        )
    )
    actas = _actas_por_visita(asignaciones, fecha)
    borradores = _borradores(asignaciones, fecha)
    filas = []
    for asignacion in asignaciones:
        clave = (asignacion.escuela_id, asignacion.inspector_id)
        filas.append(_fila(asignacion, actas.get(clave, []), clave in borradores))
    totales = {
        "total": len(filas),
        ESTADO_PENDIENTE: sum(f["estado"] == ESTADO_PENDIENTE for f in filas),
        ESTADO_EN_CURSO: sum(f["estado"] == ESTADO_EN_CURSO for f in filas),
        # Finalizadas que cuentan en los indicadores: sin anuladas ni de prueba.
        ESTADO_FINALIZADA: sum(
            any(es_acta_de_indicadores(a) for a in f["actas"]) for f in filas
        ),
        "inspectores": len({f["inspector"].pk for f in filas}),
    }
    if estado:
        filas = [f for f in filas if f["estado"] == estado]
    if estado_acta:
        filas = [
            f
            for f in filas
            if any(acta_cumple_estado(a, estado_acta) for a in f["actas"])
        ]
    return filas, totales


# --- Alta y baja ---------------------------------------------------------


def otras_asignaciones(escuela, fecha, *, excluir_inspector_id=None):
    """Inspectores que ya tienen asignada la escuela en esa jornada."""
    queryset = AsignacionEscuela.objects.filter(
        escuela=escuela, fecha=fecha
    ).select_related("inspector")
    if excluir_inspector_id:
        queryset = queryset.exclude(inspector_id=excluir_inspector_id)
    return [nombre_actor(a.inspector) for a in queryset.order_by("id")]


def crear_asignacion(*, escuela, inspector, fecha, actor):
    """Crea (o restaura, si se había quitado) la asignación.

    La misma escuela con otro inspector se permite: es otra visita. Con el
    mismo inspector y la misma jornada ya existe y se rechaza.
    """
    if not es_inspector(inspector):
        raise ValidationError("El usuario no es inspector de Inspecciones escolares.")
    with transaction.atomic():
        existente = (
            AsignacionEscuela.all_objects.select_for_update()
            .filter(escuela=escuela, inspector=inspector, fecha=fecha)
            .first()
        )
        if existente is not None and existente.deleted_at is None:
            raise ValidationError(
                "Esa escuela ya está asignada a ese inspector en esa jornada."
            )
        if existente is not None:
            existente.restore(user=actor, cascade=False)
            return existente
        return AsignacionEscuela.objects.create(
            escuela=escuela, inspector=inspector, fecha=fecha, creada_por=actor
        )


def tiene_acta(asignacion):
    return Acta.objects.filter(
        escuela_id=asignacion.escuela_id,
        inspector_id=asignacion.inspector_id,
        fecha_visita=asignacion.fecha,
    ).exists()


def quitar_asignacion(asignacion, *, actor):
    if tiene_acta(asignacion):
        raise ValidationError(
            "No se puede quitar: la visita ya tiene un acta para esa jornada."
        )
    asignacion.delete(user=actor, cascade=False)
