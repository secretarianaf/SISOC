"""Proyección JSON de la ficha Ciudadano 360 para React (C05.01, G1 v1).

No es la API de la PWA: proyecta lo que imprime ``ciudadanos/ciudadano_detail.html``
con el contexto de la vista nativa (``CiudadanosDetailView.build_familia`` y
``get_historial_context``), sin formatear nada en el cliente. Las fechas usan el
filtro ``date`` del template (hora local) y los vacíos el filtro ``default:'-'``.
Los aportes de las verticales no se proyectan acá: los trae ``web_aportes``.
"""

from django.contrib import messages
from django.template.defaultfilters import date as date_filter
from django.urls import reverse
from django.utils.timezone import localtime

from core.templatetags.custom_filters import google_maps_query

VACIO = "-"
MESSAGE_LEVELS = {
    messages.DEBUG: "info",
    messages.INFO: "info",
    messages.SUCCESS: "success",
    messages.WARNING: "warning",
    messages.ERROR: "error",
}
ESTADOS_INTERACCION = ("completo", "en_plan")


def por_defecto(valor):
    """``{{ valor|default:'-' }}`` (el template imprime ``str(valor)``)."""
    return str(valor) if valor else VACIO


def pending_messages(request):
    """Consume los mensajes en cola igual que la página nativa."""
    return [
        {"message": str(m), "level": MESSAGE_LEVELS.get(m.level, "info")}
        for m in messages.get_messages(request)
    ]


def _fecha(valor, formato):
    """``{{ valor|date:formato }}`` ('' sin valor; datetimes en hora local)."""
    if not valor:
        return ""
    if hasattr(valor, "hour"):
        valor = localtime(valor)
    return date_filter(valor, formato)


def _texto_o_none(valor):
    return str(valor) if valor else None


def _identidad(ciudadano):
    """Aviso de identidad (SIN_DNI / DNI no validado / revisión manual)."""
    tipo = ciudadano.tipo_registro_identidad
    mostrar = tipo != "ESTANDAR" or ciudadano.requiere_revision_manual
    motivo, descripcion = "", ""
    if tipo == "SIN_DNI":
        if ciudadano.motivo_sin_dni:
            motivo = ciudadano.get_motivo_sin_dni_display()
        descripcion = ciudadano.motivo_sin_dni_descripcion or ""
    elif tipo == "DNI_NO_VALIDADO_RENAPER":
        if ciudadano.motivo_no_validacion_renaper:
            motivo = ciudadano.get_motivo_no_validacion_renaper_display()
        descripcion = ciudadano.motivo_no_validacion_descripcion or ""
    return {
        "mostrar": bool(mostrar),
        "sin_dni": tipo == "SIN_DNI",
        "no_validado": tipo == "DNI_NO_VALIDADO_RENAPER",
        "requiere_revision": bool(ciudadano.requiere_revision_manual),
        "motivo_texto": motivo,
        "descripcion_texto": descripcion,
    }


def _datos(ciudadano):
    calle = f"{ciudadano.calle} {ciudadano.altura}" if ciudadano.calle else VACIO
    return {
        "cuil_cuit": por_defecto(ciudadano.cuil_cuit),
        "apellido": str(ciudadano.apellido),
        "nombre": str(ciudadano.nombre),
        "tipo_documento": ciudadano.get_tipo_documento_display(),
        "numero_documento": por_defecto(ciudadano.numero_documento),
        "pais_emisor": _texto_o_none(ciudadano.pais_emisor),
        "provincia": por_defecto(ciudadano.provincia),
        "municipio": por_defecto(ciudadano.municipio),
        "localidad": por_defecto(ciudadano.localidad),
        "calle_altura": calle,
        "codigo_postal": por_defecto(ciudadano.codigo_postal),
        "fecha_nacimiento": _fecha(ciudadano.fecha_nacimiento, "d/m/Y") or VACIO,
        "edad": por_defecto(ciudadano.edad),
        "genero": por_defecto(ciudadano.sexo),
        "estado_civil": por_defecto(ciudadano.get_estado_civil_display()),
        "nacionalidad": por_defecto(ciudadano.nacionalidad),
        "telefono": por_defecto(ciudadano.telefono),
        "telefono_alternativo": por_defecto(ciudadano.telefono_alternativo),
        "email": por_defecto(ciudadano.email),
        "fecha_actualizacion": _fecha(ciudadano.modificado, "d/m/Y H:i"),
        "origen_dato": ciudadano.get_origen_dato_display(),
    }


def _familia(vista, ciudadano):
    return [
        {
            "vinculo_texto": relacion.get_vinculo_display(),
            "nombre": familiar.nombre,
            "apellido": familiar.apellido,
            "edad_texto": por_defecto(familiar.edad),
            "url": reverse("ciudadanos_ver", args=[familiar.pk]),
        }
        for relacion, familiar in vista.build_familia(ciudadano)
    ]


def _interacciones(ciudadano):
    return [
        {
            "tipo": str(i.tipo),
            "fecha_texto": _fecha(i.fecha, "d M Y"),
            "responsable_texto": (
                i.responsable.get_full_name() if i.responsable else ""
            )
            or "Sin asignar",
            "estado": i.estado if i.estado in ESTADOS_INTERACCION else "pendiente",
        }
        for i in ciudadano.interacciones.select_related("responsable")[:10]
    ]


def proyectar_ficha(request, ciudadano, vista):
    """Todo lo de la ficha que no es un aporte de vertical."""
    historial = vista.get_historial_context(ciudadano)
    perfil = ciudadano.foto.url if ciudadano.foto else None
    return {
        "identidad": _identidad(ciudadano),
        "acciones": {
            "historial_url": (
                reverse(
                    "audittrail:log_instance",
                    args=["ciudadanos", "ciudadano", ciudadano.pk],
                )
                if request.user.has_perm("auditlog.view_logentry")
                else None
            ),
            "editar_url": reverse("ciudadanos_editar", args=[ciudadano.pk]),
            "eliminar_url": reverse("ciudadanos_eliminar", args=[ciudadano.pk]),
            "familiar_nuevo_url": reverse("grupofamiliar_crear", args=[ciudadano.pk]),
            # El botón nativo exige requiere_revision_manual y ``revision_identidad``.
            "marcar_revisado_url": (
                reverse("ciudadanos_web_marcar_revisado", args=[ciudadano.pk])
                if ciudadano.requiere_revision_manual
                and request.user.has_perm("ciudadanos.revision_identidad")
                else None
            ),
        },
        "datos": _datos(ciudadano),
        "mapa": google_maps_query(ciudadano.latitud, ciudadano.longitud) or None,
        "foto_url": perfil,
        "familia": _familia(vista, ciudadano),
        "historial": {
            "labels": historial["historial_labels"],
            "auh": historial["historial_auh"],
            "prestacion": historial["historial_prestacion"],
            "centro_familia": historial["historial_centro_familia"],
            "comedor": historial["historial_comedor"],
        },
        "interacciones": _interacciones(ciudadano),
        "observaciones": ciudadano.observaciones or "",
        "messages": pending_messages(request),
    }
