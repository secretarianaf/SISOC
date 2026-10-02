"""Validacion de un legajo contra RENAPER.

Estas reglas vivian dentro de `celiaquia/views/validacion_renaper.py`. Se
extraen para que la API REST y la pantalla hagan exactamente lo mismo: el mismo
mapeo de sexo y documento, los mismos reintentos, el mismo criterio de match y
el mismo guardado del estado 1/2/3.

El movimiento fue verbatim. La vista reexporta los helpers con sus nombres
viejos para no romper a quien los importe.

La conexion con RENAPER no vive aca: la resuelve
`core.services.renaper.consultar_datos_renaper`, que es el contrato compartido
con el resto del sistema.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

from core.models import Provincia
from core.services.renaper import consultar_datos_renaper

from celiaquia.models import ExpedienteCiudadano
from celiaquia.scope import (
    ROLE_COORDINADOR_CELIAQUIA_PERMISSION,
    ROLE_TECNICO_CELIAQUIA_PERMISSION,
    is_admin,
    user_has_permission,
)
from celiaquia.services.legajo_service import LegajoService

logger = logging.getLogger(__name__)

_has_permission = user_has_permission
_is_admin = is_admin


# --- Constantes movidas desde la vista -------------------------------------

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
EJEMPLAR_CAMPOS_DATO = ("emision", "vencimiento", "ejemplar")
EJEMPLAR_PLACEHOLDERS = {"", "0", "-", "n/a", "na", "s/d", "sd", "null", "none"}
EJEMPLAR_FORMATOS_FECHA = ("%d/%m/%Y", "%Y-%m-%d")


# --- Helpers movidos desde la vista (sin cambios) --------------------------


def _build_log_data(
    user,
    legajo=None,
    ciudadano=None,
):
    data = {
        "user_id": getattr(user, "id", None),
        "legajo_id": getattr(legajo, "pk", None),
        "expediente_id": getattr(legajo, "expediente_id", None),
        "ciudadano_id": getattr(ciudadano, "id", None),
    }
    return {k: v for k, v in data.items() if v is not None}


def _mapear_sexo_para_renaper(ciudadano):
    sexo_map = {"Masculino": "M", "Femenino": "F", "X": "X"}
    sexo_valor = (getattr(getattr(ciudadano, "sexo", None), "sexo", "") or "").strip()
    return sexo_map.get(sexo_valor)


def _normalizar_documento_para_renaper(documento_original):
    if len(documento_original) == 11:
        return documento_original[2:10]
    return documento_original


def _es_dni_valido_para_renaper(documento_consulta):
    return documento_consulta.isdigit() and len(documento_consulta) == 8


def _resolver_ciudad_provincia(ciudadano):
    localidad = getattr(ciudadano, "localidad", None)
    if localidad:
        localidad_nombre = getattr(localidad, "nombre", localidad)
        if localidad_nombre:
            return str(localidad_nombre).title()

    return (getattr(ciudadano, "ciudad", "") or "").title()


def _build_datos_provincia(ciudadano, documento_consulta):
    fecha_nacimiento = getattr(ciudadano, "fecha_nacimiento", None)
    altura = getattr(ciudadano, "altura", None)
    provincia = getattr(ciudadano, "provincia", None)
    codigo_postal = getattr(ciudadano, "codigo_postal", None)
    return {
        "documento": documento_consulta,
        "nombre": (getattr(ciudadano, "nombre", "") or "").title(),
        "apellido": (getattr(ciudadano, "apellido", "") or "").title(),
        "fecha_nacimiento": (
            fecha_nacimiento.strftime("%d/%m/%Y") if fecha_nacimiento else None
        ),
        "sexo": getattr(getattr(ciudadano, "sexo", None), "sexo", None),
        "calle": (getattr(ciudadano, "calle", "") or "").title(),
        "altura": str(altura) if altura else "",
        "piso_departamento": (
            getattr(ciudadano, "piso_departamento", "") or ""
        ).title(),
        "ciudad": _resolver_ciudad_provincia(ciudadano),
        "provincia": getattr(provincia, "nombre", None),
        "codigo_postal": str(codigo_postal) if codigo_postal else "",
    }


def _resolver_sexo_y_consulta_renaper(documento_consulta, sexo_renaper):
    if sexo_renaper:
        return sexo_renaper, None

    for sexo_test in ["M", "F"]:
        resultado_test = _consultar_datos_renaper_con_reintentos(
            documento_consulta, sexo_test
        )
        if resultado_test.get("success"):
            return sexo_test, resultado_test

    return None, None


def _get_renaper_retry_config():
    max_retries = getattr(settings, "RENAPER_VALIDACION_MAX_RETRIES", 1)
    backoff_seconds = getattr(settings, "RENAPER_VALIDACION_BACKOFF_SECONDS", 0.0)

    try:
        max_retries = max(int(max_retries or 1), 1)
    except (TypeError, ValueError):
        max_retries = 1

    try:
        backoff_seconds = max(float(backoff_seconds or 0), 0.0)
    except (TypeError, ValueError):
        backoff_seconds = 0.0

    return max_retries, backoff_seconds


def _es_error_reintentable(error_type):
    return error_type in RENAPER_TRANSIENT_ERROR_TYPES


def _enriquecer_resultado_renaper(resultado, retry_attempt, max_retries):
    resultado_normalizado = dict(resultado or {})
    if not resultado_normalizado.get("success", False):
        resultado_normalizado.setdefault(
            "error", "Error desconocido al consultar Renaper"
        )
        resultado_normalizado.setdefault("error_type", "unexpected_error")

    resultado_normalizado["retry_attempt"] = retry_attempt
    resultado_normalizado["max_retries"] = max_retries
    return resultado_normalizado


def _build_error_log_data(log_data, resultado_renaper, stage="response"):
    return {
        **log_data,
        "stage": stage,
        "error": resultado_renaper.get("error"),
        "error_type": resultado_renaper.get("error_type"),
        "retry_attempt": resultado_renaper.get("retry_attempt"),
        "max_retries": resultado_renaper.get("max_retries"),
    }


def _get_error_message(resultado_renaper):
    error_type = resultado_renaper.get("error_type")

    if error_type == "fallecido" or resultado_renaper.get("fallecido"):
        return "La persona figura como fallecida en Renaper"
    if error_type == "invalid_response":
        return RENAPER_INVALID_RESPONSE_MESSAGE
    if error_type == "no_match":
        return RENAPER_NO_MATCH_MESSAGE
    return RENAPER_REMOTE_UNAVAILABLE_MESSAGE


def _consultar_datos_renaper_con_reintentos(documento_consulta, sexo_renaper):
    max_retries, backoff_seconds = _get_renaper_retry_config()
    ultimo_resultado = None

    for intento in range(1, max_retries + 1):
        ultimo_resultado = _enriquecer_resultado_renaper(
            consultar_datos_renaper(documento_consulta, sexo_renaper),
            retry_attempt=intento,
            max_retries=max_retries,
        )
        if ultimo_resultado.get("success"):
            return ultimo_resultado

        if intento >= max_retries or not _es_error_reintentable(
            ultimo_resultado.get("error_type")
        ):
            break

        logger.warning(
            "renaper.validation.retrying_remote_query",
            extra={
                "data": {
                    "retry_attempt": intento + 1,
                    "max_retries": max_retries,
                    "error": ultimo_resultado.get("error"),
                    "error_type": ultimo_resultado.get("error_type"),
                }
            },
        )

        if backoff_seconds > 0:
            time.sleep(backoff_seconds * (2 ** (intento - 1)))

    return ultimo_resultado or _enriquecer_resultado_renaper(
        {
            "success": False,
            "error": "Error desconocido al consultar Renaper",
            "error_type": "unexpected_error",
        },
        retry_attempt=max_retries,
        max_retries=max_retries,
    )


def _formatear_fecha_renaper(fecha_renaper):
    if not fecha_renaper:
        return fecha_renaper

    try:
        if "-" in fecha_renaper and len(fecha_renaper) == 10:
            fecha_obj = datetime.strptime(fecha_renaper, "%Y-%m-%d")
            return fecha_obj.strftime("%d/%m/%Y")
    except Exception:  # pylint: disable=broad-exception-caught
        return fecha_renaper

    return fecha_renaper


def _parsear_fecha_ejemplar(fecha):
    """Interpreta la fecha del ejemplar. None si el formato no se reconoce."""
    if not fecha:
        return None

    for formato in EJEMPLAR_FORMATOS_FECHA:
        try:
            return datetime.strptime(fecha, formato).date()
        except ValueError:
            continue

    return None


def _ejemplar_esta_vencido(vencimiento, hoy=None):
    """True/False si la fecha se pudo interpretar; None si no.

    El None es deliberado y distinto de False: ante un formato desconocido no
    hay que afirmar que el documento está vigente. La UI sólo destaca el caso
    True, así que una fecha ilegible se muestra sin adjetivar.
    """
    fecha = _parsear_fecha_ejemplar(vencimiento)
    if fecha is None:
        return None

    return fecha < (hoy or timezone.localdate())


def _valor_ejemplar(datos_api, clave):
    valor = datos_api.get(clave)
    if valor is None:
        return None
    texto = str(valor).strip()
    if texto.lower() in EJEMPLAR_PLACEHOLDERS:
        return None
    return texto


def _extraer_datos_ejemplar_dni(resultado_renaper):
    """Extrae emisión, vencimiento y ejemplar del payload crudo de RENAPER.

    Devuelve None si el servicio no informó ninguno de los tres: el bloque es
    informativo y no debe ocupar lugar en la UI cuando no hay nada que mostrar.
    """
    datos_api = resultado_renaper.get("datos_api")
    if not isinstance(datos_api, dict):
        return None

    emision = _valor_ejemplar(datos_api, "emision")
    vencimiento = _valor_ejemplar(datos_api, "vencimiento")
    ejemplar = _valor_ejemplar(datos_api, "ejemplar")

    if not any((emision, vencimiento, ejemplar)):
        return None

    return {
        "emision": _formatear_fecha_renaper(emision),
        "vencimiento": _formatear_fecha_renaper(vencimiento),
        "ejemplar": ejemplar.upper() if ejemplar else None,
        "vencido": _ejemplar_esta_vencido(vencimiento),
    }


def _log_datos_ejemplar(datos_ejemplar):
    """Claves para medir cobertura en producción, sin registrar los valores."""
    datos = datos_ejemplar or {}

    return {
        "ejemplar_disponible": bool(datos_ejemplar),
        "campos_ejemplar": sorted(
            clave for clave in EJEMPLAR_CAMPOS_DATO if datos.get(clave)
        ),
        "ejemplar_vencido": datos.get("vencido"),
    }


def _resolver_provincia_renaper(datos_renaper):
    provincia_valor = datos_renaper.get("provincia")
    if provincia_valor not in (None, ""):
        try:
            from core.models import Provincia

            provincia_obj = Provincia.objects.get(pk=provincia_valor)
            return provincia_obj.nombre
        except (Provincia.DoesNotExist, ValueError, TypeError):
            return "Provincia no encontrada"

    provincia_api = (datos_renaper.get("provincia_api") or "").strip()
    return provincia_api.title() if provincia_api else None


def _formatear_datos_renaper(datos_renaper, sexo_renaper, documento_consulta=None):
    documento_renaper = (
        datos_renaper.get("dni") or datos_renaper.get("documento") or documento_consulta
    )

    datos_renaper_formateados = {
        "documento": str(documento_renaper or ""),
        "nombre": (datos_renaper.get("nombre") or "").title(),
        "apellido": (datos_renaper.get("apellido") or "").title(),
        "fecha_nacimiento": _formatear_fecha_renaper(
            datos_renaper.get("fecha_nacimiento")
        ),
        "sexo": "Masculino" if sexo_renaper == "M" else "Femenino",
        "calle": (datos_renaper.get("calle") or "").title(),
        "altura": str(datos_renaper.get("altura") or ""),
        "piso_departamento": (
            datos_renaper.get("piso_departamento")
            or datos_renaper.get("piso_vivienda")
            or ""
        ).title(),
        "ciudad": (
            datos_renaper.get("ciudad") or datos_renaper.get("localidad_api") or ""
        ).title(),
        "provincia": _resolver_provincia_renaper(datos_renaper),
        "codigo_postal": str(datos_renaper.get("codigo_postal") or ""),
    }

    return datos_renaper_formateados


def _log_respuesta_renaper(log_data, resultado_renaper):
    success = resultado_renaper.get("success", False)
    fallecido = resultado_renaper.get("fallecido")
    response_summary = {
        "success": success,
        "keys": sorted(list(resultado_renaper.keys())),
        "fallecido": fallecido,
    }

    if not success:
        error_type = resultado_renaper.get("error_type")
        log_extra = {"data": _build_error_log_data(log_data, resultado_renaper)}

        if error_type == "no_match":
            logger.info("renaper.validation.no_match", extra=log_extra)
        elif error_type in {"timeout", "remote_error"}:
            logger.warning("renaper.validation.remote_unavailable", extra=log_extra)
        elif error_type == "auth_error":
            logger.error("renaper.validation.remote_unavailable", extra=log_extra)
        elif error_type == "invalid_response":
            logger.error("renaper.validation.invalid_response", extra=log_extra)
        elif error_type == "fallecido":
            logger.info("renaper.validation.fallecido", extra=log_extra)
        else:
            logger.error("renaper.validation.response_error", extra=log_extra)
        return

    response_summary["data_keys"] = sorted(
        list(resultado_renaper.get("data", {}).keys())
    )
    logger.info(
        "renaper.validation.response_ok",
        extra={
            "data": {
                **log_data,
                "stage": "response",
                "response": response_summary,
            }
        },
    )


# --- Operaciones -----------------------------------------------------------

ESTADOS_VALIDACION = {"1": "Aceptado", "2": "Rechazado", "3": "Subsanar"}


def puede_validar(usuario) -> bool:
    """Solo tecnica, coordinacion o admin validan contra RENAPER."""

    if not getattr(usuario, "is_authenticated", False):
        return False
    return (
        is_admin(usuario)
        or user_has_permission(usuario, ROLE_COORDINADOR_CELIAQUIA_PERMISSION)
        or user_has_permission(usuario, ROLE_TECNICO_CELIAQUIA_PERMISSION)
    )


def guardar_estado(legajo, estado: str, usuario, comentario: str = "") -> str:
    """Guarda el resultado de la validacion: 1 acepta, 2 rechaza, 3 subsana.

    Movido desde `ValidacionRenaperView._guardar_validacion_estado`. Las tres
    ramas no son simetricas y por eso no se simplifican:

    - **3 con comentario** deja el legajo en SUBSANAR y marca el tipo RENAPER,
      para que el detalle muestre el motivo y no el texto generico.
    - **2** degrada `revision_tecnico` a RECHAZADO y libera el cupo, porque un
      rechazado no debe retener titularidad ni contar en padron ni en pago.
    - **1** solo guarda el estado.

    Devuelve la etiqueta legible del estado.
    """

    if estado not in ESTADOS_VALIDACION:
        raise ValidationError("Estado de validación inválido")

    legajo.estado_validacion_renaper = int(estado)

    if estado == "3" and comentario:
        legajo.subsanacion_motivo = comentario
        legajo.subsanacion_tipo = "RENAPER"
        legajo.revision_tecnico = "SUBSANAR"
        legajo.save(
            update_fields=[
                "estado_validacion_renaper",
                "subsanacion_motivo",
                "subsanacion_tipo",
                "revision_tecnico",
                "modificado_en",
            ]
        )
    elif estado == "2":
        LegajoService.rechazar_por_renaper(legajo, usuario)
    else:
        legajo.save(update_fields=["estado_validacion_renaper", "modificado_en"])

    etiqueta = ESTADOS_VALIDACION[estado]
    logger.info(
        "renaper.validation.status_saved",
        extra={
            "data": {
                "legajo_id": legajo.pk,
                "expediente_id": legajo.expediente_id,
                "estado_guardado": etiqueta,
                "requiere_subsanacion": estado == "3",
                "user_id": getattr(usuario, "id", None),
            }
        },
    )
    return etiqueta


def consultar(legajo, usuario) -> tuple[dict, int]:
    """Consulta RENAPER y arma la comparacion contra los datos de la provincia.

    Movida verbatim desde `ValidacionRenaperView._consultar_renaper`. Devuelve
    `(payload, status)` con el **mismo status que usaba la vista**, para no
    cambiarle el contrato al front Django: los errores de negocio salian con
    HTTP 200 y `success: False`. La API los traduce a 400, que es lo que
    corresponde en REST, sin tocar la pantalla.

    No guarda nada: el resultado se guarda recien cuando el usuario elige
    "datos correctos" o "datos incorrectos" (ver `guardar_estado`).
    """
    try:
        user = usuario
        legajo_id, pk = legajo.pk, legajo.expediente_id

        # Si es técnico, verificar que esté asignado al expediente
        if (
            _has_permission(user, ROLE_TECNICO_CELIAQUIA_PERMISSION)
            and not user.is_superuser
        ):
            asignaciones = legajo.expediente.asignaciones_tecnicos.filter(tecnico=user)
            if not asignaciones.exists():
                logger.warning(
                    "renaper.validation.unauthorized",
                    extra={
                        "data": {
                            "legajo_id": legajo_id,
                            "expediente_id": pk,
                            "user_id": getattr(user, "id", None),
                        }
                    },
                )
                return (
                    {
                        "success": False,
                        "error": "No sos el técnico asignado a este expediente.",
                    }
                ), 403
        ciudadano = legajo.ciudadano

        if not ciudadano:
            logger.warning(
                "renaper.validation.missing_ciudadano",
                extra={
                    "data": {
                        "legajo_id": legajo_id,
                        "expediente_id": pk,
                        "user_id": getattr(user, "id", None),
                    }
                },
            )
            return (
                {
                    "success": False,
                    "error": "El ciudadano asociado al legajo no existe.",
                }
            ), 200
        # Validaciones básicas
        if not ciudadano.documento:
            logger.warning(
                "renaper.validation.missing_documento",
                extra={"data": _build_log_data(user, legajo, ciudadano)},
            )
            return (
                {
                    "success": False,
                    "error": "El ciudadano no tiene documento cargado",
                }
            ), 200
        sexo_renaper = _mapear_sexo_para_renaper(ciudadano)

        if not sexo_renaper:
            logger.warning(
                "renaper.validation.missing_sexo",
                extra={"data": _build_log_data(user, legajo, ciudadano)},
            )

        documento_original = str(ciudadano.documento)
        documento_consulta = _normalizar_documento_para_renaper(documento_original)

        if not _es_dni_valido_para_renaper(documento_consulta):
            logger.warning(
                "renaper.validation.invalid_documento",
                extra={
                    "data": _build_log_data(
                        user,
                        legajo,
                        ciudadano,
                    )
                },
            )
            return (
                {
                    "success": False,
                    "error": "No se pudo extraer un DNI válido del documento.",
                }
            ), 200
        datos_provincia = _build_datos_provincia(ciudadano, documento_consulta)

        # Si no se pudo determinar sexo, intentar con ambos
        if not sexo_renaper:
            logger.info(
                "renaper.validation.trying_both_sexes",
                extra={
                    "data": _build_log_data(
                        user,
                        legajo,
                        ciudadano,
                    )
                },
            )
            sexo_renaper, resultado_renaper = _resolver_sexo_y_consulta_renaper(
                documento_consulta, sexo_renaper
            )

            if not sexo_renaper:
                return (
                    {
                        "success": False,
                        "error": "No se pudo determinar el sexo del ciudadano. Configure el sexo manualmente.",
                    }
                ), 200
        else:
            resultado_renaper = None

        log_data = _build_log_data(
            user,
            legajo,
            ciudadano,
        )

        logger.info(
            "renaper.validation.request",
            extra={
                "data": {
                    **log_data,
                    "stage": "request",
                }
            },
        )

        if resultado_renaper is None:
            resultado_renaper = _consultar_datos_renaper_con_reintentos(
                documento_consulta, sexo_renaper
            )

        _log_respuesta_renaper(log_data, resultado_renaper)
        success = resultado_renaper.get("success", False)
        fallecido = resultado_renaper.get("fallecido")

        if fallecido:
            return (
                {
                    "success": False,
                    "error": _get_error_message(resultado_renaper),
                }
            ), 200
        if not success:
            return (
                {
                    "success": False,
                    "error": _get_error_message(resultado_renaper),
                }
            ), 200
        datos_renaper = resultado_renaper["data"]

        datos_renaper_formateados = _formatear_datos_renaper(
            datos_renaper, sexo_renaper, documento_consulta
        )
        datos_ejemplar = _extraer_datos_ejemplar_dni(resultado_renaper)

        # La validación se guardará cuando el usuario elija "Datos correctos" o "Datos incorrectos"

        logger.info(
            "renaper.validation.result_ready",
            extra={
                "data": {
                    **log_data,
                    "stage": "result",
                    "campos_provincia": list(datos_provincia.keys()),
                    "campos_renaper": list(datos_renaper_formateados.keys()),
                    **_log_datos_ejemplar(datos_ejemplar),
                }
            },
        )

        return (
            {
                "success": True,
                "datos_provincia": datos_provincia,
                "datos_renaper": datos_renaper_formateados,
                "datos_ejemplar": datos_ejemplar,
                "ciudadano_nombre": f"{ciudadano.nombre} {ciudadano.apellido}",
                "documento": documento_consulta,
            }
        ), 200
    except Exception:  # pylint: disable=broad-exception-caught
        logger.error(
            "renaper.validation.unhandled_error",
            extra={
                "data": {
                    "legajo_id": legajo_id,
                    "expediente_id": pk,
                    "user_id": getattr(usuario, "id", None),
                }
            },
        )
        return (
            {
                "success": False,
                "error": "Ha ocurrido un error inesperado. Por favor, contacte al administrador.",
            }
        ), 500
