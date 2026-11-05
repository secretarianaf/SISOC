"""Archivos adjuntos de los formularios de relevamiento (#2781).

Reglas compartidas entre la API territorial (alta/lista/baja) y el detalle web
(lista): qué es un formulario, qué archivos se aceptan y cómo se serializan.
"""

import uuid

from django.urls import reverse

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


def adjuntos_de(comedor_id, formulario_tipo, formulario_id):
    """Adjuntos del formulario; filtra también por comedor (defensa en profundidad)."""
    return ArchivoAdjunto.objects.filter(
        comedor_id=comedor_id,
        formulario_tipo=formulario_tipo,
        formulario_id=formulario_id,
    )


def formulario_validado(formulario):
    return bool(getattr(formulario, "esta_validado", False))


def validar_archivo(archivo):  # pylint: disable=too-many-return-statements
    """Devuelve ``(extension, tipo_mime, error)``; solo el contenido manda.

    No se mira el nombre ni el ``Content-Type`` del cliente (un JPEG sin
    extensión o con ``.jfif`` es válido): un PDF empieza con ``%PDF`` y las
    imágenes las abre Pillow. GIF, SVG y todo lo demás se rechaza. La extensión y
    el MIME que se guardan salen del contenido.
    """
    if archivo.size <= 0:
        return None, None, "El archivo está vacío."
    if archivo.size > MAX_ADJUNTO_BYTES:
        return None, None, "El archivo excede el tamaño máximo de 10 MB."
    cabecera = archivo.read(5)
    archivo.seek(0)
    if cabecera.startswith(b"%PDF"):
        return "pdf", MIME_POR_EXTENSION["pdf"], None
    real = extension_de_imagen(archivo)
    if real not in ("jpg", "png", "webp"):
        return None, None, MENSAJE_FORMATO
    return real, MIME_POR_EXTENSION[real], None


def nombre_en_disco(extension):
    return f"{uuid.uuid4().hex}.{extension}"


def serializar(adjuntos, request=None):
    def _url(adjunto):
        # Descarga autenticada: los adjuntos no se sirven por /media/.
        ruta = reverse(
            "adjunto_descargar",
            kwargs={"comedor_pk": adjunto.comedor_id, "pk": adjunto.pk},
        )
        return request.build_absolute_uri(ruta) if request else ruta

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
