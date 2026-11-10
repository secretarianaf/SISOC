"""Configuración y respuestas móviles sobre las mismas encuestas y rondas."""

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.http import QueryDict
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import (
    CumplimientoRonda,
    EstadoEncuesta,
    EstadoRonda,
    RondaEncuesta,
    TipoPregunta,
)
from .services import registrar_respuesta, usuario_esta_segmentado


def rondas_pwa():
    return RondaEncuesta.objects.filter(
        encuesta__disponible_pwa=True,
        encuesta__estado=EstadoEncuesta.PUBLICADA,
        estado=EstadoRonda.ABIERTA,
        fecha_cierre_programada__gt=timezone.now(),
    ).select_related("encuesta", "encuesta__segmentacion")


def _configuracion(ronda, respondida):
    preguntas = list(
        ronda.encuesta.preguntas.order_by("orden", "pk").prefetch_related("opciones")
    )
    return {
        "id": ronda.pk,
        "encuesta_id": ronda.encuesta_id,
        "version": ronda.encuesta.version,
        "titulo": ronda.encuesta.titulo,
        "descripcion": ronda.encuesta.descripcion,
        "es_anonima": ronda.encuesta.es_anonima,
        "modalidad": ronda.encuesta.modalidad,
        "fecha_cierre": ronda.fecha_cierre_programada,
        "respondida": respondida,
        "preguntas": [
            {
                "id": p.pk,
                "orden": p.orden,
                "texto": p.texto,
                "tipo": p.tipo,
                "obligatoria": p.obligatoria,
                "bloque": p.bloque,
                "max_caracteres": p.max_caracteres,
                "opciones": [
                    {"valor": o.valor, "texto": o.texto} for o in p.opciones.all()
                ],
                "condicion": (
                    {
                        "pregunta_id": p.pregunta_condicion_id,
                        "operador": p.operador_condicion,
                        "valor": p.valor_condicion,
                    }
                    if p.pregunta_condicion_id
                    else None
                ),
            }
            for p in preguntas
        ],
    }


def listar_encuestas_pwa(usuario):
    respondidas = set(
        CumplimientoRonda.objects.filter(usuario=usuario).values_list(
            "ronda_id", flat=True
        )
    )
    return [
        _configuracion(ronda, ronda.pk in respondidas)
        for ronda in rondas_pwa().order_by("fecha_cierre_programada", "pk")
        if usuario_esta_segmentado(ronda.encuesta, usuario)
    ]


@transaction.atomic
def responder_encuesta_pwa(ronda_id, usuario, respuestas):
    # La ronda bloqueada serializa reintentos: también preserva anonimato,
    # porque el cumplimiento no referencia el contenido de la respuesta.
    ronda = get_object_or_404(rondas_pwa().select_for_update(), pk=ronda_id)
    if not usuario_esta_segmentado(ronda.encuesta, usuario):
        raise PermissionDenied("No sos destinatario de esta encuesta.")
    if CumplimientoRonda.objects.filter(ronda=ronda, usuario=usuario).exists():
        return {"respondida": True, "ya_registrada": True}
    preguntas = {str(p.pk): p for p in ronda.encuesta.preguntas.all()}
    if set(respuestas) - preguntas.keys():
        raise ValidationError("La respuesta contiene preguntas ajenas a esta encuesta.")
    post_data = QueryDict(mutable=True)
    for pregunta_id, valor in respuestas.items():
        pregunta = preguntas[pregunta_id]
        if valor is None:
            continue
        if pregunta.tipo == TipoPregunta.OPCION_MULTIPLE:
            if not isinstance(valor, list) or not all(
                isinstance(v, str) for v in valor
            ):
                raise ValidationError(
                    "Las opciones múltiples deben ser una lista de valores."
                )
            post_data.setlist(f"respuesta-{pregunta_id}", valor)
        else:
            if type(valor) not in (str, int, float):
                raise ValidationError("El valor de una respuesta no es válido.")
            post_data[f"respuesta-{pregunta_id}"] = str(valor).strip()
    registrar_respuesta(ronda, usuario, post_data)
    return {"respondida": True, "ya_registrada": False}
