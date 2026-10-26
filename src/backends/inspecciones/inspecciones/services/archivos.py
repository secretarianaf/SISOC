"""Validación y huella de los archivos subidos (sin confiar en el cliente).

El tipo se decide por la firma binaria del contenido, no por la extensión ni
por el ``Content-Type`` que manda el teléfono.
"""

import hashlib

from inspecciones.services.errores import NoProcesable
from inspecciones.services.formularios import limites

FIRMA_JPEG = b"\xff\xd8\xff"
FIRMA_PNG = b"\x89PNG\r\n\x1a\n"
FIRMA_PDF = b"%PDF-"
MAX_BYTES_PDF = 30 * 1024 * 1024


def _leer(archivo):
    archivo.seek(0)
    contenido = archivo.read()
    archivo.seek(0)
    return contenido


def sha256_de(contenido):
    return hashlib.sha256(contenido).hexdigest()


def validar_imagen(archivo):
    """``(mime, contenido)`` de una imagen JPEG/PNG de hasta 10 MB."""
    if archivo is None:
        raise NoProcesable("Falta el archivo.")
    tope = limites()["max_bytes_imagen"]
    if archivo.size > tope:
        raise NoProcesable("La imagen supera los 10 MB.")
    contenido = _leer(archivo)
    if contenido.startswith(FIRMA_JPEG):
        return "image/jpeg", contenido
    if contenido.startswith(FIRMA_PNG):
        return "image/png", contenido
    raise NoProcesable("Solo se admiten imágenes JPEG o PNG.")


def validar_pdf(archivo):
    if archivo is None:
        raise NoProcesable("Falta el archivo.")
    if archivo.size > MAX_BYTES_PDF:
        raise NoProcesable("El PDF supera los 30 MB.")
    contenido = _leer(archivo)
    if not contenido.startswith(FIRMA_PDF):
        raise NoProcesable("El archivo no es un PDF.")
    return contenido
