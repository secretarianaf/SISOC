"""Alcance por rol: el inspector ve lo propio, coordinación ve todo.

Lo ajeno responde 404 (``NoEncontrado``), igual que lo inexistente, para no
revelar que existe. Las escrituras son siempre del autor: coordinación
consulta, pero no modifica inspecciones ni actas de otros (especificación §2).
"""

from inspecciones.models import Acta, ImagenInspeccion, Inspeccion
from inspecciones.services.errores import NoEncontrado
from users.services_inspecciones import es_coordinacion_inspecciones


def ve_todo(user):
    return es_coordinacion_inspecciones(user)


def inspecciones_visibles(user):
    queryset = Inspeccion.objects.all()
    if ve_todo(user):
        return queryset
    return queryset.filter(inspector=user)


def actas_visibles(user):
    queryset = Acta.objects.select_related("inspeccion", "inspector", "escuela")
    if ve_todo(user):
        return queryset
    return queryset.filter(inspector=user)


def acta_visible(user, numero):
    acta = actas_visibles(user).filter(numero=numero).first()
    if acta is None:
        raise NoEncontrado()
    return acta


def acta_propia(user, numero, *, bloquear=False):
    queryset = Acta.objects.filter(numero=numero, inspector=user)
    if bloquear:
        queryset = queryset.select_for_update()
    acta = queryset.first()
    if acta is None:
        raise NoEncontrado()
    return acta


def imagen_visible(user, imagen_uuid):
    queryset = ImagenInspeccion.objects.select_related("inspeccion")
    if not ve_todo(user):
        queryset = queryset.filter(inspeccion__inspector=user)
    imagen = queryset.filter(uuid=imagen_uuid).first()
    if imagen is None:
        raise NoEncontrado()
    return imagen
