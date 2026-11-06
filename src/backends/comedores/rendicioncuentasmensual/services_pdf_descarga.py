"""Generación asíncrona del PDF consolidado de una rendición (issue #2845).

Armar el PDF puede superar el timeout de lectura del proxy del core (25 s),
así que la vista solo encola la solicitud y una tarea Celery lo genera en la
cola ``comedores``. El archivo se reutiliza mientras los documentos validados
no cambien y una purga diaria borra los que tienen más de
``PDF_DESCARGA_RETENCION``.
"""

import hashlib
import logging
import uuid
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from rendicioncuentasmensual.models import RendicionPdfDescarga
from rendicioncuentasmensual.services import RendicionCuentaMensualService

logger = logging.getLogger("django")

PDF_DESCARGA_COLA = "comedores"
PDF_DESCARGA_TAREA = "rendicioncuentasmensual.tasks.generar_pdf_descarga"
PDF_DESCARGA_RETENCION = timedelta(days=7)
# Una solicitud pendiente o en proceso más vieja que esto se considera perdida
# (worker caído, mensaje descartado) y la próxima solicitud la reemplaza.
PDF_DESCARGA_TIEMPO_MAXIMO = timedelta(minutes=15)
PDF_DESCARGA_BROKER_OPCIONES = {
    "max_retries": 0,
    "socket_connect_timeout": 3,
    "socket_timeout": 3,
}

MENSAJE_SIN_DOCUMENTOS = "La rendición no tiene documentación para descargar."
MENSAJE_NO_FINALIZADA = (
    "La descarga consolidada solo está disponible cuando la rendición está "
    "finalizada."
)
MENSAJE_ERROR_GENERICO = "No se pudo generar el PDF. Intentá nuevamente."
MENSAJE_VENCIDO = "La generación del PDF tardó demasiado. Intentá nuevamente."

ESTADOS_EN_CURSO = (
    RendicionPdfDescarga.ESTADO_PENDIENTE,
    RendicionPdfDescarga.ESTADO_PROCESANDO,
)


def calcular_huella(documentos):
    """Identifica el contenido del PDF: documentos, orden, archivo y edición."""
    partes = []
    for documento in documentos:
        modificado = getattr(documento, "ultima_modificacion", None)
        partes.append(
            f"{documento.pk}:{documento.archivo.name}:"
            f"{modificado.isoformat() if modificado else ''}"
        )
    return hashlib.sha256("|".join(partes).encode("utf-8")).hexdigest()


def _documentos_vigentes(rendicion):
    if not RendicionCuentaMensualService.rendicion_esta_completamente_validada(
        rendicion
    ):
        raise ValidationError(MENSAJE_NO_FINALIZADA)
    documentos = RendicionCuentaMensualService.obtener_documentos_para_descarga_pdf(
        rendicion
    )
    if not documentos:
        raise ValidationError(MENSAJE_SIN_DOCUMENTOS)
    return documentos


def _archivo_disponible(solicitud):
    return bool(solicitud.archivo) and solicitud.archivo.storage.exists(
        solicitud.archivo.name
    )


def _esta_vencida(solicitud, ahora=None):
    referencia = solicitud.fecha_inicio or solicitud.fecha_solicitud
    ahora = ahora or timezone.now()
    return referencia is None or ahora - referencia > PDF_DESCARGA_TIEMPO_MAXIMO


def _borrar_archivo(storage, nombre):
    if not nombre:
        return
    try:
        storage.delete(nombre)
    except OSError:
        logger.warning(
            "No se pudo borrar un PDF consolidado de rendición.",
            extra={"archivo": nombre},
            exc_info=True,
        )


def _encolar(solicitud_id, token):
    # Import diferido: el web solo necesita la app Celery al encolar.
    from config.celery import app  # pylint: disable=import-outside-toplevel

    try:
        # Conexión propia sin reintentos: con el broker inalcanzable, los
        # reintentos por defecto demoran ~20 s el POST, cerca del timeout de
        # 25 s del proxy del core. Así falla en unos 3 s.
        with app.connection_for_write(
            transport_options={
                **app.conf.broker_transport_options,
                **PDF_DESCARGA_BROKER_OPCIONES,
            }
        ) as conexion:
            app.send_task(
                PDF_DESCARGA_TAREA,
                args=[solicitud_id, token],
                queue=PDF_DESCARGA_COLA,
                retry=False,
                connection=conexion,
            )
    except Exception:  # pylint: disable=broad-exception-caught
        # Sin broker la solicitud quedaría pendiente hasta vencer: se informa ya.
        logger.exception(
            "No se pudo encolar la generación del PDF de rendición.",
            extra={"solicitud_id": solicitud_id},
        )
        RendicionPdfDescarga.objects.filter(
            pk=solicitud_id,
            token=token,
            estado=RendicionPdfDescarga.ESTADO_PENDIENTE,
        ).update(
            estado=RendicionPdfDescarga.ESTADO_ERROR,
            error=MENSAJE_ERROR_GENERICO,
            fecha_fin=timezone.now(),
        )


def solicitar_pdf_descarga(rendicion, usuario):
    """Devuelve la solicitud vigente o encola una nueva generación.

    Lanza ``ValidationError`` si la rendición no está finalizada o no tiene
    documentos validados.
    """
    huella = calcular_huella(_documentos_vigentes(rendicion))
    with transaction.atomic():
        solicitud, _ = RendicionPdfDescarga.objects.select_for_update().get_or_create(
            rendicion=rendicion
        )
        if solicitud.huella == huella:
            if (
                solicitud.estado == RendicionPdfDescarga.ESTADO_LISTO
                and _archivo_disponible(solicitud)
            ):
                return solicitud
            if solicitud.estado in ESTADOS_EN_CURSO and not _esta_vencida(solicitud):
                return solicitud

        storage = solicitud.archivo.storage
        archivo_anterior = solicitud.archivo.name
        solicitud.estado = RendicionPdfDescarga.ESTADO_PENDIENTE
        solicitud.token = uuid.uuid4().hex
        solicitud.huella = huella
        solicitud.archivo = ""
        solicitud.error = ""
        solicitud.solicitado_por = (
            usuario if getattr(usuario, "is_authenticated", False) else None
        )
        solicitud.fecha_solicitud = timezone.now()
        solicitud.fecha_inicio = None
        solicitud.fecha_fin = None
        solicitud.save()

        solicitud_id, token = solicitud.pk, solicitud.token
        transaction.on_commit(lambda: _encolar(solicitud_id, token))
        transaction.on_commit(lambda: _borrar_archivo(storage, archivo_anterior))
    # Refleja un fallo al encolar (on_commit ya corrió si no hay atomic externo).
    solicitud.refresh_from_db(fields=["estado", "error", "fecha_fin"])
    return solicitud


def obtener_estado_pdf_descarga(rendicion):
    """Estado de la última solicitud, o ``None`` si nunca se pidió el PDF.

    Una solicitud en curso que superó ``PDF_DESCARGA_TIEMPO_MAXIMO`` se informa
    como error para que el usuario pueda reintentar.
    """
    solicitud = RendicionPdfDescarga.objects.filter(rendicion=rendicion).first()
    if solicitud is None:
        return None
    if solicitud.estado in ESTADOS_EN_CURSO and _esta_vencida(solicitud):
        solicitud.estado = RendicionPdfDescarga.ESTADO_ERROR
        solicitud.error = MENSAJE_VENCIDO
    elif (
        solicitud.estado == RendicionPdfDescarga.ESTADO_LISTO
        and not _archivo_disponible(solicitud)
    ):
        solicitud.estado = RendicionPdfDescarga.ESTADO_ERROR
        solicitud.error = MENSAJE_ERROR_GENERICO
    return solicitud


def obtener_pdf_vigente(rendicion):
    """Solicitud lista cuyo PDF coincide con los documentos actuales, o ``None``."""
    huella = calcular_huella(_documentos_vigentes(rendicion))
    solicitud = RendicionPdfDescarga.objects.filter(
        rendicion=rendicion,
        estado=RendicionPdfDescarga.ESTADO_LISTO,
        huella=huella,
    ).first()
    if solicitud is None or not _archivo_disponible(solicitud):
        return None
    return solicitud


def generar_pdf_descarga(solicitud_id, token):
    """Cuerpo de la tarea Celery: genera y guarda el PDF de una solicitud."""
    de_esta_solicitud = RendicionPdfDescarga.objects.filter(pk=solicitud_id).filter(
        token=token
    )
    tomada = de_esta_solicitud.filter(
        estado=RendicionPdfDescarga.ESTADO_PENDIENTE
    ).update(estado=RendicionPdfDescarga.ESTADO_PROCESANDO, fecha_inicio=timezone.now())
    if not tomada:
        return

    solicitud = RendicionPdfDescarga.objects.select_related("rendicion").get(
        pk=solicitud_id
    )
    en_proceso = de_esta_solicitud.filter(estado=RendicionPdfDescarga.ESTADO_PROCESANDO)
    storage = solicitud.archivo.storage
    try:
        pdf = RendicionCuentaMensualService.generar_pdf_descarga_rendicion(
            solicitud.rendicion
        )
        nombre = storage.save(
            solicitud.archivo.field.generate_filename(
                solicitud, f"rendicion-{solicitud.rendicion_id}-{token}.pdf"
            ),
            ContentFile(pdf.getvalue()),
        )
    except ValidationError as exc:
        en_proceso.update(
            estado=RendicionPdfDescarga.ESTADO_ERROR,
            error=" ".join(exc.messages) or MENSAJE_ERROR_GENERICO,
            fecha_fin=timezone.now(),
        )
        return
    except Exception:  # pylint: disable=broad-exception-caught
        logger.exception(
            "No se pudo generar el PDF consolidado de la rendición.",
            extra={"rendicion_id": solicitud.rendicion_id},
        )
        en_proceso.update(
            estado=RendicionPdfDescarga.ESTADO_ERROR,
            error=MENSAJE_ERROR_GENERICO,
            fecha_fin=timezone.now(),
        )
        return

    if not en_proceso.update(
        estado=RendicionPdfDescarga.ESTADO_LISTO,
        archivo=nombre,
        fecha_fin=timezone.now(),
    ):
        # Una solicitud más nueva reemplazó a esta mientras se generaba.
        _borrar_archivo(storage, nombre)


def purgar_pdfs_descarga(ahora=None):
    """Borra los PDFs y solicitudes terminadas hace más de la retención."""
    limite = (ahora or timezone.now()) - PDF_DESCARGA_RETENCION
    viejas = RendicionPdfDescarga.objects.filter(
        estado__in=(
            RendicionPdfDescarga.ESTADO_LISTO,
            RendicionPdfDescarga.ESTADO_ERROR,
        ),
        fecha_fin__lt=limite,
    )
    borradas = 0
    for solicitud in viejas.iterator():
        # Borrado condicional: si una solicitud nueva reinició la fila entre la
        # lectura y el borrado, se conserva (y su archivo ya no es este).
        eliminadas, _ = viejas.filter(pk=solicitud.pk, token=solicitud.token).delete()
        if eliminadas:
            _borrar_archivo(solicitud.archivo.storage, solicitud.archivo.name)
            borradas += 1
    return borradas
