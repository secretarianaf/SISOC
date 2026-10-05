"""Consulta de registros PAV en el data warehouse (schema ``DW_sisoc``).

Las tablas no son de SISOC: se leen con SQL crudo sobre la conexión default,
igual que ``comedores.services.dw_transacciones_service``. En local y en tests
el schema no existe, por eso los tests mockean esta capa.
"""

import logging

from django.db import connection

logger = logging.getLogger(__name__)

# MySQL sobre Linux distingue mayúsculas en nombres de schema y tabla.
TABLA_PAV = "DW_sisoc.FCT_PAV"
TABLA_PAV_CURSOS = "DW_sisoc.DIM_PAV_Cursos"
# FCT_PAV no tiene DNI: identifica al ciudadano con ``ciudadano_key``, la clave
# de la dimensión de ciudadanos del DW (no el id de ciudadanos de SISOC). El
# documento no es único ahí, así que un DNI puede traer varios ciudadanos.
TABLA_CIUDADANOS = "DW_sisoc.DIM_Ciudadanos_Ciudadano"

# Columnas de FCT_PAV que expone la API. Explícitas para que un cambio en el DW
# no altere el contrato.
COLUMNAS_PAV = (
    "pav_cursada_key",
    "ciudadano_key",
    "pav_curso_key",
    "fecha_inscripcion",
    "fecha_finalizacion",
    "estado",
    "fecha_carga",
)

# Corta la consulta en el motor antes del timeout de 10 s del cliente web.
TIEMPO_MAXIMO_CONSULTA_MS = 5000

_SELECT_COLUMNAS_PAV = ", ".join(f"f.{columna}" for columna in COLUMNAS_PAV)

CONSULTA_PAV_POR_DOCUMENTO = f"""
    SELECT /*+ MAX_EXECUTION_TIME({TIEMPO_MAXIMO_CONSULTA_MS}) */
        {_SELECT_COLUMNAS_PAV},
        c.pav_curso_desc
    FROM {TABLA_CIUDADANOS} d
    JOIN {TABLA_PAV} f ON f.ciudadano_key = d.ciudadano_key
    LEFT JOIN {TABLA_PAV_CURSOS} c ON c.pav_curso_key = f.pav_curso_key
    WHERE d.documento = %s
    ORDER BY f.fecha_inscripcion DESC, f.pav_cursada_key DESC
"""


class PavService:
    @staticmethod
    def listar_por_documento(documento: str) -> list[dict]:
        """Devuelve los registros de FCT_PAV del documento con la descripción del curso.

        Un error de base se propaga: bajo ``/api/`` termina en un 500 con
        ``{"detail": ...}`` y no se confunde con un documento sin registros.
        """
        try:
            with connection.cursor() as cursor:
                # ``documento`` es bigint en el DW: se compara como número.
                cursor.execute(CONSULTA_PAV_POR_DOCUMENTO, [int(documento)])
                columnas = [col[0] for col in cursor.description]
                return [dict(zip(columnas, fila)) for fila in cursor.fetchall()]
        except Exception:
            logger.exception("Error consultando PAV en el DW por documento.")
            raise
