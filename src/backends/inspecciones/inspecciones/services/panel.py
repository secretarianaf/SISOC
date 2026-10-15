"""Totales del panel del backoffice (el dashboard de coordinación es otra etapa)."""

from datetime import datetime, time, timedelta

from django.utils import timezone

from inspecciones.models import Acta, AsignacionEscuela, Escuela, Inspeccion
from inspecciones.services.formato import hoy


def _rango_del_dia(fecha):
    # Rango explícito en vez de ``__date``: en MySQL ``__date`` con USE_TZ
    # depende de que estén cargadas las tablas de zonas horarias.
    inicio = timezone.make_aware(datetime.combine(fecha, time.min))
    return inicio, inicio + timedelta(days=1)


def resumen_panel():
    jornada = hoy()
    inicio, fin = _rango_del_dia(jornada)
    return {
        "jornada": jornada,
        "escuelas": Escuela.objects.count(),
        "asignaciones_hoy": AsignacionEscuela.objects.filter(fecha=jornada).count(),
        "borradores": Inspeccion.objects.filter(
            estado=Inspeccion.Estado.BORRADOR, revision__gt=0
        ).count(),
        "actas_hoy": Acta.objects.filter(
            cerrada_at__gte=inicio,
            cerrada_at__lt=fin,
            estado=Acta.Estado.FINALIZADA,
        ).count(),
    }
