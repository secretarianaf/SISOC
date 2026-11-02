"""Archivos adjuntos de los formularios de relevamiento (#2781).

Reglas compartidas entre la API territorial (alta/lista/baja) y el detalle web
(lista): qué es un formulario, qué archivos se aceptan y cómo se serializan.
"""

import uuid

from comedores.api_views_territorial_validaciones import extension_de_imagen
from relevamientos.models import (
    ActaComplementaria,
    ArchivoAdjunto,
    PrimerSeguimiento,
    Relevamiento,
    SeguimientoPnud,
)

MAX_ADJUNTOS_POR_FORMULARIO = 10
MAX_ADJUNTO_BYTES = 10 * 1024 * 1024  # 10 MB
EXTENSIONES_ADJUNTO = ("jpg", "jpeg", "png", "webp", "pdf")
MIME_POR_EXTENSION = {
    "jpg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
    "pdf": "application/pdf",
}
MENSAJE_FORMATO = "El archivo debe ser una imagen JPG, PNG o WEBP, o un PDF."

# tipo -> (modelo, filtro del comedor)
_FORMULARIOS = {
    ArchivoAdjunto.TIPO_RELEVAMIENTO: (Relevamiento, "comedor"),
    ArchivoAdjunto.TIPO_SEGUIMIENTO: (PrimerSeguimiento, "id_relevamiento__comedor"),
    ArchivoAdjunto.TIPO_SEGUIMIENTO_PNUD: (SeguimientoPnud, "comedor"),
    ArchivoAdjunto.TIPO_ACTA: (ActaComplementaria, "comedor"),
}


def formulario_de_comedor(comedor, formulario_tipo, formulario_id):
    """Instancia del formulario si existe y es de ese comedor; si no, ``None``."""
    modelo, campo_comedor = _FORMULARIOS[formulario_tipo]
    return modelo.objects.filter(
        **{"pk": formulario_id, campo_comedor: comedor}
    ).first()


def adjuntos_de(formulario_tipo, formulario_id):
    return ArchivoAdjunto.objects.filter(
        formulario_tipo=formulario_tipo, formulario_id=formulario_id
    )


def validar_archivo(archivo):  # pylint: disable=too-many-return-statements
    """Devuelve ``(extension, tipo_mime, error)``; el contenido manda.

    La extensión declarada filtra, pero se verifica el contenido real: un PDF
    empieza con ``%PDF`` y las imágenes las abre Pillow (un SVG o un texto
    renombrado a ``.png`` no pasan). La extensión y el MIME que se guardan salen
    del contenido, no del nombre ni del ``Content-Type`` del cliente.
    """
    nombre = (getattr(archivo, "name", "") or "").lower()
    declarada = nombre.rsplit(".", 1)[-1] if "." in nombre else ""
    if declarada not in EXTENSIONES_ADJUNTO:
        return None, None, MENSAJE_FORMATO
    if archivo.size <= 0:
        return None, None, "El archivo está vacío."
    if archivo.size > MAX_ADJUNTO_BYTES:
        return None, None, "El archivo excede el tamaño máximo de 10 MB."
    if declarada == "pdf":
        cabecera = archivo.read(5)
        archivo.seek(0)
        if not cabecera.startswith(b"%PDF"):
            return None, None, MENSAJE_FORMATO
        return "pdf", MIME_POR_EXTENSION["pdf"], None
    real = extension_de_imagen(archivo)
    if real not in ("jpg", "png", "webp"):
        return None, None, MENSAJE_FORMATO
    return real, MIME_POR_EXTENSION[real], None


def nombre_en_disco(extension):
    return f"{uuid.uuid4().hex}.{extension}"


def serializar(adjuntos, request=None):
    def _url(adjunto):
        url = adjunto.archivo.url if adjunto.archivo else None
        return request.build_absolute_uri(url) if (url and request) else url

    return [
        {
            "id": adjunto.id,
            "nombre": adjunto.nombre_original,
            "tipo_mime": adjunto.tipo_mime,
            "tamano": adjunto.tamano,
            "url": _url(adjunto),
            "formulario_tipo": adjunto.formulario_tipo,
            "formulario_id": adjunto.formulario_id,
            "client_uuid": adjunto.client_uuid,
            "fecha_subida": adjunto.fecha_subida,
        }
        for adjunto in adjuntos
    ]
