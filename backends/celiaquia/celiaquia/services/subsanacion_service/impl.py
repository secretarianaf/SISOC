"""Servicio de subsanaciones (Fase 2).

La provincia responde una subsanación adjuntando uno o varios archivos. La
documentación corregida se incorpora como evidencia nueva (`SubsanacionArchivo`)
SIN reemplazar los archivos originales del legajo (archivo1/2/3), preservando la
trazabilidad histórica.

Ese mismo modelo guarda la documentación complementaria que Nación adjunta al
solicitar la subsanación (issue #2523); las distingue `SubsanacionArchivo.origen`.
Toda lectura que pregunte "¿ya respondió la Provincia?" tiene que filtrar por
origen: ver `tiene_evidencia`.
"""

import logging

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from celiaquia.models import (
    ExpedienteCiudadano,
    OrigenArchivoSubsanacion,
    RevisionTecnico,
    SubsanacionArchivo,
    SubsanacionEstado,
    SubsanacionObservacion,
)
from celiaquia.services.comentarios_service import ComentariosService
from celiaquia.validators import validar_archivos_complementarios

logger = logging.getLogger("django")


class SubsanacionService:
    @staticmethod
    def subsanacion_activa(legajo: ExpedienteCiudadano):
        """Devuelve la subsanación del ciclo actual del legajo (la más reciente),
        ya sea que esté pendiente de respuesta o ya respondida pero aún no
        confirmada. None si el legajo no tiene subsanaciones."""
        return legajo.subsanaciones.order_by("-solicitada_en", "-pk").first()

    @staticmethod
    def tiene_evidencia(legajo: ExpedienteCiudadano) -> bool:
        """True si la subsanación activa del legajo tiene evidencia de respuesta.

        Cuenta como evidencia un archivo nuevo (SubsanacionArchivo) del flujo
        actual o, por compatibilidad con subsanaciones en curso al momento del
        despliegue, una respuesta del flujo anterior (SubsanacionRespuesta)
        registrada durante el ciclo actual.

        **Solo cuentan los archivos cargados por la Provincia.** La misma
        relación guarda la documentación complementaria que adjunta Nación al
        pedir la subsanación (issue #2523), y esa no es una respuesta: sin el
        filtro, pedir subsanación con documentación adjunta habilitaría el
        confirmar de la Provincia sin que haya subido nada."""
        subsanacion = SubsanacionService.subsanacion_activa(legajo)
        if subsanacion is None:
            return False
        if subsanacion.archivos.filter(
            origen=OrigenArchivoSubsanacion.PROVINCIA
        ).exists():
            return True
        # Compatibilidad hacia atrás: respuesta cargada por el flujo previo
        # (reemplazo de archivos) dentro del ciclo de subsanación vigente.
        return legajo.subsanaciones_respuestas.filter(
            creado_en__gte=subsanacion.solicitada_en
        ).exists()

    @staticmethod
    def legajos_sin_evidencia(expediente):
        """Legajos en SUBSANAR cuya subsanación activa todavía no tiene archivos
        de respuesta cargados. Excluye las subsanaciones RENAPER
        (estado_validacion_renaper=3), que se responden por su propio flujo."""
        legajos = (
            expediente.expediente_ciudadanos.filter(
                revision_tecnico=RevisionTecnico.SUBSANAR
            )
            .exclude(estado_validacion_renaper=3)
            .select_related("ciudadano")
        )
        return [
            legajo
            for legajo in legajos
            if not SubsanacionService.tiene_evidencia(legajo)
        ]

    @staticmethod
    @staticmethod
    def exigir_puede_confirmar(legajo) -> None:
        """Guard previo a pasar un legajo de SUBSANAR a SUBSANADO.

        Vivia dentro de `ExpedienteConfirmSubsanacionView`. Se extrae para que
        la API aplique lo mismo: confirmar sin evidencia dejaria al tecnico
        aprobando un legajo que nadie corrigio.
        """

        from celiaquia.models import RevisionTecnico

        if legajo.revision_tecnico != RevisionTecnico.SUBSANAR:
            raise ValidationError("El legajo no tiene una subsanación pendiente.")
        if legajo.estado_validacion_renaper == 3:
            raise ValidationError("El legajo tiene una subsanación Renaper pendiente.")
        if not legajo.archivo2 or not legajo.archivo3:
            raise ValidationError(
                "El legajo no tiene los archivos obligatorios (archivo2 y archivo3)."
            )
        if not SubsanacionService.tiene_evidencia(legajo):
            raise ValidationError(
                "Debés adjuntar al menos un archivo de subsanación antes de confirmar."
            )

    @staticmethod
    @transaction.atomic
    def confirmar(legajo, usuario):
        """Pasa el legajo a SUBSANADO, que es lo que habilita volver a evaluarlo."""

        from celiaquia.models import RevisionTecnico

        SubsanacionService.exigir_puede_confirmar(legajo)
        legajo.revision_tecnico = RevisionTecnico.SUBSANADO
        legajo.modificado_en = timezone.now()
        legajo.subsanacion_enviada_en = timezone.now()
        legajo.subsanacion_usuario = usuario
        legajo.save()
        logger.info(
            "Subsanacion confirmada - Legajo: %s, Usuario: %s",
            legajo.pk,
            getattr(usuario, "id", None),
        )
        return legajo

    @staticmethod
    def exigir_puede_responder(legajo: ExpedienteCiudadano) -> None:
        """Guard previo a responder una subsanacion.

        Vivia en `SubsanacionRespuestaUploadView`. Se extrae para que la API y
        la pantalla rechacen exactamente los mismos casos: sin esto, un legajo
        con subsanacion Renaper pendiente podria responderse por la API y no por
        la pantalla.
        """

        from celiaquia.models import RevisionTecnico

        if legajo.revision_tecnico != RevisionTecnico.SUBSANAR:
            raise ValidationError("El legajo no tiene una subsanación técnica activa.")
        if legajo.estado_validacion_renaper == 3:
            raise ValidationError("El legajo tiene una subsanación Renaper pendiente.")

    @staticmethod
    def adjuntar_documentacion_complementaria(subsanacion, archivos, usuario=None):
        """Documentación complementaria que Nación adjunta al pedir la subsanación.

        A diferencia de las observaciones, no cuelga de una observación puntual:
        acompaña a la solicitud entera (issue #2523). Es opcional — sin archivos
        no hace nada y devuelve lista vacía, para no bloquear la acción.

        Valida el lote antes de escribir. Se espera que el llamador la invoque
        dentro de la transacción que cambia el estado del legajo, para que la
        subsanación y su documentación entren o no entren juntas.
        """
        archivos = validar_archivos_complementarios(archivos)
        if not archivos:
            return []

        creados = [
            SubsanacionArchivo.objects.create(
                subsanacion=subsanacion,
                archivo=archivo,
                usuario=usuario,
                origen=OrigenArchivoSubsanacion.NACION,
            )
            for archivo in archivos
        ]

        logger.info(
            "Documentación complementaria adjuntada a subsanación %s por user=%s: "
            "%s archivo(s).",
            subsanacion.pk,
            getattr(usuario, "id", None),
            len(creados),
        )
        return creados

    @staticmethod
    @transaction.atomic
    def responder(
        legajo: ExpedienteCiudadano,
        archivos,
        usuario=None,
        descripcion: str = "",
        observacion_id=None,
    ):
        """Registra la respuesta de la provincia a la subsanación activa del
        legajo: crea un SubsanacionArchivo por cada archivo adjunto (evidencia
        nueva) y marca la subsanación como RESPONDIDA. No modifica los archivos
        originales del legajo."""
        archivos = [a for a in (archivos or []) if a]
        if not archivos:
            raise ValidationError("Debés adjuntar al menos un archivo.")

        subsanacion = SubsanacionService.subsanacion_activa(legajo)
        if subsanacion is None:
            raise ValidationError(
                "El legajo no tiene una subsanación activa para responder."
            )

        observacion = None
        if observacion_id:
            observacion = SubsanacionObservacion.objects.filter(
                pk=observacion_id, subsanacion=subsanacion
            ).first()
            if observacion is None:
                raise ValidationError(
                    "La observación seleccionada no pertenece a la subsanación activa."
                )

        descripcion = (descripcion or "").strip()[:255]
        creados = [
            SubsanacionArchivo.objects.create(
                subsanacion=subsanacion,
                observacion=observacion,
                archivo=archivo,
                descripcion=descripcion,
                usuario=usuario,
                origen=OrigenArchivoSubsanacion.PROVINCIA,
            )
            for archivo in archivos
        ]

        subsanacion.estado = SubsanacionEstado.RESPONDIDA
        subsanacion.respondida_por = usuario
        subsanacion.respondida_en = timezone.now()
        subsanacion.save(update_fields=["estado", "respondida_por", "respondida_en"])

        comentario = f"La provincia adjuntó {len(creados)} archivo(s) de subsanación."
        if descripcion:
            comentario = f"{comentario} {descripcion}"
        try:
            ComentariosService.agregar_subsanacion_respuesta(
                legajo=legajo,
                respuesta=comentario,
                usuario=usuario,
                archivo_adjunto=creados[0].archivo if creados else None,
            )
        except Exception as exc:  # pragma: no cover - traza no crítica
            logger.warning(
                "No se pudo registrar el comentario de respuesta de subsanación "
                "para legajo %s: %s",
                legajo.pk,
                exc,
            )

        logger.info(
            "Subsanación %s respondida por user=%s con %s archivo(s) (legajo=%s).",
            subsanacion.pk,
            getattr(usuario, "id", None),
            len(creados),
            legajo.pk,
        )
        return subsanacion
