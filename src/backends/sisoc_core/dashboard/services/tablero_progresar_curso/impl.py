"""Tablero Becas Progresar · Curso obligatorio: datos para la pantalla.

Lee dos tablas `bi_` que arma una carga diaria del equipo de Datos (padrón de
Progresar cruzado con el curso "Proyecto de vida y economía personal" de FCH):

- `ProgresarCursoResumen`: titulares por provincia, línea, estado, género y edad.
- `ProgresarCursoEvolucion`: inscriptos y aprobados por día.

Son agregados: no hay datos de personas. Las reglas de negocio (estado del curso,
edad, tramos) se aplican en la carga; acá solo se recorta por el alcance del
usuario y se arma lo que necesita el JS.

Alcance (se aplica en el servidor, antes de mandar los datos a la página):
- superusuario o usuario no provincial: todo el país;
- usuario provincial: solo las provincias completas de su alcance territorial;
- usuario provincial sin provincia completa (sin alcance, o solo municipio o
  localidad, que estas tablas no tienen): nada, con aviso.

Si las tablas no existen o no se pueden leer (por ejemplo en un entorno donde el
equipo de Datos no las cargó), el tablero muestra "sin datos" en lugar de fallar.
"""

import logging

from django.db import DatabaseError, transaction
from django.db.models import Max

from core.models import Provincia  # pylint: disable=import-error
from users.territorial_scope import (  # pylint: disable=import-error
    build_territorial_scope_q,
    get_effective_scopes,
    is_territorial_user,
)

from dashboard.models import ProgresarCursoEvolucion, ProgresarCursoResumen

ALCANCE_NACIONAL = "nacional"
ALCANCE_PROVINCIAL = "provincial"
SIN_ALCANCE = "sin_alcance"

logger = logging.getLogger(__name__)

# Columnas que lee el JS, en este orden.
COLUMNAS_RESUMEN = [
    "provincia_id",
    "linea",
    "estado_curso",
    "genero_codigo",
    "rango_edad",
    "tramo_inactividad",
    "tramo_aprobacion",
    "titulares",
    "suma_edad",
    "casos_edad",
]
COLUMNAS_EVOLUCION = [
    "fecha",
    "provincia_id",
    "linea",
    "genero_codigo",
    "inscriptos",
    "aprobados",
]

# Nombres de SISOC demasiado largos para las etiquetas del tablero.
NOMBRES_CORTOS = {
    "Ciudad Autónoma de Buenos Aires": "CABA",
    "Tierra del Fuego, Antártida e Islas del Atlántico Sur": "Tierra del Fuego",
}


def alcance_del_usuario(user):
    """Devuelve (tipo de alcance, filtro Q o None)."""

    if getattr(user, "is_superuser", False) or not is_territorial_user(user):
        return ALCANCE_NACIONAL, None
    filtro = build_territorial_scope_q(
        get_effective_scopes(user), provincia_lookup="provincia_id"
    )
    if filtro is None:
        return SIN_ALCANCE, None
    return ALCANCE_PROVINCIAL, filtro


def _filas(queryset, columnas, filtro):
    if filtro is not None:
        queryset = queryset.filter(filtro)
    return [list(fila) for fila in queryset.order_by("id").values_list(*columnas)]


def _hora_de_carga(valor):
    """La carga del equipo de Datos guarda `fecha_carga` en hora de Argentina, sin zona.

    Django la lee como si fuera UTC (USE_TZ), así que se muestra tal cual está en la
    base, sin convertirla: convertirla a hora local le restaría 3 horas.
    """
    if valor is None:
        return None
    return valor.replace(tzinfo=None).strftime("%Y-%m-%d %H:%M")


def _vacio(tipo, sin_datos=False):
    return {
        "alcance": tipo,
        "sin_datos": sin_datos,
        "fecha_carga": None,
        "provincias": {},
        "resumen_columnas": COLUMNAS_RESUMEN,
        "resumen": [],
        "evolucion_columnas": COLUMNAS_EVOLUCION,
        "evolucion": [],
    }


def construir_tablero(user):
    """Datos agregados del tablero, ya recortados al alcance del usuario."""

    tipo, filtro = alcance_del_usuario(user)
    if tipo == SIN_ALCANCE:
        return _vacio(tipo)

    try:
        with transaction.atomic():
            resumen = _filas(
                ProgresarCursoResumen.objects.all(), COLUMNAS_RESUMEN, filtro
            )
            evolucion = _filas(
                ProgresarCursoEvolucion.objects.all(), COLUMNAS_EVOLUCION, filtro
            )
            ultima_carga = ProgresarCursoResumen.objects.aggregate(
                ultima=Max("fecha_carga")
            )["ultima"]
    except DatabaseError:
        logger.exception("Tablero Progresar: no se pudieron leer las tablas bi_")
        return _vacio(tipo, sin_datos=True)

    for fila in evolucion:
        fila[0] = fila[0].isoformat()
    ids = sorted({fila[0] for fila in resumen if fila[0] is not None})
    provincias = {
        str(p.id): NOMBRES_CORTOS.get(p.nombre, p.nombre)
        for p in Provincia.objects.filter(id__in=ids)
    }
    return {
        "alcance": tipo,
        "sin_datos": not resumen,
        "fecha_carga": _hora_de_carga(ultima_carga),
        "provincias": provincias,
        "resumen_columnas": COLUMNAS_RESUMEN,
        "resumen": resumen,
        "evolucion_columnas": COLUMNAS_EVOLUCION,
        "evolucion": evolucion,
    }
