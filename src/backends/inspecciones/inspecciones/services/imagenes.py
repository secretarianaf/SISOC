"""Imágenes de la inspección: foto del ingreso, adicionales y firma.

Idempotentes por ``imagen_uuid``: repetir la subida devuelve la misma huella
sin reemplazar el archivo. Se pueden subir y borrar sólo antes del cierre.
"""

from django.core.files.base import ContentFile
from django.db import transaction

from inspecciones.models import EventoInspeccion, ImagenInspeccion
from inspecciones.services.archivos import sha256_de, validar_imagen
from inspecciones.services.auditoria import registrar_evento
from inspecciones.services.borradores import (
    asegurar_inspeccion,
    bloquear_propia,
    rechazar_si_finalizada,
)
from inspecciones.services.errores import Conflicto, DatosInvalidos, NoProcesable
from inspecciones.services.formato import fecha_hora_desde_texto, iso
from inspecciones.services.formularios import limites

MAX_DESCRIPCION = 1000


def _respuesta(imagen):
    return {
        "uuid": str(imagen.uuid),
        "sha256": imagen.sha256,
        "subida_at": iso(imagen.subida_at),
    }


def _capturada_at(valor):
    if valor in (None, ""):
        return None
    fecha = fecha_hora_desde_texto(valor)
    if fecha is None:
        raise DatosInvalidos(
            "La fecha de captura no es válida.",
            errores={"capturada_at": "Fecha ISO 8601."},
        )
    return fecha


def subir_imagen(  # pylint: disable=too-many-arguments
    user,
    inspeccion_uuid,
    imagen_uuid,
    *,
    archivo,
    tipo,
    descripcion="",
    capturada_at=None,
):
    if tipo not in ImagenInspeccion.Tipo.values:
        raise DatosInvalidos(
            "Tipo de imagen inválido.",
            errores={"tipo": "ingreso, adicional o firma."},
        )
    capturada = _capturada_at(capturada_at)
    asegurar_inspeccion(user, inspeccion_uuid)
    with transaction.atomic():
        inspeccion = bloquear_propia(user, inspeccion_uuid)
        rechazar_si_finalizada(inspeccion)
        existente = ImagenInspeccion.objects.filter(uuid=imagen_uuid).first()
        if existente is not None:
            if existente.inspeccion_id != inspeccion.pk:
                raise Conflicto("El identificador de imagen ya está en uso.")
            return _respuesta(existente)
        if tipo == ImagenInspeccion.Tipo.ADICIONAL:
            tope = limites()["max_imagenes_adicionales"]
            cantidad = inspeccion.imagenes.filter(tipo=tipo).count()
            if cantidad >= tope:
                raise NoProcesable(f"Hasta {tope} imágenes adicionales por inspección.")
        mime, contenido = validar_imagen(archivo)
        imagen = ImagenInspeccion(
            uuid=imagen_uuid,
            inspeccion=inspeccion,
            tipo=tipo,
            mime=mime,
            tamano=len(contenido),
            sha256=sha256_de(contenido),
            descripcion=(descripcion or "")[:MAX_DESCRIPCION],
            capturada_at=capturada,
            subida_por=user,
        )
        imagen.archivo.save("imagen", ContentFile(contenido), save=False)
        imagen.save()
        registrar_evento(
            inspeccion=inspeccion,
            accion=EventoInspeccion.Accion.IMAGEN_SUBIDA,
            actor=user,
            detalle={"imagen": str(imagen.uuid), "tipo": tipo, "sha256": imagen.sha256},
        )
    return _respuesta(imagen)


def eliminar_imagen(user, inspeccion_uuid, imagen_uuid):
    """Borra una imagen antes del cierre. Repetirlo no es error."""
    with transaction.atomic():
        inspeccion = bloquear_propia(user, inspeccion_uuid)
        rechazar_si_finalizada(inspeccion)
        imagen = inspeccion.imagenes.filter(uuid=imagen_uuid).first()
        if imagen is None:
            return
        nombre = imagen.archivo.name
        storage = imagen.archivo.storage
        detalle = {"imagen": str(imagen.uuid), "tipo": imagen.tipo}
        imagen.delete()
        registrar_evento(
            inspeccion=inspeccion,
            accion=EventoInspeccion.Accion.IMAGEN_ELIMINADA,
            actor=user,
            detalle=detalle,
        )
        transaction.on_commit(lambda: storage.delete(nombre))
