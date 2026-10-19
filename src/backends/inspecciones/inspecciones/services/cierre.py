"""Cierre de la inspección: una sola transacción (especificación §4 paso 7).

Dentro de la transacción: valida, guarda la instantánea inmutable, asigna el
número ``ACTA-AAAA-NNNNNN`` y registra la hora oficial del servidor.

Numeración: una fila de ``SecuenciaActa`` por año, bloqueada con
``select_for_update``. El incremento y el acta se confirman juntos: si algo
falla, se revierten juntos, así que no quedan huecos ni números repetidos. Los
cierres se serializan sólo en ese tramo corto (validar va antes del bloqueo).

Idempotencia: la inspección se bloquea primero. Un segundo cierre del mismo
uuid (doble toque, reintento, pedido simultáneo) espera al primero y devuelve
la misma acta con el mismo número y la misma hora.

Compatible con MySQL: Django usa READ COMMITTED y las lecturas con bloqueo ven
siempre la última versión confirmada.
"""

import hashlib
import json

from django.db import IntegrityError, transaction
from django.utils import timezone

from inspecciones.models import (
    Acta,
    EventoInspeccion,
    ImagenInspeccion,
    Inspeccion,
    SecuenciaActa,
)
from inspecciones.services.auditoria import registrar_evento
from inspecciones.services.borradores import (
    aplicar_payload,
    asegurar_inspeccion,
    bloquear_propia,
    revision_del_payload,
)
from inspecciones.services.errores import Conflicto, DatosInvalidos
from inspecciones.services.escuelas import serializar_escuela
from inspecciones.services.formato import (
    fecha_desde_texto,
    fecha_hora_desde_texto,
    iso,
    nombre_actor,
)
from inspecciones.services.formularios import es_version_valida, obtener_formulario
from inspecciones.services.validacion import validar_inspeccion

FORMATO_NUMERO = "ACTA-{anio}-{secuencia:06d}"


def formatear_numero(anio, secuencia):
    return FORMATO_NUMERO.format(anio=anio, secuencia=secuencia)


def _resultado_cierre(acta):
    return {
        "numero": acta.numero,
        "cerrada_at": iso(acta.cerrada_at),
        "pdf_estado": "disponible" if acta.pdf else "pendiente",
    }


def asegurar_secuencia(anio):
    """Crea la fila del año fuera de la transacción del cierre (si falta)."""
    if SecuenciaActa.objects.filter(anio=anio).exists():
        return
    try:
        with transaction.atomic():
            SecuenciaActa.objects.create(anio=anio, ultimo=0)
    except IntegrityError:
        pass


def siguiente_numero(anio):
    """Toma el próximo número del año. Debe llamarse dentro de una transacción."""
    secuencia = SecuenciaActa.objects.select_for_update().filter(anio=anio).first()
    if secuencia is None:
        # Sólo pasa si el año cambió entre el aseguramiento y el bloqueo.
        SecuenciaActa.objects.get_or_create(anio=anio)
        secuencia = SecuenciaActa.objects.select_for_update().get(anio=anio)
    secuencia.ultimo += 1
    secuencia.save(update_fields=["ultimo"])
    return secuencia.ultimo


def _uuids_referidos(payload):
    """Imágenes que el estado final dice tener (todas deben estar subidas)."""
    respuestas = payload.get("respuestas") if isinstance(payload, dict) else None
    respuestas = respuestas if isinstance(respuestas, dict) else {}
    referidas = {}
    for imagen in payload.get("imagenes") or []:
        if isinstance(imagen, dict) and imagen.get("uuid"):
            referidas[str(imagen["uuid"])] = imagen.get("tipo")
    f04 = respuestas.get("f04") if isinstance(respuestas.get("f04"), dict) else {}
    if f04.get("imagen_uuid"):
        referidas.setdefault(str(f04["imagen_uuid"]), ImagenInspeccion.Tipo.INGRESO)
    f15 = payload.get("f15") or respuestas.get("f15") or []
    for imagen_uuid in f15 if isinstance(f15, list) else []:
        referidas.setdefault(str(imagen_uuid), ImagenInspeccion.Tipo.ADICIONAL)
    firma = payload.get("firma") if isinstance(payload.get("firma"), dict) else {}
    if firma.get("tipo") == "firma" and firma.get("imagen_uuid"):
        referidas.setdefault(str(firma["imagen_uuid"]), ImagenInspeccion.Tipo.FIRMA)
    return referidas


def _imagenes_del_cierre(inspeccion, payload):
    referidas = _uuids_referidos(payload)
    subidas = {
        str(imagen.uuid): imagen
        for imagen in inspeccion.imagenes.filter(uuid__in=list(referidas))
    }
    faltantes = [u for u in referidas if u not in subidas]
    if faltantes:
        raise DatosInvalidos(
            f"Faltan subir {len(faltantes)} imagen(es).",
            errores={"imagenes": "Hay imágenes sin subir."},
            faltantes=faltantes,
        )
    errores = {}
    for imagen_uuid, tipo in referidas.items():
        if tipo and subidas[imagen_uuid].tipo != tipo:
            errores[f"imagenes.{imagen_uuid}"] = "El tipo de la imagen no coincide."
    if errores:
        raise DatosInvalidos("Las imágenes no coinciden con el acta.", errores=errores)
    return [subidas[u] for u in referidas]


def _turnos_visitados_hoy(inspeccion, payload):
    """Turnos con un acta válida de la misma escuela y jornada (exige motivo)."""
    if inspeccion.escuela_id is None:
        return set()
    fecha = fecha_desde_texto(payload.get("fecha_visita"))
    if fecha is None:
        return set()
    return set(
        Acta.objects.filter(
            escuela_id=inspeccion.escuela_id,
            fecha_visita=fecha,
            estado=Acta.Estado.FINALIZADA,
        )
        .exclude(inspeccion=inspeccion)
        .values_list("turno", flat=True)
    )


def _validar(inspeccion, payload):
    errores = {}
    if not es_version_valida(payload.get("formulario_version")):
        errores["formulario_version"] = "Versión de formulario desconocida."
    if fecha_desde_texto(payload.get("fecha_visita")) is None:
        errores["fecha_visita"] = "La fecha de visita no es válida."
    errores.update(
        validar_inspeccion(
            payload, turnos_visitados_hoy=_turnos_visitados_hoy(inspeccion, payload)
        )
    )
    if errores:
        raise DatosInvalidos(
            "El acta tiene datos incompletos o inválidos.", errores=errores
        )


def _serializar_imagen(imagen):
    return {
        "uuid": str(imagen.uuid),
        "tipo": imagen.tipo,
        "descripcion": imagen.descripcion,
        "mime": imagen.mime,
        "tamano": imagen.tamano,
        "sha256": imagen.sha256,
        "capturada_at": iso(imagen.capturada_at),
        "subida_at": iso(imagen.subida_at),
    }


def _instantanea(  # pylint: disable=too-many-arguments
    *, inspeccion, payload, imagenes, numero, cerrada_at, user
):
    contenido = {
        "numero": numero,
        "uuid": str(inspeccion.uuid),
        "cerrada_at": iso(cerrada_at),
        "inspector": {
            "id": user.pk,
            "username": user.get_username(),
            "nombre": nombre_actor(user),
        },
        "escuela_catalogo": (
            serializar_escuela(inspeccion.escuela) if inspeccion.escuela else None
        ),
        "escuela_carga_manual": inspeccion.escuela_carga_manual,
        "formulario": obtener_formulario(payload["formulario_version"]),
        "payload": {k: v for k, v in payload.items() if k != "uuid"},
        "imagenes": [_serializar_imagen(imagen) for imagen in imagenes],
    }
    canonico = json.dumps(
        contenido, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )
    return contenido, hashlib.sha256(canonico.encode("utf-8")).hexdigest()


def _registrar_firma(inspeccion, acta, payload, user):
    firma = payload.get("firma") if isinstance(payload.get("firma"), dict) else {}
    if firma.get("tipo") == "firma":
        registrar_evento(
            inspeccion=inspeccion,
            acta=acta,
            accion=EventoInspeccion.Accion.FIRMADA,
            actor=None,
            actor_nombre=str(firma.get("nombre") or "")[:200],
            at=fecha_hora_desde_texto(firma.get("firmada_at")) or acta.cerrada_at,
            detalle={
                "cargo": firma.get("cargo"),
                "hash_contenido": firma.get("hash_contenido"),
            },
        )
    elif firma.get("tipo") == "excepcion":
        registrar_evento(
            inspeccion=inspeccion,
            acta=acta,
            accion=EventoInspeccion.Accion.EXCEPCION_FIRMA,
            actor=user,
            at=fecha_hora_desde_texto(firma.get("registrada_at")) or acta.cerrada_at,
            detalle={
                "motivo_tipo": firma.get("motivo_tipo"),
                "hash_contenido": firma.get("hash_contenido"),
            },
        )


def finalizar_inspeccion(user, inspeccion_uuid, payload):
    """Cierra la inspección y devuelve ``{numero, cerrada_at, pdf_estado}``."""
    revision = revision_del_payload(payload)
    asegurar_inspeccion(user, inspeccion_uuid)
    asegurar_secuencia(timezone.localdate().year)
    with transaction.atomic():
        inspeccion = bloquear_propia(user, inspeccion_uuid)
        if inspeccion.estado == Inspeccion.Estado.FINALIZADA:
            acta = Acta.objects.select_for_update().get(inspeccion=inspeccion)
            return _resultado_cierre(acta)
        if revision < inspeccion.revision:
            raise Conflicto(
                "El servidor tiene una versión más nueva de este borrador.",
                revision=inspeccion.revision,
            )
        sin_borrador_previo = inspeccion.revision == 0
        aplicar_payload(inspeccion, payload, revision)
        _validar(inspeccion, payload)
        imagenes = _imagenes_del_cierre(inspeccion, payload)
        if sin_borrador_previo:
            # Cerrada sin haber subido nunca el borrador: igual queda su alta.
            registrar_evento(
                inspeccion=inspeccion,
                accion=EventoInspeccion.Accion.CREADA,
                actor=user,
                at=inspeccion.creada_cliente_at,
                detalle={"revision": revision},
            )

        # Tramo serializado: número y hora oficial.
        cerrada_at = timezone.now()
        anio = timezone.localtime(cerrada_at).year
        secuencia = siguiente_numero(anio)
        numero = formatear_numero(anio, secuencia)
        instantanea, huella = _instantanea(
            inspeccion=inspeccion,
            payload=payload,
            imagenes=imagenes,
            numero=numero,
            cerrada_at=cerrada_at,
            user=user,
        )
        inspeccion.estado = Inspeccion.Estado.FINALIZADA
        inspeccion.deleted_at = None
        inspeccion.deleted_by = None
        inspeccion.save()
        firma = payload.get("firma") if isinstance(payload.get("firma"), dict) else {}
        acta = Acta.objects.create(
            inspeccion=inspeccion,
            inspector=user,
            escuela=inspeccion.escuela,
            numero=numero,
            anio=anio,
            secuencia=secuencia,
            cerrada_at=cerrada_at,
            fecha_visita=inspeccion.fecha_visita,
            turno=inspeccion.turno,
            resultado=inspeccion.resultado,
            firma_tipo=str(firma.get("tipo") or "")[:20],
            formulario_version=inspeccion.formulario_version,
            instantanea=instantanea,
            instantanea_sha256=huella,
        )
        _registrar_firma(inspeccion, acta, payload, user)
        registrar_evento(
            inspeccion=inspeccion,
            acta=acta,
            accion=EventoInspeccion.Accion.FINALIZADA,
            actor=user,
            at=cerrada_at,
            detalle={"numero": numero, "revision": revision},
        )
    return _resultado_cierre(acta)
