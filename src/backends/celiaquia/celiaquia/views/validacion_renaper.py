"""Validación de un legajo contra RENAPER.

La lógica vive en `celiaquia/services/validacion_renaper_service/`, para que la
API REST valide exactamente igual que esta pantalla. Acá quedan los permisos y
la traducción a HTTP.

Los helpers se reexportan con sus nombres viejos porque los tests y otros
módulos los importan desde acá.
"""

import logging

from django.core.exceptions import PermissionDenied, ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_protect

from celiaquia.models import ExpedienteCiudadano
from celiaquia.services import validacion_renaper_service
from celiaquia.services.validacion_renaper_service import (
    _build_datos_provincia,
    _build_error_log_data,
    _build_log_data,
    _consultar_datos_renaper_con_reintentos,
    _ejemplar_esta_vencido,
    _enriquecer_resultado_renaper,
    _es_dni_valido_para_renaper,
    _es_error_reintentable,
    _extraer_datos_ejemplar_dni,
    _formatear_datos_renaper,
    _formatear_fecha_renaper,
    _get_error_message,
    _get_renaper_retry_config,
    _log_datos_ejemplar,
    _log_respuesta_renaper,
    _mapear_sexo_para_renaper,
    _normalizar_documento_para_renaper,
    _parsear_fecha_ejemplar,
    _resolver_ciudad_provincia,
    _resolver_provincia_renaper,
    _resolver_sexo_y_consulta_renaper,
    _valor_ejemplar,
    EJEMPLAR_CAMPOS_DATO,
    EJEMPLAR_FORMATOS_FECHA,
    EJEMPLAR_PLACEHOLDERS,
    ESTADOS_VALIDACION,
    RENAPER_INVALID_RESPONSE_MESSAGE,
    RENAPER_NO_MATCH_MESSAGE,
    RENAPER_REMOTE_UNAVAILABLE_MESSAGE,
    RENAPER_TRANSIENT_ERROR_TYPES,
    ROLE_COORDINADOR_CELIAQUIA_PERMISSION,
    ROLE_TECNICO_CELIAQUIA_PERMISSION,
)

# Reexportados a proposito: los tests y otros modulos los importan desde aca.
__all__ = [
    "ValidacionRenaperView",
    "EJEMPLAR_CAMPOS_DATO",
    "EJEMPLAR_FORMATOS_FECHA",
    "EJEMPLAR_PLACEHOLDERS",
    "ESTADOS_VALIDACION",
    "RENAPER_INVALID_RESPONSE_MESSAGE",
    "RENAPER_NO_MATCH_MESSAGE",
    "RENAPER_REMOTE_UNAVAILABLE_MESSAGE",
    "RENAPER_TRANSIENT_ERROR_TYPES",
    "ROLE_COORDINADOR_CELIAQUIA_PERMISSION",
    "ROLE_TECNICO_CELIAQUIA_PERMISSION",
    "_build_datos_provincia",
    "_build_error_log_data",
    "_build_log_data",
    "_consultar_datos_renaper_con_reintentos",
    "_ejemplar_esta_vencido",
    "_enriquecer_resultado_renaper",
    "_es_dni_valido_para_renaper",
    "_es_error_reintentable",
    "_extraer_datos_ejemplar_dni",
    "_formatear_datos_renaper",
    "_formatear_fecha_renaper",
    "_get_error_message",
    "_get_renaper_retry_config",
    "_log_datos_ejemplar",
    "_log_respuesta_renaper",
    "_mapear_sexo_para_renaper",
    "_normalizar_documento_para_renaper",
    "_parsear_fecha_ejemplar",
    "_resolver_ciudad_provincia",
    "_resolver_provincia_renaper",
    "_resolver_sexo_y_consulta_renaper",
    "_valor_ejemplar",
]

logger = logging.getLogger(__name__)


ROLE_COORDINADOR_CELIAQUIA_PERMISSION = "auth.role_coordinadorceliaquia"
ROLE_TECNICO_CELIAQUIA_PERMISSION = "auth.role_tecnicoceliaquia"

RENAPER_TRANSIENT_ERROR_TYPES = {
    "timeout",
    "remote_error",
    "auth_error",
    "invalid_response",
    "unexpected_error",
}
RENAPER_REMOTE_UNAVAILABLE_MESSAGE = (
    "No pudimos validar con RENAPER en este momento. "
    "Por favor, intentá nuevamente en unos minutos."
)
RENAPER_INVALID_RESPONSE_MESSAGE = (
    "RENAPER devolvió una respuesta inválida y no pudimos completar la validación. "
    "Intentá nuevamente más tarde."
)
RENAPER_NO_MATCH_MESSAGE = (
    "RENAPER no pudo validar los datos ingresados. "
    "Verificá el DNI y el sexo registrados."
)


def _truncate(value, length=500):
    if isinstance(value, str) and len(value) > length:
        return f"{value[:length]}…"
    return value


# Datos del ejemplar del DNI. RENAPER los devuelve en el payload crudo, pero el
# dict mapeado por core.services.renaper (18 campos fijos) no los conserva, así
# que hasta ahora llegaban en cada consulta y se descartaban. Sirven como
# referencia para saber a qué versión del documento corresponde el domicilio
# informado, que es la duda que motiva el pedido.
EJEMPLAR_CAMPOS_DATO = ("emision", "vencimiento", "ejemplar")

# Criterio propio de esta vista, más amplio que el único filtro equivalente que
# hay en core (`_mapear_datos_renaper` descarta {"0", "", None} y sólo para
# `barrio`). Si un tercer módulo necesita el mismo criterio, conviene subirlo a
# core antes que volver a copiarlo.
EJEMPLAR_PLACEHOLDERS = {"", "0", "-", "n/a", "na", "s/d", "sd", "null", "none"}

# Formatos en los que puede llegar la fecha. El real, medido en producción, es
# dd/mm/aaaa; el ISO se contempla porque es el que _formatear_fecha_renaper ya
# venía convirtiendo para el resto de los campos.
EJEMPLAR_FORMATOS_FECHA = ("%d/%m/%Y", "%Y-%m-%d")


class ValidacionRenaperView(View):
    """Vista para validar datos del ciudadano contra Renaper"""

    def dispatch(self, request, *args, **kwargs):
        # Solo tecnica, coordinacion o admin. La regla vive en el service para
        # que la API pida exactamente lo mismo.
        if not request.user.is_authenticated:
            raise PermissionDenied("Autenticación requerida.")
        if not validacion_renaper_service.puede_validar(request.user):
            raise PermissionDenied("Permiso denegado.")

        return super().dispatch(request, *args, **kwargs)

    @method_decorator(csrf_protect)
    def post(self, request, pk, legajo_id):
        # Si viene el parámetro 'validacion_estado', guardar el estado.
        validacion_estado = request.POST.get("validacion_estado")
        if validacion_estado:
            return self._guardar_validacion_estado(
                request, pk, legajo_id, validacion_estado
            )

        # Si no, hacer la consulta normal a Renaper.
        return self._consultar_renaper(request, pk, legajo_id)

    def _guardar_validacion_estado(self, request, pk, legajo_id, validacion_estado):
        """Guarda el estado de validación Renaper (1=correcto, 2=incorrecto, 3=subsanar)."""
        try:
            # Dentro del try a proposito: un fallo al resolver el legajo tambien
            # tiene que salir como 500 con mensaje generico, igual que antes.
            legajo = get_object_or_404(
                ExpedienteCiudadano, pk=legajo_id, expediente__pk=pk
            )
            etiqueta = validacion_renaper_service.guardar_estado(
                legajo,
                validacion_estado,
                request.user,
                comentario=request.POST.get("comentario") or "",
            )
        except ValidationError as exc:
            return JsonResponse({"success": False, "error": exc.messages[0]})
        except Exception:  # pylint: disable=broad-exception-caught
            logger.error(
                "renaper.validation.status_error",
                extra={
                    "data": {
                        "legajo_id": legajo_id,
                        "expediente_id": pk,
                        "user_id": getattr(request.user, "id", None),
                    }
                },
            )
            return JsonResponse(
                {
                    "success": False,
                    "error": "No se pudo guardar la validación por un error interno.",
                },
                status=500,
            )
        return JsonResponse(
            {
                "success": True,
                "message": f"Validación Renaper guardada: {etiqueta}",
                "validacion_estado": int(validacion_estado),
            }
        )

    def _consultar_renaper(self, request, pk, legajo_id):
        """Consulta Renaper y devuelve la comparación contra los datos cargados."""
        legajo = get_object_or_404(ExpedienteCiudadano, pk=legajo_id, expediente__pk=pk)
        payload, status = validacion_renaper_service.consultar(legajo, request.user)
        return JsonResponse(payload, status=status)
