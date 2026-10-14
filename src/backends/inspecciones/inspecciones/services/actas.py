"""Actas emitidas: listado, detalle y PDF original.

El PDF lo genera la app con el número y la hora oficial del cierre y lo sube
una sola vez: si ya hay uno, la subida responde 200 sin cambiarlo.
"""

from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from inspecciones.models import Acta, EventoInspeccion
from inspecciones.services.acceso import acta_propia, acta_visible, actas_visibles
from inspecciones.services.archivos import sha256_de, validar_pdf
from inspecciones.services.auditoria import ACCIONES_VISIBLES, registrar_evento
from inspecciones.services.errores import NoEncontrado
from inspecciones.services.formato import iso, nombre_actor

ALCANCE_TODAS = "todas"


def _escuela_resumen(acta):
    escuela = acta.instantanea.get("payload", {}).get("escuela") or {}
    return {
        "nombre": escuela.get("nombre", ""),
        "cue": escuela.get("cue", ""),
        "distrito": escuela.get("distrito", ""),
        "localidad": escuela.get("localidad", ""),
    }


def _ultima_notificacion(acta):
    notificaciones = list(acta.notificaciones.all())
    return max(notificaciones, key=lambda n: n.version) if notificaciones else None


def resumen_acta(acta):
    ultima = _ultima_notificacion(acta)
    return {
        "numero": acta.numero,
        "uuid": str(acta.inspeccion.uuid),
        "estado": acta.estado,
        "escuela": _escuela_resumen(acta),
        "turno": acta.turno or None,
        "fecha_visita": acta.fecha_visita.isoformat() if acta.fecha_visita else "",
        "cerrada_at": iso(acta.cerrada_at),
        "resultado": acta.resultado or None,
        "firma_tipo": acta.firma_tipo or None,
        "pdf_estado": "disponible" if acta.pdf else "pendiente",
        "notificacion": {
            "estado": acta.notificacion_estado,
            "cargada_at": iso(ultima.cargada_at) if ultima else None,
            "condicion_firma": ultima.condicion_firma if ultima else None,
        },
        "inspector": {"id": acta.inspector_id, "nombre": nombre_actor(acta.inspector)},
        "es_prueba": acta.es_prueba,
    }


def listar_actas(user, *, alcance=""):
    """Actas propias, de la más reciente a la más vieja.

    Coordinación puede pedir ``alcance=todas``. Sin el parámetro, también ve
    sólo las propias: "Mis actas" de la app no se mezcla con las de otros.
    """
    if alcance == ALCANCE_TODAS:
        queryset = actas_visibles(user)
    else:
        queryset = Acta.objects.select_related("inspeccion", "inspector").filter(
            inspector=user
        )
    queryset = queryset.prefetch_related("notificaciones").order_by("-cerrada_at")
    return [resumen_acta(acta) for acta in queryset]


def serializar_notificacion(notificacion):
    archivos = list(notificacion.archivos.all())
    return {
        "uuid": str(notificacion.uuid),
        "version": notificacion.version,
        "cargada_at": iso(notificacion.cargada_at),
        "cargada_por": nombre_actor(notificacion.cargada_por),
        "notificada_at": iso(notificacion.notificada_at),
        "receptor_nombre": notificacion.receptor_nombre,
        "receptor_cargo": notificacion.receptor_cargo,
        "condicion_firma": notificacion.condicion_firma,
        "motivo": notificacion.motivo,
        "observaciones": notificacion.observaciones,
        "archivos": len(archivos),
        "archivos_ids": [str(archivo.uuid) for archivo in archivos],
        "reemplaza_uuid": (
            str(notificacion.reemplaza.uuid) if notificacion.reemplaza_id else None
        ),
        "motivo_correccion": notificacion.motivo_correccion,
    }


def _eventos(acta):
    eventos = acta.inspeccion.eventos.filter(accion__in=ACCIONES_VISIBLES).order_by(
        "at", "id"
    )
    return [
        {
            "actor": evento.actor_nombre,
            "accion": evento.get_accion_display(),
            "codigo": evento.accion,
            "at": iso(evento.at),
        }
        for evento in eventos
    ]


def detalle_acta(user, numero):
    """El acta completa: resumen + instantánea + historial + notificaciones.

    Los datos de la inspección van en la raíz con el mismo formato del cuerpo
    del borrador, para que la app los lea con el mismo conversor.
    """
    acta = acta_visible(user, numero)
    instantanea = acta.instantanea
    payload = instantanea.get("payload", {})
    notificaciones = (
        acta.notificaciones.select_related("cargada_por", "reemplaza")
        .prefetch_related("archivos")
        .order_by("version")
    )
    return {
        **resumen_acta(acta),
        **payload,
        "uuid": str(acta.inspeccion.uuid),
        "imagenes": instantanea.get("imagenes", []),
        "formulario": instantanea.get("formulario", {}),
        "instantanea_sha256": acta.instantanea_sha256,
        "eventos": _eventos(acta),
        "notificaciones": [serializar_notificacion(n) for n in notificaciones],
    }


def subir_pdf(user, numero, archivo):
    with transaction.atomic():
        acta = acta_propia(user, numero, bloquear=True)
        if not acta.pdf:
            contenido = validar_pdf(archivo)
            acta.pdf.save("acta.pdf", ContentFile(contenido), save=False)
            acta.pdf_sha256 = sha256_de(contenido)
            acta.pdf_subido_at = timezone.now()
            acta.pdf_subido_por = user
            acta.save(
                update_fields=["pdf", "pdf_sha256", "pdf_subido_at", "pdf_subido_por"]
            )
            registrar_evento(
                inspeccion=acta.inspeccion,
                acta=acta,
                accion=EventoInspeccion.Accion.PDF_SUBIDO,
                actor=user,
                detalle={"sha256": acta.pdf_sha256},
            )
    return {
        "numero": acta.numero,
        "pdf_estado": "disponible",
        "sha256": acta.pdf_sha256,
        "subido_at": iso(acta.pdf_subido_at),
    }


def obtener_pdf(user, numero):
    acta = acta_visible(user, numero)
    if not acta.pdf:
        raise NoEncontrado("El PDF todavía no está disponible.")
    return acta
