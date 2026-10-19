"""Descarga de actas completas desde Tablero → Últimas actas (#2718).

Reusa ``tablero.actas_validas`` (la misma fuente que el CSV y los indicadores)
y entrega el PDF original de cada acta: el que genera la app con todos los
datos del reporte y las imágenes, y sube al cerrar (``Acta.pdf``). Una acta se
baja como PDF; varias, en un ZIP armado en un archivo temporal (no en memoria).
Las actas cuyo PDF aún no llegó se listan en ``ACTAS_SIN_PDF.txt`` dentro del
ZIP, para que nadie crea que la descarga está completa.
"""

import tempfile
import zipfile
from dataclasses import dataclass

from inspecciones.services.tablero import actas_validas

MAX_ACTAS = 100
NOMBRE_FALTANTES = "ACTAS_SIN_PDF.txt"
MENSAJE_SIN_ACTAS = "No hay actas para descargar con los filtros aplicados."
MENSAJE_SIN_PDF = (
    "Las actas de los filtros aplicados todavía no tienen su PDF disponible."
)


def mensaje_tope(maximo=None):
    maximo = MAX_ACTAS if maximo is None else maximo
    return (
        f"Hay demasiadas actas para descargar juntas (máximo {maximo}). "
        "Acotá los filtros e intentá de nuevo."
    )


class SinDescarga(Exception):
    """No hay nada que descargar; ``str(exc)`` es el mensaje para el usuario."""


@dataclass
class Descarga:
    archivo: object
    content_type: str
    nombre: str


def nombre_archivo_zip(filtros):
    return f"inspecciones-actas-{filtros.fecha.isoformat()}.zip"


def _texto_faltantes(numeros):
    lineas = ["Actas sin PDF disponible todavía (no incluidas en esta descarga):", ""]
    return "\n".join(lineas + list(numeros)) + "\n"


def _armar_zip(con_pdf, faltantes):
    temporal = tempfile.TemporaryFile()  # pylint: disable=consider-using-with
    with zipfile.ZipFile(temporal, "w", zipfile.ZIP_STORED) as zf:
        for acta in con_pdf:
            with (
                acta.pdf.open("rb") as origen,
                zf.open(f"{acta.numero}.pdf", "w", force_zip64=True) as destino,
            ):
                for bloque in iter(lambda: origen.read(1024 * 1024), b""):
                    destino.write(bloque)
        if faltantes:
            zf.writestr(NOMBRE_FALTANTES, _texto_faltantes(faltantes))
    temporal.seek(0)
    return temporal


def armar_descarga(filtros):
    actas = list(
        actas_validas(filtros)
        .only("id", "numero", "pdf")
        .order_by("cerrada_at", "id")[: MAX_ACTAS + 1]
    )
    if not actas:
        raise SinDescarga(MENSAJE_SIN_ACTAS)
    if len(actas) > MAX_ACTAS:
        raise SinDescarga(mensaje_tope())
    con_pdf = [acta for acta in actas if acta.pdf]
    faltantes = [acta.numero for acta in actas if not acta.pdf]
    if not con_pdf:
        raise SinDescarga(MENSAJE_SIN_PDF)
    if len(con_pdf) == 1 and not faltantes:
        acta = con_pdf[0]
        return Descarga(acta.pdf.open("rb"), "application/pdf", f"{acta.numero}.pdf")
    return Descarga(
        _armar_zip(con_pdf, faltantes),
        "application/zip",
        nombre_archivo_zip(filtros),
    )
