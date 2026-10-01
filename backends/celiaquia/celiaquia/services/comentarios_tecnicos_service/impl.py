"""Comentarios técnicos de legajo y su publicación a la Provincia (issue #2318).

Reglas de negocio que implementa este servicio:

- Cada alta crea un comentario nuevo; nunca se sobrescriben los anteriores.
- Los comentarios nacen **internos**: sólo Nación los ve.
- La Provincia recibe únicamente los que tienen observaciones (``Sí``), y recién
  cuando el técnico solicita una subsanación o rechaza el legajo. Los ``No``
  quedan internos para siempre.
- En cada Subsanar/Rechazar, Nación **elige** qué observaciones forman parte de
  esa instancia (issue #2592). Solo esas arman el motivo y se publican; las
  demás quedan en el historial sin arrastrarse a la instancia nueva.
- El motivo se arma **en backend** concatenando las elegidas en orden
  cronológico y sin duplicados.
"""

import logging
import re

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone

from celiaquia.comentarios_tecnicos import (
    CODIGO_OTROS,
    TipoDocumentoComentario,
    es_codigo_valido,
    normalizar_tipo_documento,
    texto_observacion,
)
from celiaquia.models import ExpedienteCiudadano, HistorialComentarios

logger = logging.getLogger("django")

#: Texto que se guarda cuando la revisión no encontró observaciones.
TEXTO_SIN_OBSERVACIONES = "Sin observaciones."

#: Separador entre observaciones dentro del motivo concatenado.
SEPARADOR_OBSERVACIONES = "\n"

#: Separador entre el bloque concatenado y el texto libre complementario.
SEPARADOR_TEXTO_LIBRE = "\n\n"

_VALORES_SI = {"1", "true", "on", "yes", "si", "sí", "s"}
_VALORES_NO = {"0", "false", "off", "no", "n"}

_ESPACIOS = re.compile(r"\s+")


def normalizar_si_no(valor):
    """Interpreta el "¿Tiene observaciones?" del formulario.

    Devuelve ``True``/``False``, o ``None`` si el valor no es interpretable
    (campo vacío o basura), para que quien llama lo trate como falta de dato.
    """
    if isinstance(valor, bool):
        return valor
    texto = str(valor or "").strip().lower()
    if texto in _VALORES_SI:
        return True
    if texto in _VALORES_NO:
        return False
    return None


def _clave_dedup(tipo_documento, observacion_codigo, texto):
    """Clave de deduplicación de una observación.

    Para las observaciones del catálogo alcanza con (tipo, código). Para
    ``OTROS`` el texto es lo que distingue una de otra, así que entra normalizado
    para que dos redacciones idénticas salvo mayúsculas o espacios cuenten como
    una sola.
    """
    texto_normalizado = _ESPACIOS.sub(" ", (texto or "").strip()).casefold()
    return (tipo_documento or "", observacion_codigo or "", texto_normalizado)


def _clave(comentario):
    """Clave de deduplicación de un comentario técnico ya persistido."""
    return _clave_dedup(
        comentario.tipo_documento,
        comentario.observacion_codigo,
        comentario.comentario,
    )


def _linea(comentario):
    """Observación como línea de texto, prefijada por su tipo de documento."""
    etiquetas = dict(TipoDocumentoComentario.choices)
    etiqueta = etiquetas.get(comentario.tipo_documento, comentario.tipo_documento)
    return f"{etiqueta}: {comentario.comentario}"


class ComentariosTecnicosService:
    """Alta, consulta, concatenación y publicación de comentarios técnicos."""

    @staticmethod
    def registrar(  # pylint: disable=too-many-arguments
        legajo: ExpedienteCiudadano,
        *,
        tipo_documento,
        tiene_observaciones,
        observacion_codigo=None,
        observacion_libre="",
        usuario=None,
    ) -> HistorialComentarios:
        """Registra un comentario técnico interno sobre el legajo.

        Valida la combinación de opciones según el requerimiento: el tipo de
        documento es obligatorio, el Sí/No es obligatorio, y la observación se
        exige sólo cuando la respuesta es ``Sí``. Cuando es ``No`` la
        observación se descarta (la UI la oculta, pero el POST puede arrastrar
        el valor anterior).

        Devuelve el `HistorialComentarios` creado, siempre con
        ``es_interno=True``.
        """
        tipo = normalizar_tipo_documento(tipo_documento)
        if not tipo:
            raise ValidationError("Seleccioná un tipo de documento válido.")

        respuesta = normalizar_si_no(tiene_observaciones)
        if respuesta is None:
            raise ValidationError("Indicá si la revisión tiene observaciones.")

        if not respuesta:
            codigo = None
            texto = TEXTO_SIN_OBSERVACIONES
        else:
            codigo = (observacion_codigo or "").strip().upper()
            if not codigo:
                raise ValidationError("Seleccioná una observación.")
            if not es_codigo_valido(tipo, codigo):
                raise ValidationError(
                    "La observación seleccionada no corresponde al tipo de documento."
                )
            if codigo == CODIGO_OTROS:
                texto = (observacion_libre or "").strip()
                if not texto:
                    raise ValidationError(
                        'Redactá la observación cuando elegís la opción "Otros".'
                    )
            else:
                texto = texto_observacion(tipo, codigo)

        comentario = HistorialComentarios.objects.create(
            legajo=legajo,
            tipo_comentario=HistorialComentarios.TIPO_COMENTARIO_TECNICO,
            comentario=texto,
            usuario=usuario,
            estado_relacionado=legajo.revision_tecnico,
            es_interno=True,
            tipo_documento=tipo,
            tiene_observaciones=respuesta,
            observacion_codigo=codigo,
        )

        logger.info(
            "Comentario técnico registrado: legajo=%s tipo=%s observaciones=%s "
            "codigo=%s user=%s",
            legajo.pk,
            tipo,
            respuesta,
            codigo,
            getattr(usuario, "id", None),
        )
        return comentario

    @staticmethod
    def historial(legajo: ExpedienteCiudadano):
        """Comentarios técnicos del legajo en orden cronológico ascendente."""
        return (
            legajo.historial_comentarios.filter(
                tipo_comentario=HistorialComentarios.TIPO_COMENTARIO_TECNICO
            )
            .select_related("usuario")
            .order_by("fecha_creacion", "pk")
        )

    @staticmethod
    def deduplicar(comentarios):
        """Descarta las observaciones repetidas conservando la primera de cada una.

        Se usa tanto para armar el motivo como para no mostrarle a la Provincia
        la misma observación varias veces: el técnico puede registrarla más de
        una vez y el historial interno las conserva todas.
        """
        vistos = set()
        unicos = []
        for comentario in comentarios:
            clave = _clave(comentario)
            if clave in vistos:
                continue
            vistos.add(clave)
            unicos.append(comentario)
        return unicos

    @staticmethod
    def opciones_seleccionables(legajo: ExpedienteCiudadano):
        """Motivos que Nación puede elegir al Subsanar o Rechazar (issue #2592).

        Son las observaciones con ``Sí`` del legajo, de cualquier instancia y
        sin duplicados. Cada opción apunta al registro más reciente de su
        observación, y viene marcada como ``pendiente`` si alguno de sus
        registros sigue interno, es decir, si todavía no se le comunicó a la
        Provincia. La UI usa esa marca para tildarla de entrada; lo que cuenta
        es lo que se envía.

        Estructura: ``[{"id", "etiqueta", "pendiente"}, ...]``, en orden
        cronológico de su último registro.
        """
        grupos = {}
        for comentario in ComentariosTecnicosService.historial(legajo).filter(
            tiene_observaciones=True
        ):
            grupos.setdefault(_clave(comentario), []).append(comentario)

        opciones = sorted(
            (
                (comentarios[-1], any(c.es_interno for c in comentarios))
                for comentarios in grupos.values()
            ),
            key=lambda par: (par[0].fecha_creacion, par[0].pk),
        )
        return [
            {
                "id": comentario.pk,
                "etiqueta": _linea(comentario),
                "pendiente": pendiente,
            }
            for comentario, pendiente in opciones
        ]

    @staticmethod
    def resolver_seleccion(legajo: ExpedienteCiudadano, ids):
        """Comentarios técnicos elegidos para una subsanación o un rechazo.

        Valida que cada id sea un comentario técnico con ``Sí`` de este legajo:
        los ids llegan del cliente. Devuelve los comentarios en orden
        cronológico y sin duplicados, o lista vacía si no se eligió ninguno.
        """
        try:
            ids = {int(valor) for valor in ids or [] if str(valor).strip()}
        except (TypeError, ValueError) as exc:
            raise ValidationError("La selección de motivos no es válida.") from exc
        if not ids:
            return []

        comentarios = list(
            ComentariosTecnicosService.historial(legajo).filter(
                tiene_observaciones=True, pk__in=ids
            )
        )
        if len(comentarios) != len(ids):
            raise ValidationError(
                "Alguno de los motivos seleccionados no corresponde al legajo."
            )
        return ComentariosTecnicosService.deduplicar(comentarios)

    @staticmethod
    def lineas(comentarios):
        """Comentarios como líneas de texto, prefijadas por tipo de documento."""
        return [_linea(comentario) for comentario in comentarios]

    @staticmethod
    def componer_motivo(comentarios, texto_libre: str = "") -> str:
        """Motivo final de una subsanación o un rechazo.

        Une las observaciones **elegidas para esta instancia** con el texto
        libre complementario. No lee el historial del legajo a propósito: antes
        del issue #2592 concatenaba todas las observaciones con ``Sí`` y cada
        subsanación arrastraba los motivos de las anteriores.

        Sin observaciones ni texto libre no hay motivo que comunicar y se corta
        con `ValidationError`, sin tocar el estado del legajo.
        """
        concatenado = SEPARADOR_OBSERVACIONES.join(
            ComentariosTecnicosService.lineas(comentarios)
        )
        libre = (texto_libre or "").strip()

        if not concatenado and not libre:
            raise ValidationError(
                "Seleccioná al menos un motivo o completá la información "
                "complementaria para poder continuar."
            )

        partes = [parte for parte in (concatenado, libre) if parte]
        return SEPARADOR_TEXTO_LIBRE.join(partes)

    @staticmethod
    def publicar(legajo: ExpedienteCiudadano, *, comentarios, usuario=None) -> int:
        """Publica a la Provincia las observaciones elegidas para la instancia.

        Baja el flag `es_interno` y sella `publicado_en`/`publicado_por`, que es
        el registro de auditoría de la publicación. Alcanza también a los
        registros repetidos de una misma observación elegida, para que no
        vuelva a figurar como pendiente. Lo no elegido queda interno (issue
        #2592), y los ya publicados conservan la fecha y el usuario del evento
        original.

        Devuelve la cantidad de comentarios publicados en esta llamada.
        """
        claves = {_clave(comentario) for comentario in comentarios}
        if not claves:
            return 0

        ids = [
            comentario.pk
            for comentario in legajo.historial_comentarios.filter(
                Q(tipo_comentario=HistorialComentarios.TIPO_COMENTARIO_TECNICO)
                & Q(tiene_observaciones=True)
                & Q(es_interno=True)
            )
            if _clave(comentario) in claves
        ]
        if not ids:
            return 0

        publicados = HistorialComentarios.objects.filter(pk__in=ids).update(
            es_interno=False,
            publicado_en=timezone.now(),
            publicado_por=usuario,
        )

        logger.info(
            "Comentarios técnicos publicados a Provincia: legajo=%s cantidad=%s "
            "user=%s",
            legajo.pk,
            publicados,
            getattr(usuario, "id", None),
        )
        return publicados
