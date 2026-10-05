"""Revision tecnica de legajos: aprobar, rechazar, subsanar y eliminar.

Estas reglas vivian dentro de `RevisarLegajoView`. Se extraen aca por el mismo
motivo que `celiaquia/scope.py`: la API REST tiene que ejecutar **exactamente**
el mismo flujo que la pantalla. Duplicarlo es la forma mas facil de que un
legajo quede aprobado sin liberar el cupo, sin historial o sin publicar las
observaciones al usuario provincial.

La vista sigue siendo la duena de parsear el request (los formatos del POST son
suyos); de aca sale que significa cada accion.
"""

from __future__ import annotations

import logging
from typing import Iterable

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from celiaquia.comentarios_tecnicos import TipoDocumentoComentario
from celiaquia.models import (
    Expediente,
    ExpedienteCiudadano,
    HistorialValidacionTecnica,
    RevisionTecnico,
    Subsanacion,
    SubsanacionEstado,
    SubsanacionObservacion,
    TipoSubsanacion,
)
from celiaquia.permissions import can_delete_legajo
from celiaquia.scope import is_admin, is_coordinador, is_provincial, is_tecnico
from celiaquia.services.comentarios_tecnicos_service import ComentariosTecnicosService
from celiaquia.services.cupo_service import CupoService
from celiaquia.services.subsanacion_service import SubsanacionService
from celiaquia.services.validacion_edad_service import ValidacionEdadService
from celiaquia.validators import validar_archivos_complementarios
from core.soft_delete.preview import build_delete_preview
from core.soft_delete.view_helpers import is_soft_deletable_instance

logger = logging.getLogger("django")

#: Los comentarios tecnicos se registran por tipo de documento; las
#: observaciones de la Fase 2 usan las categorias previas. ANSES y condicion
#: diagnostica son ambas cuestiones de documentacion respaldatoria.
MAPA_TIPO_DOCUMENTO_A_SUBSANACION = {
    TipoDocumentoComentario.RENAPER.value: TipoSubsanacion.RENAPER,
    TipoDocumentoComentario.ANSES.value: TipoSubsanacion.DOCUMENTACION,
    TipoDocumentoComentario.CONDICION_DIAGNOSTICA.value: TipoSubsanacion.DOCUMENTACION,
}

ACCIONES_REVISION = ("APROBAR", "RECHAZAR", "SUBSANAR", "ELIMINAR")

#: Desde que estados se puede pedir cada accion. Un legajo ya aprobado o
#: rechazado es final: se corrige por `CorregirEvaluacionView`, no por aca.
TRANSICIONES_PERMITIDAS = {
    RevisionTecnico.PENDIENTE: {"APROBAR", "RECHAZAR", "SUBSANAR"},
    RevisionTecnico.SUBSANADO: {"APROBAR", "RECHAZAR", "SUBSANAR"},
}


class RevisionService:
    """Acciones de revision tecnica sobre un legajo."""

    # --- Permisos ----------------------------------------------------------

    @staticmethod
    def es_solo_provincia(usuario) -> bool:
        """Provincia sin rol de Nacion: lo unico que puede hacer es ELIMINAR."""

        return is_provincial(usuario) and not (
            is_admin(usuario) or is_tecnico(usuario) or is_coordinador(usuario)
        )

    @staticmethod
    def verificar_permiso(usuario, expediente: Expediente, accion: str) -> None:
        """Valida quien puede ejecutar la accion. Levanta `PermissionDenied`.

        La provincia sin rol tecnico/coordinador solo puede ELIMINAR, y el
        limite de cuando puede hacerlo lo pone `can_delete_legajo`. Aprobar,
        rechazar y subsanar quedan reservados a tecnicos y coordinadores.
        """

        es_admin = is_admin(usuario)
        es_tecnico = is_tecnico(usuario)
        es_coord = is_coordinador(usuario)

        if RevisionService.es_solo_provincia(usuario):
            if accion != "ELIMINAR":
                raise PermissionDenied("Permiso denegado.")
            return

        if not (es_admin or es_tecnico or es_coord):
            raise PermissionDenied("Permiso denegado.")

        # Los tecnicos operan solo sobre lo que tienen asignado; coordinacion y
        # admin quedan exceptuados.
        if not (es_admin or es_coord):
            tecnicos_ids = [
                t.tecnico_id for t in expediente.asignaciones_tecnicos.all()
            ]
            if usuario.id not in tecnicos_ids:
                raise PermissionDenied("No sos un técnico asignado.")

        if accion == "ELIMINAR" and not (es_admin or es_coord):
            raise PermissionDenied("Solo coordinadores pueden eliminar legajos.")

    # --- Validacion --------------------------------------------------------

    @staticmethod
    def validar_accion(accion: str) -> str:
        accion = (accion or "").upper()
        if accion not in ACCIONES_REVISION:
            raise ValidationError("Acción inválida.")
        return accion

    @staticmethod
    def validar_transicion(legajo: ExpedienteCiudadano, accion: str) -> None:
        """Verifica que la accion sea legal para el estado actual del legajo."""

        if accion not in ("APROBAR", "RECHAZAR", "SUBSANAR"):
            return

        estado_actual = legajo.revision_tecnico
        if estado_actual in (RevisionTecnico.APROBADO, RevisionTecnico.RECHAZADO):
            raise ValidationError(
                f"No se puede modificar un legajo en estado {estado_actual}."
            )

        if accion not in TRANSICIONES_PERMITIDAS.get(estado_actual, set()):
            raise ValidationError(
                "La acción solicitada no es válida para el estado actual "
                f"del legajo ({estado_actual})."
            )

    # --- Observaciones -----------------------------------------------------

    @staticmethod
    def resolver_seleccion(legajo: ExpedienteCiudadano, ids):
        """Comentarios tecnicos elegidos para esta instancia, a partir de sus ids.

        Lo que manda el cliente son los ids; el texto sale de la base. Asi la
        API y la pantalla no pueden publicar un texto distinto del registrado.
        """

        return ComentariosTecnicosService.resolver_seleccion(legajo, ids)

    @staticmethod
    def componer_motivo(comentarios, texto_libre: str = "") -> str:
        """Motivo final = observaciones **elegidas** + texto libre.

        Toma los comentarios de esta instancia y no el historial del legajo: de
        lo contrario cada subsanacion arrastraria los motivos de las anteriores
        (issue #2592).
        """

        return ComentariosTecnicosService.componer_motivo(comentarios, texto_libre)

    @staticmethod
    def observaciones_desde_comentarios_tecnicos(comentarios):
        """Observaciones (tipo, detalle) derivadas de los comentarios elegidos.

        Lista vacia si no se eligio ninguno: el llamador decide si cae al
        formato previo al issue #2318.
        """

        return [
            (
                MAPA_TIPO_DOCUMENTO_A_SUBSANACION.get(
                    comentario.tipo_documento, TipoSubsanacion.OTROS
                ),
                comentario.comentario,
            )
            for comentario in comentarios or []
        ]

    @staticmethod
    def normalizar_observaciones(
        observaciones: Iterable, motivo_general: str = ""
    ) -> list:
        """Filtra a los tipos validos y recorta los detalles a 500 caracteres.

        Sirve para la entrada de la API, que llega como lista de pares
        `(tipo, detalle)`. Si no queda ninguna valida, devuelve una de OTROS con
        el motivo general, para que la subsanacion nunca quede sin observacion.

        No deduplica por tipo: la pantalla admite varias observaciones del
        mismo tipo con detalles distintos y cada una es un pedido aparte.
        """

        tipos_validos = {value for value, _ in TipoSubsanacion.choices}
        normalizadas = []
        for tipo, detalle in observaciones or []:
            tipo = (tipo or "").strip().upper()
            detalle = (detalle or "").strip()
            if tipo in tipos_validos:
                normalizadas.append((tipo, detalle[:500]))

        if not normalizadas:
            normalizadas.append((TipoSubsanacion.OTROS, (motivo_general or "")[:500]))
        return normalizadas

    # --- Cupo --------------------------------------------------------------

    @staticmethod
    def liberar_cupo_si_corresponde(
        legajo: ExpedienteCiudadano, usuario, accion: str
    ) -> bool:
        """Saca al legajo del cupo cuando se rechaza o se manda a subsanar.

        El error al liberar no aborta la revision: se registra y se sigue, tal
        como hacia la vista. Un cupo que no se libero se corrige despues; una
        revision a medias deja el legajo en un estado inconsistente.
        """

        if accion not in ("RECHAZAR", "SUBSANAR") or legajo.estado_cupo != "DENTRO":
            return False

        try:
            CupoService.liberar_slot(
                legajo=legajo,
                usuario=usuario,
                motivo=f"Salida del cupo por {accion.lower()} técnico en expediente",
            )
            legajo.estado_cupo = "NO_EVAL"
            legajo.es_titular_activo = False
            return True
        except Exception as exc:  # pylint: disable=broad-except
            logger.error(
                "Error al liberar cupo para legajo %s: %s",
                legajo.pk,
                exc,
                exc_info=True,
            )
            return False

    # --- Acciones ----------------------------------------------------------

    @staticmethod
    def aprobar(legajo: ExpedienteCiudadano, usuario) -> dict:
        estado_anterior = legajo.revision_tecnico
        legajo.revision_tecnico = RevisionTecnico.APROBADO
        # Un legajo aprobado no puede quedar con RENAPER sin validar.
        if getattr(legajo, "estado_validacion_renaper", 0) == 0:
            legajo.estado_validacion_renaper = 1

        legajo.save(
            update_fields=[
                "revision_tecnico",
                "estado_validacion_renaper",
                "modificado_en",
                "estado_cupo",
                "es_titular_activo",
            ]
        )

        HistorialValidacionTecnica.objects.create(
            legajo=legajo,
            estado_anterior=estado_anterior,
            estado_nuevo=RevisionTecnico.APROBADO,
            usuario=usuario,
            motivo=None,
        )

        return {
            "success": True,
            "estado": legajo.revision_tecnico,
            "cupo_liberado": False,
        }

    @staticmethod
    def rechazar(
        legajo: ExpedienteCiudadano, usuario, motivo: str, *, comentarios=()
    ) -> dict:
        """Rechaza el legajo y publica a la Provincia las observaciones elegidas."""

        estado_anterior = legajo.revision_tecnico
        legajo.revision_tecnico = RevisionTecnico.RECHAZADO
        if getattr(legajo, "estado_validacion_renaper", 0) == 0:
            legajo.estado_validacion_renaper = 2

        with transaction.atomic():
            legajo.save(
                update_fields=[
                    "revision_tecnico",
                    "estado_validacion_renaper",
                    "modificado_en",
                    "estado_cupo",
                    "es_titular_activo",
                ]
            )

            HistorialValidacionTecnica.objects.create(
                legajo=legajo,
                estado_anterior=estado_anterior,
                estado_nuevo=RevisionTecnico.RECHAZADO,
                usuario=usuario,
                motivo=motivo,
            )

            publicados = ComentariosTecnicosService.publicar(
                legajo, comentarios=comentarios, usuario=usuario
            )

        return {
            "success": True,
            "estado": legajo.revision_tecnico,
            "cupo_liberado": True,
            "comentarios_publicados": publicados,
        }

    @staticmethod
    def subsanar(
        legajo: ExpedienteCiudadano,
        usuario,
        motivo: str,
        *,
        tipo_subsanacion: str = "",
        comentarios=(),
        documentacion_complementaria=None,
        observaciones_fallback: Iterable | None = None,
    ) -> dict:
        """Marca el legajo para subsanar y crea la solicitud con observaciones.

        `comentarios` son los comentarios tecnicos elegidos para esta instancia
        (issue #2592). `observaciones_fallback` solo se usa si no se eligio
        ninguno, para no romper los legajos previos al issue #2318.

        `documentacion_complementaria` son los archivos que Nacion adjunta a la
        solicitud (issue #2523). Se validan **antes** de tocar el estado del
        legajo: un archivo invalido no puede dejar la subsanacion a medias.
        """

        complementaria = validar_archivos_complementarios(documentacion_complementaria)

        observaciones = RevisionService.observaciones_desde_comentarios_tecnicos(
            comentarios
        ) or RevisionService.normalizar_observaciones(observaciones_fallback, motivo)

        estado_anterior = legajo.revision_tecnico
        legajo.revision_tecnico = RevisionTecnico.SUBSANAR
        # Campos legacy: se preserva el primer tipo y el motivo general para
        # compatibilidad con la UI y los datos previos a la Fase 1.
        legajo.subsanacion_tipo = (
            observaciones[0][0] if observaciones else (tipo_subsanacion or None)
        )
        legajo.subsanacion_motivo = motivo
        legajo.subsanacion_solicitada_en = timezone.now()
        legajo.subsanacion_usuario = usuario
        # La subsanacion tecnica no marca estado_validacion_renaper=3: ese
        # estado queda para la validacion RENAPER real.

        with transaction.atomic():
            legajo.save(
                update_fields=[
                    "revision_tecnico",
                    "subsanacion_tipo",
                    "subsanacion_motivo",
                    "subsanacion_solicitada_en",
                    "subsanacion_usuario",
                    "modificado_en",
                    "estado_cupo",
                    "es_titular_activo",
                ]
            )

            HistorialValidacionTecnica.objects.create(
                legajo=legajo,
                estado_anterior=estado_anterior,
                estado_nuevo=RevisionTecnico.SUBSANAR,
                usuario=usuario,
                motivo=motivo,
            )

            subsanacion = Subsanacion.objects.create(
                legajo=legajo,
                estado=SubsanacionEstado.PENDIENTE,
                motivo_general=motivo,
                solicitada_por=usuario,
            )
            SubsanacionObservacion.objects.bulk_create(
                [
                    SubsanacionObservacion(
                        subsanacion=subsanacion, tipo=tipo, detalle=detalle
                    )
                    for tipo, detalle in observaciones
                ]
            )

            adjuntos = SubsanacionService.adjuntar_documentacion_complementaria(
                subsanacion, complementaria, usuario=usuario
            )

            publicados = ComentariosTecnicosService.publicar(
                legajo, comentarios=comentarios, usuario=usuario
            )

        return {
            "success": True,
            "estado": str(RevisionTecnico.SUBSANAR),
            "cupo_liberado": True,
            "subsanacion_id": subsanacion.pk,
            "observaciones": len(observaciones),
            "documentacion_complementaria": len(adjuntos),
            "comentarios_publicados": publicados,
        }

    @staticmethod
    def preview_eliminacion(legajo: ExpedienteCiudadano) -> dict | None:
        """Que se lleva puesto la baja en cascada, antes de confirmarla."""

        if not is_soft_deletable_instance(legajo):
            return None
        payload = {"success": True, "preview": build_delete_preview(legajo)}
        advertencia = ValidacionEdadService.advertencia_por_eliminacion(legajo)
        if advertencia:
            payload["menores_sin_responsable"] = advertencia
        return payload

    @staticmethod
    def eliminar(
        legajo: ExpedienteCiudadano,
        usuario,
        *,
        revalidar_baja_provincial: bool = False,
    ) -> dict:
        """Baja logica en cascada, liberando el cupo si estaba ocupado.

        `revalidar_baja_provincial` re-chequea el permiso con el expediente
        bloqueado: entre que la provincia abre el modal y confirma, el
        expediente puede haber cambiado de estado.

        Para la provincia el chequeo corre **siempre**, lo pida o no el
        llamador: `verificar_permiso` la deja pasar en ELIMINAR justamente
        porque el limite (estado EN_ESPERA y alcance territorial) lo pone
        `can_delete_legajo`. Un llamador que lo olvide no puede saltearlo.
        """

        revalidar = revalidar_baja_provincial or RevisionService.es_solo_provincia(
            usuario
        )
        with transaction.atomic():
            if revalidar:
                expediente_bloqueado = (
                    Expediente.objects.select_for_update()
                    .select_related("estado")
                    .get(pk=legajo.expediente_id)
                )
                legajo = (
                    ExpedienteCiudadano.objects.select_for_update()
                    .select_related("ciudadano")
                    .get(pk=legajo.pk, expediente=expediente_bloqueado)
                )
                can_delete_legajo(usuario, expediente_bloqueado, legajo)

            estado_expediente = getattr(
                getattr(legajo.expediente, "estado", None), "nombre", ""
            )

            if legajo.estado_cupo == "DENTRO":
                try:
                    CupoService.liberar_slot(
                        legajo=legajo,
                        usuario=usuario,
                        motivo="Eliminación de legajo del expediente",
                    )
                except Exception as exc:  # pylint: disable=broad-except
                    logger.error(
                        "Error al liberar cupo para legajo %s: %s",
                        legajo.pk,
                        exc,
                        exc_info=True,
                    )

            if is_soft_deletable_instance(legajo):
                legajo.delete(user=usuario, cascade=True)
            else:
                legajo.delete()

        logger.info(
            "Legajo %s eliminado por user=%s (expediente=%s, estado=%s).",
            legajo.pk,
            getattr(usuario, "id", None),
            legajo.expediente_id,
            estado_expediente,
        )
        return {"success": True, "message": "Legajo eliminado correctamente."}


__all__ = [
    "ACCIONES_REVISION",
    "MAPA_TIPO_DOCUMENTO_A_SUBSANACION",
    "TRANSICIONES_PERMITIDAS",
    "RevisionService",
]
