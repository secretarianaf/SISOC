"""Registros erroneos de la importacion masiva de Celiaquia.

Estas reglas vivian dentro de `celiaquia/views/expediente.py`. Se extraen aca
para que la API REST y las pantallas apliquen **exactamente** el mismo
comportamiento: validar el mismo payload, resolver la misma provincia y crear
los legajos por el mismo camino. Duplicar esto es la forma mas facil de que la
API acepte un registro que la pantalla rechaza, o al reves.

Las funciones se movieron sin cambios. La vista las sigue exponiendo con sus
nombres viejos (`_normalizar_datos_registro_erroneo`, etc.) para no romper a
quien las importe, incluidos los tests de `tests/test_celiaquia_expediente_view_helpers_unit.py`.

Los permisos genericos (`is_admin`, `is_provincial`, ...) salen de
`celiaquia/scope.py`, que ya los centraliza para la API y las vistas.
"""

from __future__ import annotations

import json
import logging
import re

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import transaction
from django.utils import timezone

from core.models import Localidad, Nacionalidad, Provincia
from users.territorial_scope import (
    get_effective_scopes,
    get_single_full_province_scope_id,
)

from celiaquia.models import EstadoLegajo, ExpedienteCiudadano, RegistroErroneo
from celiaquia.scope import (
    ROLE_COORDINADOR_CELIAQUIA_PERMISSION,
    is_admin,
    is_provincial,
    user_has_permission,
)
from celiaquia.services.ciudadano_service import CiudadanoService
from celiaquia.services.importacion_service import (
    IMPORTACION_EDITABLE_FIELDS,
    IMPORTACION_RESPONSABLE_FIELDS,
    _beneficiario_requiere_responsable_importacion,
    _beneficiario_tiene_conflicto_importacion,
    _cargar_nacionalidades_cache,
    _cargar_paises_a_nacionalidad_importacion,
    _obtener_provincias_permitidas_ids,
    _precargar_conflictos_y_existentes_importacion,
    _resolver_nacionalidad_payload_importacion,
    validar_y_normalizar_payloads_importacion,
)

logger = logging.getLogger(__name__)

# Alias de los helpers de permisos, para que el codigo movido no cambie.
_is_admin = is_admin
_is_provincial = is_provincial
_user_has_permission = user_has_permission


# --- Helpers movidos desde la vista (sin cambios) --------------------------


def _can_manage_registros_erroneos(user) -> bool:
    return bool(
        _is_admin(user)
        or _is_provincial(user)
        or _user_has_permission(user, ROLE_COORDINADOR_CELIAQUIA_PERMISSION)
    )


def _resolver_localidad_registro_erroneo(localidad_value):
    if localidad_value in (None, ""):
        return None

    localidad_str = str(localidad_value).strip()
    if not localidad_str:
        return None

    localidades = Localidad.objects.select_related("municipio")
    if localidad_str.isdigit():
        return localidades.filter(pk=int(localidad_str)).first()
    return localidades.filter(nombre__iexact=localidad_str).first()


def _resolver_municipio_id_desde_localidad(localidad_value):
    localidad = _resolver_localidad_registro_erroneo(localidad_value)
    if not localidad or not localidad.municipio_id:
        return ""
    return str(localidad.municipio_id)


def _resolver_nacionalidad_registro_erroneo(nacionalidad_value):
    if nacionalidad_value in (None, ""):
        return None

    payload = {"nacionalidad": nacionalidad_value}
    try:
        _resolver_nacionalidad_payload_importacion(
            payload,
            nacionalidades_cache=_cargar_nacionalidades_cache(),
            paises_a_nacionalidad=_cargar_paises_a_nacionalidad_importacion(),
        )
    except ValidationError:
        return None

    nacionalidad_id = payload.get("nacionalidad")
    if not nacionalidad_id:
        return None
    return Nacionalidad.objects.filter(pk=nacionalidad_id).first()


def _resolver_nacionalidad_id_registro_erroneo(nacionalidad_value):
    nacionalidad = _resolver_nacionalidad_registro_erroneo(nacionalidad_value)
    if not nacionalidad:
        return ""
    return str(nacionalidad.pk)


def _normalizar_mensaje_error_invalid_fields(message):
    if isinstance(message, ValidationError):
        mensajes = getattr(message, "messages", None) or [str(message)]
        msg = " ".join(str(item) for item in mensajes if item)
    else:
        msg = str(message or "")

    msg = msg.strip()
    if msg.startswith("[") and msg.endswith("]"):
        msg = msg[1:-1].strip()
    msg = msg.strip("'\" ")

    prefijo_reproceso = "error al reprocesar:"
    if msg.lower().startswith(prefijo_reproceso):
        msg = msg[len(prefijo_reproceso) :].strip()

    return msg


def _campos_invalidos_desde_mensaje_error(message):
    if not message:
        return []

    msg = _normalizar_mensaje_error_invalid_fields(message)
    msg_lower = msg.lower()
    campos = []

    faltantes_match = re.search(
        r"faltan campos obligatorios:\s*(?P<faltantes>.+)$",
        msg,
        flags=re.IGNORECASE,
    )
    if faltantes_match:
        faltantes = faltantes_match.group("faltantes")
        return [
            campo.strip()
            for campo in faltantes.split(",")
            if campo and campo.strip() in IMPORTACION_EDITABLE_FIELDS
        ]

    patrones = [
        (
            r"\bfecha_nacimiento_responsable\b|fecha de nacimiento responsable",
            "fecha_nacimiento_responsable",
        ),
        (r"\bdocumento_responsable\b|documento responsable", "documento_responsable"),
        (r"\bapellido_responsable\b|apellido responsable", "apellido_responsable"),
        (r"\bnombre_responsable\b|nombre responsable", "nombre_responsable"),
        (r"\bsexo_responsable\b|sexo responsable", "sexo_responsable"),
        (r"\bdomicilio_responsable\b|domicilio responsable", "domicilio_responsable"),
        (r"\blocalidad_responsable\b|localidad responsable", "localidad_responsable"),
        (
            r"\btelefono_responsable\b|telefono responsable",
            "telefono_responsable",
        ),
        (r"\bemail_responsable\b|email responsable", "email_responsable"),
        (r"\bcontacto_responsable\b|contacto responsable", "contacto_responsable"),
        (r"\bfecha_nacimiento\b|fecha de nacimiento", "fecha_nacimiento"),
        (r"\bdocumento\b", "documento"),
        (r"\bsexo\b", "sexo"),
        (r"\bnacionalidad\b", "nacionalidad"),
        (r"\bmunicipio\b", "municipio"),
        (r"\blocalidad\b", "localidad"),
        (r"\bcodigo_postal\b|codigo postal", "codigo_postal"),
        (r"\bcalle\b", "calle"),
        (r"\baltura\b", "altura"),
        (r"\btelefono\b", "telefono"),
        (r"\bemail\b", "email"),
    ]
    for patron, campo in patrones:
        if re.search(patron, msg_lower) and campo in IMPORTACION_EDITABLE_FIELDS:
            campos.append(campo)

    if "debe tener un responsable" in msg_lower:
        campos.extend(
            [
                "apellido_responsable",
                "nombre_responsable",
                "documento_responsable",
                "fecha_nacimiento_responsable",
                "sexo_responsable",
                "domicilio_responsable",
                "localidad_responsable",
            ]
        )

    return list(dict.fromkeys(campos))


def _aplicar_defaults_registro_erroneo(datos):
    datos_con_defaults = dict(datos)

    municipio_id = _resolver_municipio_id_desde_localidad(
        datos_con_defaults.get("localidad")
    )
    if municipio_id:
        datos_con_defaults["municipio"] = municipio_id

    return datos_con_defaults


def _normalizar_datos_registro_erroneo(payload):
    datos_normalizados = {}
    for field in IMPORTACION_EDITABLE_FIELDS:
        if field not in payload:
            continue
        value = payload.get(field)
        if isinstance(value, str):
            value = value.strip()
        datos_normalizados[field] = value
    return datos_normalizados


def _limpiar_datos_registro_erroneo(payload):
    return {k: v for k, v in payload.items() if v not in (None, "")}


def _consolidar_datos_registro_erroneo(datos_previos, datos_nuevos):
    datos_consolidados = _normalizar_datos_registro_erroneo(datos_previos or {})
    for field in IMPORTACION_EDITABLE_FIELDS:
        if field not in datos_nuevos:
            continue
        value = datos_nuevos.get(field)
        if value in (None, ""):
            datos_consolidados.pop(field, None)
            continue
        datos_consolidados[field] = value

    responsable_tocado = any(
        field in datos_nuevos for field in IMPORTACION_RESPONSABLE_FIELDS
    )
    responsable_vacio = not any(
        datos_consolidados.get(field) not in (None, "")
        for field in IMPORTACION_RESPONSABLE_FIELDS
    )
    if responsable_tocado and responsable_vacio:
        for field in IMPORTACION_RESPONSABLE_FIELDS:
            datos_consolidados.pop(field, None)

    return _aplicar_defaults_registro_erroneo(datos_consolidados)


def _user_provincia(user):
    try:
        provincia = user.profile.provincia
    except (AttributeError, ObjectDoesNotExist):
        provincia = None
    if provincia:
        return provincia

    try:
        provincia_id = get_single_full_province_scope_id(user)
    except ObjectDoesNotExist:
        provincia_id = None
    if not provincia_id:
        return None
    return Provincia.objects.filter(pk=provincia_id).first()


def _resolver_provincia_id_registro_erroneo(user, expediente):
    provincia = _user_provincia(user) or getattr(expediente, "provincia", None)
    if provincia is None and _is_provincial(user):
        provincia_ids = {scope.provincia_id for scope in get_effective_scopes(user)}
        if len(provincia_ids) == 1:
            return next(iter(provincia_ids))
    if provincia is None:
        try:
            provincia = expediente.usuario_provincia.profile.provincia
        except Exception:
            provincia = None
    for attr in ("pk", "id"):
        provincia_id = getattr(provincia, attr, None)
        if provincia_id is not None:
            return provincia_id
    return provincia


def _validar_datos_registro_erroneo(
    payload, provincia_id, fila_excel=0, provincias_permitidas_ids=None
):
    return validar_y_normalizar_payloads_importacion(
        payload=payload,
        provincia_usuario_id=provincia_id,
        provincias_permitidas_ids=provincias_permitidas_ids,
        offset=fila_excel,
    )


def _registro_erroneo_responsable_requerido(payload):
    fecha_nacimiento = payload.get("fecha_nacimiento")
    if fecha_nacimiento in (None, ""):
        return False
    try:
        payload_normalizado = dict(payload)
        payload_normalizado["fecha_nacimiento"] = CiudadanoService._to_date(
            fecha_nacimiento
        )
    except ValidationError:
        return False
    return _beneficiario_requiere_responsable_importacion(payload_normalizado)


# --- Alerta persistente de la importacion (movida sin cambios) -------------


def _deduplicar_excluidos_alerta(excluidos):
    vistos = set()
    resultado = []
    for item in excluidos or []:
        if isinstance(item, dict):
            key = (
                item.get("ciudadano_id"),
                item.get("documento"),
                item.get("expediente_origen_id"),
                item.get("estado_programa"),
                item.get("estado_legajo_origen"),
                item.get("motivo"),
            )
        else:
            key = ("raw", str(item))
        if key in vistos:
            continue
        vistos.add(key)
        resultado.append(item)
    return resultado


def _build_excluidos_importacion_alerta(excluidos):
    excluidos_lineas = []
    if excluidos:
        cantidad = len(excluidos)
        sujeto = (
            "No se creó 1 legajo"
            if cantidad == 1
            else f"No se crearon {cantidad} legajos"
        )
        predicado = (
            "porque pertenece a otro expediente."
            if cantidad == 1
            else "porque pertenecen a otro expediente."
        )
        excluidos_lineas.append(f"{sujeto} {predicado}")
        for item in excluidos[:10]:
            if not isinstance(item, dict):
                excluidos_lineas.append(str(item))
                continue
            documento = item.get("documento", "-")
            apellido = item.get("apellido", "-")
            nombre = item.get("nombre", "-")
            estado = (
                item.get("estado_programa")
                or item.get("estado_legajo_origen")
                or item.get("motivo")
                or "-"
            )
            expediente_origen = item.get("expediente_origen_id", "-")
            excluidos_lineas.append(
                f"- Documento {documento} - {apellido}, {nombre} - Estado legajo: {estado} - Exp #{expediente_origen}"
            )
        restantes = len(excluidos) - 10
        if restantes > 0:
            excluidos_lineas.append(f"... y {restantes} mas.")
    return "\n".join(excluidos_lineas)


def _actualizar_alerta_importacion_persistente(
    expediente, *, creados_incremento=0, errores_actuales=None, excluidos_nuevos=None
):
    historial_qs = (
        expediente.historial.filter(estado_nuevo=expediente.estado)
        .exclude(observaciones__isnull=True)
        .exclude(observaciones="")
        .order_by("-fecha")
    )
    historial_actual = historial_qs.first()
    if not historial_actual:
        return

    try:
        payload = json.loads(historial_actual.observaciones)
    except (TypeError, ValueError):
        return

    if not isinstance(payload, dict):
        return

    creados_total = int(payload.get("creados_total") or 0) + int(
        creados_incremento or 0
    )
    errores_vigentes = (
        int(errores_actuales)
        if errores_actuales is not None
        else int(payload.get("errores_actuales") or 0)
    )

    payload["resumen"] = _build_resumen_importacion_alerta(
        creados_total=creados_total,
        errores_actuales=errores_vigentes,
    )
    excluidos_detalle = _deduplicar_excluidos_alerta(
        (payload.get("excluidos_detalle") or []) + (excluidos_nuevos or [])
    )
    payload["excluidos_detalle"] = excluidos_detalle
    payload["excluidos"] = _build_excluidos_importacion_alerta(excluidos_detalle)
    payload["tiene_errores"] = bool(errores_vigentes)
    payload["creados_total"] = creados_total
    payload["errores_actuales"] = errores_vigentes

    historial_actual.observaciones = json.dumps(payload)
    historial_actual.save(update_fields=["observaciones"])
    return payload


def _build_resumen_importacion_alerta(*, creados_total=0, errores_actuales=0):
    resumen_lineas = [
        f"Importacion procesada. Se crearon {creados_total} legajos y el expediente paso a EN ESPERA."
    ]
    if errores_actuales:
        resumen_lineas.append(f"Errores detectados: {errores_actuales}.")
    return "\n".join(resumen_lineas)


# --- Operaciones -----------------------------------------------------------


def provincia_de(usuario, expediente):
    """Provincia con la que se valida este expediente.

    Es la que usa `_cargar_municipios_cache` para decidir que municipios acepta
    la importacion. Se expone para que los desplegables de la pantalla ofrezcan
    exactamente esos y no otros.
    """

    return _resolver_provincia_id_registro_erroneo(usuario, expediente)


def puede_gestionar(usuario) -> bool:
    """Quien puede tocar los registros erroneos de un expediente."""

    return _can_manage_registros_erroneos(usuario)


def alcance_total(usuario) -> bool:
    """Coordinador y admin operan cualquier expediente; el resto, el suyo.

    El usuario provincial se acota afuera, con el queryset de la vista o del
    ViewSet: asi un pk directo de otra provincia da 404 y no confirma que
    exista.
    """

    return is_admin(usuario) or user_has_permission(
        usuario, ROLE_COORDINADOR_CELIAQUIA_PERMISSION
    )


def actualizar(expediente, registro, datos, usuario) -> None:
    """Corrige un registro erroneo. Lanza `ValidationError` si sigue invalido.

    Al fallar deja el motivo en `mensaje_error`, igual que la pantalla: es lo
    que despues se muestra en la grilla.
    """

    datos_nuevos = _normalizar_datos_registro_erroneo(datos)
    datos_normalizados = _consolidar_datos_registro_erroneo(
        registro.datos_raw, datos_nuevos
    )
    provincia_id = _resolver_provincia_id_registro_erroneo(usuario, expediente)
    try:
        _validar_datos_registro_erroneo(
            datos_normalizados,
            provincia_id=provincia_id,
            fila_excel=registro.fila_excel,
            provincias_permitidas_ids=_obtener_provincias_permitidas_ids(usuario),
        )
    except ValidationError as exc:
        registro.mensaje_error = str(exc)
        registro.save(update_fields=["mensaje_error"])
        raise

    # Al fallar se deja el motivo en `mensaje_error`; al funcionar hay que
    # limpiarlo. Si no, la fila corregida sigue mostrando el error viejo y
    # parece que el guardado no hizo nada.
    registro.datos_raw = _limpiar_datos_registro_erroneo(datos_normalizados)
    registro.mensaje_error = ""
    registro.campo_error = ""
    registro.save(update_fields=["datos_raw", "mensaje_error", "campo_error"])


def campos_invalidos(exc) -> list:
    """Campos que el mensaje de error senala, para pintarlos en el formulario."""

    return _campos_invalidos_desde_mensaje_error(exc)


def eliminar(registro, usuario) -> None:
    """Baja del registro, respetando el soft delete si el modelo lo soporta."""

    from core.soft_delete.view_helpers import is_soft_deletable_instance

    if is_soft_deletable_instance(registro):
        registro.delete(user=usuario, cascade=True)
    else:
        registro.delete()


@transaction.atomic
def reprocesar(expediente, usuario) -> dict:
    """Reintenta crear los legajos de los registros que quedaron con error.

    Movido tal cual desde `ReprocesarRegistrosErroneosView`: misma validacion,
    mismo manejo de conflictos, mismas relaciones de grupo familiar y la misma
    alerta persistente.
    """

    registros = expediente.registros_erroneos.filter(procesado=False)
    if not registros.exists():
        raise ValidationError("No hay registros erróneos para reprocesar.")

    creados = 0
    errores = 0
    errores_detalle = []
    excluidos_detalle = []
    relaciones_crear = []

    estado_inicial = EstadoLegajo.objects.get(nombre="DOCUMENTO_PENDIENTE")
    existentes_ids, en_programa, abiertos = (
        _precargar_conflictos_y_existentes_importacion(expediente)
    )
    provincia_id = _resolver_provincia_id_registro_erroneo(usuario, expediente)
    provincias_permitidas_ids = _obtener_provincias_permitidas_ids(usuario)

    for registro in registros:
        datos = _aplicar_defaults_registro_erroneo(
            _normalizar_datos_registro_erroneo(registro.datos_raw.copy())
        )
        try:
            (
                datos_beneficiario,
                datos_responsable,
                es_mismo_documento,
            ) = _validar_datos_registro_erroneo(
                datos,
                provincia_id=provincia_id,
                fila_excel=registro.fila_excel,
                provincias_permitidas_ids=provincias_permitidas_ids,
            )

            with transaction.atomic():
                ciudadano = CiudadanoService.get_or_create_ciudadano(
                    datos=datos_beneficiario, usuario=usuario, expediente=expediente
                )

                if ciudadano and ciudadano.pk:
                    if _beneficiario_tiene_conflicto_importacion(
                        ciudadano=ciudadano,
                        offset=registro.fila_excel,
                        existentes_ids=existentes_ids,
                        en_programa=en_programa,
                        abiertos=abiertos,
                        excluidos=excluidos_detalle,
                    ):
                        _marcar_procesado(registro)
                        continue

                    rol_beneficiario = (
                        ExpedienteCiudadano.ROLE_BENEFICIARIO_Y_RESPONSABLE
                        if es_mismo_documento
                        else ExpedienteCiudadano.ROLE_BENEFICIARIO
                    )
                    legajo, created = ExpedienteCiudadano.objects.get_or_create(
                        expediente=expediente,
                        ciudadano=ciudadano,
                        defaults={"estado": estado_inicial, "rol": rol_beneficiario},
                    )
                    if not created and legajo.rol != rol_beneficiario:
                        legajo.rol = rol_beneficiario
                        legajo.save(update_fields=["rol"])
                    if created:
                        creados += 1
                        existentes_ids.add(ciudadano.pk)

                    if datos_responsable and not es_mismo_documento:
                        responsable = CiudadanoService.get_or_create_ciudadano(
                            datos=datos_responsable,
                            usuario=usuario,
                            expediente=expediente,
                        )
                        if responsable and responsable.pk:
                            legajo_resp, created_resp = (
                                ExpedienteCiudadano.objects.get_or_create(
                                    expediente=expediente,
                                    ciudadano=responsable,
                                    defaults={
                                        "estado": estado_inicial,
                                        "rol": ExpedienteCiudadano.ROLE_RESPONSABLE,
                                    },
                                )
                            )
                            if (
                                not created_resp
                                and legajo_resp.rol
                                == ExpedienteCiudadano.ROLE_BENEFICIARIO
                            ):
                                legajo_resp.rol = (
                                    ExpedienteCiudadano.ROLE_BENEFICIARIO_Y_RESPONSABLE
                                )
                                legajo_resp.save(update_fields=["rol"])
                            relaciones_crear.append(
                                {
                                    "responsable_id": responsable.pk,
                                    "hijo_id": ciudadano.pk,
                                }
                            )

                    _marcar_procesado(registro)
                else:
                    errores += 1
                    errores_detalle.append(
                        f"Fila {registro.fila_excel}: No se pudo crear el ciudadano"
                    )

        except Exception as e:  # pylint: disable=broad-except
            errores += 1
            error_msg = _mensaje_error_reproceso(e, registro)
            errores_detalle.append(f"Fila {registro.fila_excel}: {error_msg}")
            if not isinstance(e, ValidationError):
                logger.error(
                    "Error reprocesando registro %s: %s - Datos: %s",
                    registro.pk,
                    e,
                    datos,
                    exc_info=True,
                )
            registro.mensaje_error = f"Error al reprocesar: {error_msg}"
            registro.save(update_fields=["mensaje_error"])

    _crear_relaciones_familiares(relaciones_crear)

    registros_restantes = expediente.registros_erroneos.filter(procesado=False).count()
    alerta = _actualizar_alerta_importacion_persistente(
        expediente,
        creados_incremento=creados,
        errores_actuales=registros_restantes,
        excluidos_nuevos=excluidos_detalle,
    )

    return {
        "creados": creados,
        "errores": errores,
        "errores_detalle": errores_detalle,
        "excluidos": len(excluidos_detalle),
        "excluidos_detalle": excluidos_detalle,
        "registros_restantes": registros_restantes,
        "alerta_resumen": (alerta or {}).get("resumen", ""),
    }


def _marcar_procesado(registro) -> None:
    registro.procesado = True
    registro.procesado_en = timezone.now()
    registro.mensaje_error = ""
    registro.save(update_fields=["procesado", "procesado_en", "mensaje_error"])


def _mensaje_error_reproceso(exc, registro) -> str:
    if "Field" in str(exc) and "expected" in str(exc):
        return str(exc)
    if "IntegrityError" in str(type(exc).__name__):
        return "Error de integridad: registro duplicado o datos inconsistentes"
    if "ValidationError" in str(type(exc).__name__):
        return str(exc)
    return registro.mensaje_error or "Error interno al procesar registro"


def _crear_relaciones_familiares(relaciones_crear) -> None:
    if not relaciones_crear:
        return
    try:
        from ciudadanos.models import GrupoFamiliar

        relaciones_creadas = 0
        for rel in relaciones_crear:
            _, created = GrupoFamiliar.objects.get_or_create(
                ciudadano_1_id=rel["responsable_id"],
                ciudadano_2_id=rel["hijo_id"],
                defaults={
                    "vinculo": GrupoFamiliar.RELACION_PADRE,
                    "estado_relacion": GrupoFamiliar.ESTADO_BUENO,
                    "conviven": True,
                    "cuidador_principal": True,
                },
            )
            if created:
                relaciones_creadas += 1
        logger.info(
            "Creadas %s relaciones familiares al reprocesar", relaciones_creadas
        )
    except Exception as e:  # pylint: disable=broad-except
        logger.error(
            "Error creando relaciones familiares al reprocesar: %s", e, exc_info=True
        )
