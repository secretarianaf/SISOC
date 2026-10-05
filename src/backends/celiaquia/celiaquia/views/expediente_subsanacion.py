import logging
from django.views import View
from django.http import HttpResponseNotAllowed
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from django.db.models import Q
from django.utils import timezone

from celiaquia.models import Expediente, ExpedienteCiudadano, RevisionTecnico
from celiaquia.permissions import can_confirm_subsanacion
from celiaquia.services.subsanacion_service import SubsanacionService
from celiaquia.utils import error_response, success_response

logger = logging.getLogger("django")


def _same_owner(user, exp) -> bool:
    """Verifica si el usuario es el propietario del expediente."""
    return exp.usuario_provincia_id == user.id


class ExpedienteConfirmSubsanacionView(View):
    """Vista para confirmar la subsanación de legajos en un expediente."""

    def get(self, *_a, **_k):
        return HttpResponseNotAllowed(["POST"])

    @method_decorator(csrf_protect)
    def post(self, request, pk):
        exp = get_object_or_404(Expediente, pk=pk)

        # Validar permisos usando función centralizada
        can_confirm_subsanacion(request.user, exp)

        # Verificar si es confirmación individual o masiva
        legajo_id = request.POST.get("legajo_id")
        if legajo_id:
            return self._confirmar_individual(request, exp, legajo_id)
        return self._confirmar_masiva(request, exp)

    def _confirmar_individual(self, request, exp, legajo_id):
        legajo = get_object_or_404(
            ExpedienteCiudadano,
            pk=legajo_id,
            expediente=exp,
            revision_tecnico=RevisionTecnico.SUBSANAR,
        )
        try:
            SubsanacionService.confirmar(legajo, request.user)
        except ValidationError as exc:
            return error_response("; ".join(exc.messages), status=400)
        return success_response("Subsanación confirmada correctamente.")

    def _confirmar_masiva(self, request, exp):
        # Confirmación masiva de subsanaciones técnicas. Las subsanaciones RENAPER
        # (estado_validacion_renaper=3) se confirman por su propio flujo, por lo
        # que se excluyen de la masiva.
        base_qs = ExpedienteCiudadano.objects.filter(
            expediente=exp, revision_tecnico=RevisionTecnico.SUBSANAR
        ).exclude(estado_validacion_renaper=3)

        query_archivos_faltantes = (
            Q(archivo2__isnull=True)
            | Q(archivo2="")
            | Q(archivo3__isnull=True)
            | Q(archivo3="")
        )
        legajos_sin_archivos = base_qs.filter(query_archivos_faltantes)

        if legajos_sin_archivos.exists():
            dnis = list(
                legajos_sin_archivos.values_list("ciudadano__documento", flat=True)[:10]
            )
            return error_response(
                "Hay legajos en SUBSANAR que aún no tienen los archivos obligatorios (archivo2 y archivo3).",
                status=400,
                extra_data={"ejemplo_dnis": dnis},
            )

        # Cada legajo debe tener evidencia de subsanación cargada.
        sin_evidencia = SubsanacionService.legajos_sin_evidencia(exp)
        if sin_evidencia:
            dnis = [legajo.ciudadano.documento for legajo in sin_evidencia[:10]]
            return error_response(
                "Hay legajos en SUBSANAR sin archivos de subsanación cargados.",
                status=400,
                extra_data={"ejemplo_dnis": dnis},
            )

        # Cambiar SUBSANAR → SUBSANADO (excluyendo subsanaciones RENAPER)
        actualizados = base_qs.update(
            revision_tecnico=RevisionTecnico.SUBSANADO,
            modificado_en=timezone.now(),
            subsanacion_enviada_en=timezone.now(),
            subsanacion_usuario=request.user,
        )

        logger.info(
            "Subsanación masiva confirmada - Expediente: %s, Usuario: %s, Legajos actualizados: %s",
            exp.pk,
            request.user.id,
            actualizados,
        )

        return success_response(
            f"Se confirmaron {actualizados} legajos como SUBSANADO."
        )
