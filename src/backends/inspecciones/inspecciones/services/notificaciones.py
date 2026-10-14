"""Notificación en papel, posterior al cierre (especificación §16).

La carga es un anexo: no reabre el acta, no cambia número, respuestas, firma
ni PDF original. Es idempotente por ``uuid``. Una corrección es una carga
nueva que ``reemplaza`` a otra con motivo; la anterior se conserva.
"""

import uuid as uuid_lib

from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Max

from inspecciones.models import (
    Acta,
    ArchivoNotificacion,
    EventoInspeccion,
    NotificacionPapel,
)
from inspecciones.services.acceso import acta_propia, ve_todo
from inspecciones.services.archivos import sha256_de, validar_imagen
from inspecciones.services.auditoria import registrar_evento
from inspecciones.services.errores import Conflicto, DatosInvalidos, NoEncontrado
from inspecciones.services.formato import fecha_hora_desde_texto, iso
from inspecciones.services.formularios import limites

MAX_TEXTO = 200


def _texto(valor):
    return valor.strip() if isinstance(valor, str) else ""


def _uuid(valor, campo):
    try:
        return uuid_lib.UUID(str(valor))
    except (TypeError, ValueError, AttributeError) as exc:
        raise DatosInvalidos(
            f"El campo {campo} no es un UUID válido.", errores={campo: "UUID."}
        ) from exc


def _respuesta(notificacion):
    return {
        "uuid": str(notificacion.uuid),
        "cargada_at": iso(notificacion.cargada_at),
        "estado": "cargada",
    }


def _validar_datos(acta, datos, archivos):
    errores = {}
    tope = limites()["max_fotos_notificacion"]
    if not archivos or len(archivos) > tope:
        errores["archivos"] = f"Adjuntá entre 1 y {tope} fotos."
    if _texto(datos.get("numero_confirmado")) != acta.numero:
        errores["numero_confirmado"] = "El número confirmado no coincide con el acta."
    notificada_at = fecha_hora_desde_texto(datos.get("notificada_at"))
    if notificada_at is None:
        errores["notificada_at"] = "Indicá la fecha y hora de la notificación."
    for campo in ("receptor_nombre", "receptor_cargo"):
        if not _texto(datos.get(campo)):
            errores[campo] = "Este campo es obligatorio."
    condicion = _texto(datos.get("condicion_firma"))
    if condicion not in NotificacionPapel.CondicionFirma.values:
        errores["condicion_firma"] = "firmada, negativa o sin_receptor."
    elif condicion != NotificacionPapel.CondicionFirma.FIRMADA and not _texto(
        datos.get("motivo")
    ):
        errores["motivo"] = "Indicá el motivo."
    reemplaza = None
    if _texto(datos.get("reemplaza_uuid")):
        reemplaza_uuid = _uuid(datos.get("reemplaza_uuid"), "reemplaza_uuid")
        reemplaza = acta.notificaciones.filter(uuid=reemplaza_uuid).first()
        if reemplaza is None:
            errores["reemplaza_uuid"] = "La carga a corregir no es de esta acta."
        if not _texto(datos.get("motivo_correccion")):
            errores["motivo_correccion"] = "Indicá el motivo de la corrección."
    if errores:
        raise DatosInvalidos(
            next(iter(errores.values())) if len(errores) == 1 else "Datos inválidos.",
            errores=errores,
        )
    return notificada_at, condicion, reemplaza


def cargar_notificacion(
    user, numero, datos, archivos
):  # pylint: disable=too-many-locals
    carga_uuid = _uuid(datos.get("uuid"), "uuid")
    with transaction.atomic():
        # Bloquear el acta serializa las cargas: la versión no se repite.
        acta = acta_propia(user, numero, bloquear=True)
        existente = NotificacionPapel.objects.filter(uuid=carga_uuid).first()
        if existente is not None:
            if existente.acta_id != acta.pk:
                raise Conflicto("El identificador de la carga ya está en uso.")
            return _respuesta(existente)
        if acta.estado == Acta.Estado.ANULADA:
            raise Conflicto("El acta está anulada: no admite nuevas cargas.")
        notificada_at, condicion, reemplaza = _validar_datos(acta, datos, archivos)
        imagenes = [validar_imagen(archivo) for archivo in archivos]
        version = (
            acta.notificaciones.aggregate(maximo=Max("version"))["maximo"] or 0
        ) + 1
        notificacion = NotificacionPapel.objects.create(
            uuid=carga_uuid,
            acta=acta,
            version=version,
            cargada_por=user,
            notificada_at=notificada_at,
            receptor_nombre=_texto(datos.get("receptor_nombre"))[:MAX_TEXTO],
            receptor_cargo=_texto(datos.get("receptor_cargo"))[:MAX_TEXTO],
            condicion_firma=condicion,
            motivo=_texto(datos.get("motivo")),
            observaciones=_texto(datos.get("observaciones")),
            numero_confirmado=_texto(datos.get("numero_confirmado")),
            reemplaza=reemplaza,
            motivo_correccion=_texto(datos.get("motivo_correccion")),
        )
        for orden, (mime, contenido) in enumerate(imagenes, start=1):
            archivo = ArchivoNotificacion(
                uuid=uuid_lib.uuid4(),
                notificacion=notificacion,
                orden=orden,
                mime=mime,
                tamano=len(contenido),
                sha256=sha256_de(contenido),
            )
            archivo.archivo.save("notificacion", ContentFile(contenido), save=False)
            archivo.save()
        acta.notificacion_estado = Acta.EstadoNotificacion.CARGADA
        acta.save(update_fields=["notificacion_estado"])
        registrar_evento(
            inspeccion=acta.inspeccion,
            acta=acta,
            accion=(
                EventoInspeccion.Accion.NOTIFICACION_CORREGIDA
                if reemplaza
                else EventoInspeccion.Accion.NOTIFICACION_CARGADA
            ),
            actor=user,
            at=notificacion.cargada_at,
            detalle={"uuid": str(notificacion.uuid), "version": version},
        )
    return _respuesta(notificacion)


def archivo_notificacion_visible(user, archivo_uuid):
    queryset = ArchivoNotificacion.objects.select_related("notificacion__acta")
    if not ve_todo(user):
        queryset = queryset.filter(notificacion__acta__inspector=user)
    archivo = queryset.filter(uuid=archivo_uuid).first()
    if archivo is None:
        raise NoEncontrado()
    return archivo
