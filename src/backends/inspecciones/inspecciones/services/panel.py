"""Totales del panel del backoffice (el dashboard de coordinación es otra etapa).

Las actas anuladas y las de prueba no cuentan en los indicadores.
"""

from datetime import datetime, time, timedelta

from django.utils import timezone

from inspecciones.models import Acta, AsignacionEscuela, Escuela
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
        "escuelas_a_revisar": Escuela.objects.filter(a_revisar=True).count(),
        "asignaciones_hoy": AsignacionEscuela.objects.filter(fecha=jornada).count(),
        "actas_hoy": Acta.objects.filter(
            cerrada_at__gte=inicio,
            cerrada_at__lt=fin,
            estado=Acta.Estado.FINALIZADA,
            es_prueba=False,
        ).count(),
    }
