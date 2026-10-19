"""Archivos privados de Inspecciones escolares.

Fotos, firmas, PDFs de actas y notificaciones contienen datos de personas y
escuelas: se sirven sólo por la API con los permisos del acta, nunca por una
URL pública. Viven bajo ``MEDIA_ROOT/inspecciones/`` (el volumen ``media`` ya
está montado en todos los servicios) y el Nginx del host debe bloquear
``/media/inspecciones/`` igual que ``/media/pas/ddjj/``; ver
``docs/registro/cambios/2026-T4/2026-10-14-inspecciones-escolares-backend.md``.
"""

from django.core.files.storage import FileSystemStorage

PREFIJO = "inspecciones"


class AlmacenamientoPrivado(FileSystemStorage):
    """``FileSystemStorage`` sin URL: los archivos sólo se leen desde la API."""

    def url(self, name):
        raise NotImplementedError(
            "Los archivos de inspecciones son privados: se descargan por la API."
        )


def almacenamiento_privado():
    """Callable para ``FileField.storage`` (``MEDIA_ROOT`` se lee en uso)."""
    return AlmacenamientoPrivado()


def _extension(mime):
    return {"image/png": "png", "image/jpeg": "jpg", "application/pdf": "pdf"}.get(
        mime, "bin"
    )


def ruta_imagen(instance, _filename):
    return (
        f"{PREFIJO}/{instance.inspeccion.uuid}/imagenes/"
        f"{instance.uuid}.{_extension(instance.mime)}"
    )


def ruta_pdf(instance, _filename):
    return f"{PREFIJO}/{instance.inspeccion.uuid}/acta/{instance.numero}.pdf"


def ruta_archivo_notificacion(instance, _filename):
    notificacion = instance.notificacion
    return (
        f"{PREFIJO}/{notificacion.acta.inspeccion.uuid}/notificaciones/"
        f"{notificacion.uuid}/{instance.uuid}.{_extension(instance.mime)}"
    )
