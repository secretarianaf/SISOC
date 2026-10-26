"""Lecturas y alcance del frontend INET, dentro del dominio VAT."""

from django.utils import timezone
from django.db.models import Count, Q

from VAT import models
from VAT.services.access_scope import (
    can_user_edit_centro,
    es_operador_cfp,
    filter_centros_queryset_for_management,
    filter_centros_queryset_for_user,
    is_vat_provincial,
    is_vat_sse,
)
from iam.services import user_has_permission_code
from users.territorial_scope import apply_full_province_scope


RESOURCES = {
    "centros": (models.Centro, "centro"),
    "cursos": (models.Curso, "curso"),
    "comisiones": (models.ComisionCurso, "comisioncurso"),
    "horarios": (models.ComisionHorario, "comisionhorario"),
    "contactos": (models.InstitucionContacto, "institucioncontacto"),
    "ubicaciones": (models.InstitucionUbicacion, "institucionubicacion"),
    "planes": (models.PlanVersionCurricular, "planversioncurricular"),
    "inscripciones": (models.Inscripcion, "inscripcion"),
    "sesiones": (models.SesionComision, "asistenciasesion"),
}

DETAIL_FIELDS = {
    "centros": [
        "codigo",
        "provincia",
        "municipio",
        "localidad",
        "domicilio_actividad",
        "codigo_postal",
        "telefono",
        "celular",
        "correo",
        "sitio_web",
        "tipo_gestion",
        "clase_institucion",
        "situacion",
    ],
    "cursos": [
        "plan_estudio",
        "modalidad",
        "tipo",
        "estado",
        "inscripcion_libre",
        "observaciones",
    ],
    "comisiones": [
        "curso",
        "ubicacion",
        "fecha_inicio",
        "fecha_fin",
        "cupo_total",
        "acepta_lista_espera",
        "cupo_lista_espera",
        "estado",
        "observaciones",
    ],
    "contactos": [
        "nombre_contacto",
        "documento",
        "rol_area",
        "telefono_contacto",
        "email_contacto",
        "es_principal",
    ],
    "ubicaciones": [
        "nombre_ubicacion",
        "rol_ubicacion",
        "localidad",
        "domicilio",
        "es_principal",
        "observaciones",
    ],
    "planes": [
        "provincia",
        "sector",
        "subsector",
        "modalidad_cursada",
        "normativa",
        "horas_reloj",
        "nivel_requerido",
        "nivel_certifica",
        "activo",
    ],
    "inscripciones": ["ciudadano", "estado", "fecha_inscripcion", "observaciones"],
    "sesiones": ["numero_sesion", "fecha", "estado"],
    "horarios": ["dia_semana", "hora_desde", "hora_hasta", "vigente"],
}


def centros_for_actor(actor, *, management=False):
    scope = (
        filter_centros_queryset_for_management
        if management
        else filter_centros_queryset_for_user
    )
    return scope(models.Centro.objects.all(), actor)


# Cada recurso conserva su queryset y alcance de dominio.
# pylint: disable-next=too-many-return-statements
def resource_queryset(resource, actor, *, management=False):
    model, _ = RESOURCES[resource]
    queryset = model.objects.all()
    centros = centros_for_actor(actor, management=management)
    if resource == "centros":
        return (
            centros.select_related("provincia", "localidad", "municipio", "referente")
            .prefetch_related("contactos_adicionales")
            .annotate(
                ubicaciones_count=Count("ubicaciones", distinct=True),
                contactos_count=Count("contactos_adicionales", distinct=True),
            )
        )
    if resource == "planes":
        if not (is_vat_sse(actor) or is_vat_provincial(actor)):
            return queryset.none()
        if not is_vat_sse(actor):
            queryset = apply_full_province_scope(
                queryset, actor, provincia_lookup="provincia_id"
            )
        return queryset.select_related(
            "provincia", "sector", "subsector", "modalidad_cursada"
        )
    if resource == "comisiones":
        return (
            queryset.filter(curso__centro__in=centros)
            .select_related("curso__centro", "ubicacion", "curso__plan_estudio")
            .prefetch_related("horarios__dia_semana")
            .annotate(
                inscriptos_count=Count(
                    "inscripciones",
                    filter=Q(
                        inscripciones__estado__in=("inscripta", "validada_presencial")
                    ),
                    distinct=True,
                ),
                clases_count=Count("sesiones", distinct=True),
                clases_realizadas=Count(
                    "sesiones", filter=Q(sesiones__estado="realizada"), distinct=True
                ),
            )
        )
    if resource in ("inscripciones", "sesiones", "horarios"):
        queryset = queryset.filter(comision_curso__curso__centro__in=centros)
        if resource == "inscripciones":
            return queryset.select_related("ciudadano", "comision_curso__curso__centro")
        if resource == "horarios":
            return queryset.select_related(
                "dia_semana", "comision_curso__curso__centro"
            )
        return queryset.select_related(
            "horario__dia_semana", "comision_curso__curso__centro"
        ).annotate(
            presentes_count=Count("asistencias", filter=Q(asistencias__presente=True)),
            ausentes_count=Count("asistencias", filter=Q(asistencias__presente=False)),
        )
    queryset = queryset.filter(centro__in=centros).select_related("centro")
    if resource == "cursos":
        queryset = queryset.select_related("plan_estudio").annotate(
            comisiones_count=Count("comisiones", distinct=True)
        )
    return queryset


# Adaptación explícita de filtros por recurso.
# pylint: disable-next=too-many-branches
def filter_resource_queryset(queryset, resource, params):
    query = (params.get("search") or "").strip()
    if query:
        lookups = {
            "centros": ["nombre", "codigo"],
            "cursos": ["nombre"],
            "planes": ["nombre"],
            "contactos": ["nombre_contacto", "documento"],
            "ubicaciones": ["nombre_ubicacion", "domicilio"],
            "comisiones": ["curso__nombre"],
            "inscripciones": [
                "ciudadano__nombre",
                "ciudadano__apellido",
                "ciudadano__documento",
                "ciudadano__documento_pasaporte",
            ],
        }.get(resource, [])
        condition = Q()
        for lookup in lookups:
            condition |= Q(**{f"{lookup}__icontains": query})
        if lookups:
            queryset = queryset.filter(condition)
    filters = {
        "centros": {
            "provincia": "provincia_id",
            "municipio": "municipio_id",
            "localidad": "localidad_id",
            "cue": "codigo",
        },
        "cursos": {"centro": "centro_id", "plan_estudio": "plan_estudio_id"},
        "comisiones": {"curso": "curso_id", "centro": "curso__centro_id"},
        "contactos": {"centro": "centro_id"},
        "ubicaciones": {"centro": "centro_id"},
        "inscripciones": {"comision": "comision_curso_id"},
        "sesiones": {"comision": "comision_curso_id"},
        "horarios": {"comision": "comision_curso_id"},
        "planes": {"provincia": "provincia_id", "sector": "sector_id"},
    }[resource]
    for param, lookup in filters.items():
        value = params.get(param)
        if value:
            if lookup.endswith("_id") and not str(value).isdigit():
                return queryset.none()
            queryset = queryset.filter(**{lookup: value})
    if resource in ("centros", "planes") and params.get("activo") in ("true", "false"):
        queryset = queryset.filter(activo=params["activo"] == "true")
    elif resource in (
        "cursos",
        "comisiones",
        "inscripciones",
        "sesiones",
    ) and params.get("estado"):
        queryset = queryset.filter(estado=params["estado"])
    if resource == "centros" and params.get("nombre"):
        queryset = queryset.filter(nombre__icontains=params["nombre"].strip())
    if resource == "cursos" and params.get("estado_carga") in (
        "con_comision",
        "sin_comision",
    ):
        queryset = (
            queryset.filter(comisiones_count__gt=0)
            if params["estado_carga"] == "con_comision"
            else queryset.filter(comisiones_count=0)
        )
    if resource == "sesiones" and params.get("estado_asistencia"):
        state = params["estado_asistencia"]
        if state == "pendiente":
            queryset = queryset.filter(
                estado="programada", fecha__lt=timezone.localdate()
            )
        elif state == "programada":
            queryset = queryset.filter(
                estado="programada", fecha__gte=timezone.localdate()
            )
        elif state in ("completada", "cancelada"):
            queryset = queryset.filter(
                estado="realizada" if state == "completada" else "cancelada"
            )
    return queryset.order_by("id")


def item_centro(resource, item):
    if resource == "centros":
        return item
    if resource == "comisiones":
        return item.curso.centro
    if resource in ("inscripciones", "sesiones", "horarios"):
        return item.comision_curso.curso.centro
    return getattr(item, "centro", None)


def can_mutate(resource, actor, item, action):
    _, codename = RESOURCES[resource]
    if not user_has_permission_code(actor, f"VAT.{action}_{codename}"):
        return False
    if resource == "planes":
        return is_vat_sse(actor) or is_vat_provincial(actor)
    centro = item_centro(resource, item)
    return centro is not None and can_user_edit_centro(actor, centro)


# Adaptador explícito del contrato común para los recursos de INET.
# pylint: disable-next=too-many-branches
def serialize_item(resource, item, actor):
    centro = item_centro(resource, item)
    label = getattr(item, "nombre", None)
    if resource == "contactos":
        label = item.nombre_contacto or item.valor
    elif resource == "ubicaciones":
        label = item.nombre_ubicacion or item.get_rol_ubicacion_display()
    elif resource == "inscripciones":
        label = item.ciudadano.nombre_completo
    elif resource == "sesiones":
        label = f"Clase {item.numero_sesion}"
    elif resource == "horarios":
        label = str(item.dia_semana)
    elif resource == "comisiones":
        label = f"Comisión #{item.pk} · {item.curso.nombre}"
    fields = []
    for name in DETAIL_FIELDS[resource]:
        if (
            resource == "centros"
            and es_operador_cfp(actor)
            and name in ("tipo_gestion", "clase_institucion", "situacion")
        ):
            continue
        value = getattr(item, name, None)
        if isinstance(value, bool):
            value = "Sí" if value else "No"
        elif isinstance(value, list):
            value = ", ".join(map(str, value))
        else:
            display = getattr(item, f"get_{name}_display", None)
            if display:
                value = display()
        fields.append(
            {
                "label": str(item._meta.get_field(name).verbose_name),
                "value": str(value or ""),
            }
        )
    if resource == "inscripciones":
        fields.append(
            {
                "label": "Documento",
                "value": str(
                    item.ciudadano.documento_pasaporte
                    or item.ciudadano.documento
                    or "Sin DNI"
                ),
            }
        )
    fields.extend(presentation_fields(resource, item, actor))
    ciudadano = item.ciudadano if resource == "inscripciones" else None
    attendance = None
    if resource == "inscripciones":
        completed = models.SesionComision.objects.filter(
            comision_curso_id=item.comision_curso_id, estado="realizada"
        ).count()
        if completed:
            attendance = round(
                100
                * item.asistencias.filter(
                    sesion__estado="realizada", presente=True
                ).count()
                / completed,
                1,
            )
    elif resource == "comisiones":
        summary = models.AsistenciaSesion.objects.filter(
            sesion__comision_curso=item,
            sesion__estado="realizada",
            inscripcion__estado__in=("inscripta", "validada_presencial"),
        ).aggregate(total=Count("pk"), presentes=Count("pk", filter=Q(presente=True)))
        attendance = (
            round(100 * summary["presentes"] / summary["total"], 1)
            if summary["total"]
            else None
        )
    state = getattr(item, "estado", "")
    display = getattr(item, "get_estado_display", None)
    if hasattr(item, "activo"):
        state = "Activo" if item.activo else "Inactivo"
    return {
        "id": item.pk,
        "nombre": label or str(item),
        "estado": display() if display else state,
        "provincia": str(getattr(centro or item, "provincia", "") or ""),
        "localidad": str(getattr(centro, "localidad", "") or ""),
        "cue": getattr(centro, "codigo", ""),
        "centro_id": centro.pk if centro else None,
        "curso_id": (
            item.curso_id
            if resource == "comisiones"
            else (item.pk if resource == "cursos" else None)
        ),
        "comision_id": (
            item.pk
            if resource == "comisiones"
            else getattr(item, "comision_curso_id", None)
        ),
        "fecha_inicio": getattr(item, "fecha_inicio", None),
        "fecha_fin": getattr(item, "fecha_fin", None),
        "detalle": fields,
        "puede_gestionar": (
            can_user_edit_centro(actor, centro)
            if centro
            else (is_vat_sse(actor) or is_vat_provincial(actor))
        ),
        "puede_editar": can_mutate(resource, actor, item, "change"),
        "puede_eliminar": can_mutate(resource, actor, item, "delete"),
        "comisiones_count": getattr(item, "comisiones_count", 0),
        "inscriptos_count": getattr(item, "inscriptos_count", 0),
        "clases_count": getattr(item, "clases_count", 0),
        "clases_realizadas": getattr(item, "clases_realizadas", 0),
        "asistencia_pct": attendance,
        "documento": (
            str(ciudadano.documento_pasaporte or ciudadano.documento or "")
            if ciudadano
            else ""
        ),
        "email": ciudadano.email or "" if ciudadano else "",
        "telefono": ciudadano.telefono or "" if ciudadano else "",
        "identidad_pendiente": bool(
            ciudadano
            and ciudadano.tipo_registro_identidad != ciudadano.TIPO_REGISTRO_ESTANDAR
        ),
    }


def presentation_fields(resource, item, actor):
    """Datos del contexto visual, con el mismo alcance/permisos del recurso."""
    values = {}
    if resource == "centros":
        values = {
            "Domicilio mapa": (
                " ".join(
                    str(part).strip()
                    for part in (item.calle, item.numero)
                    if part is not None and str(part).strip()
                )
                if item.calle and item.calle.strip()
                else item.domicilio_actividad
            ),
            "Ubicaciones": getattr(item, "ubicaciones_count", 0),
            "Contactos": getattr(item, "contactos_count", 0),
            "Actualizado": (
                getattr(item, "fecha_modificacion", None).date().isoformat()
                if getattr(item, "fecha_modificacion", None)
                else ""
            ),
        }
        if user_has_permission_code(actor, "VAT.view_institucioncontacto"):
            principal = next(
                (row for row in item.contactos_adicionales.all() if row.es_principal),
                None,
            )
            values.update(
                {
                    "Referente nombre": principal.nombre_contacto if principal else "",
                    "Referente DNI": principal.documento if principal else "",
                    "Referente teléfono": (
                        principal.telefono_contacto if principal else ""
                    ),
                    "Referente correo": principal.email_contacto if principal else "",
                    "Referente usuario": (
                        item.referente.get_username() if item.referente else ""
                    ),
                }
            )
    elif resource == "comisiones":
        weekly_minutes = sum(
            row.hora_hasta.hour * 60
            + row.hora_hasta.minute
            - row.hora_desde.hour * 60
            - row.hora_desde.minute
            for row in item.horarios.all()
            if row.vigente
        )
        values = {
            "Curso nombre": item.curso.nombre,
            "Centro nombre": item.curso.centro.nombre,
            "Plan nombre": (
                item.curso.plan_estudio.nombre if item.curso.plan_estudio else ""
            ),
            "Ubicación nombre": (
                item.ubicacion.nombre_ubicacion
                or item.ubicacion.get_rol_ubicacion_display()
                if item.ubicacion
                else ""
            ),
            "Total semanal": f"{weekly_minutes / 60:g} horas",
            "Horarios": " · ".join(
                f"{row.dia_semana}, {row.hora_desde:%H:%M} a {row.hora_hasta:%H:%M}"
                for row in item.horarios.all()
                if row.vigente
            ),
        }
    elif resource == "cursos":
        values = {
            "Centro nombre": item.centro.nombre,
            "Plan nombre": item.plan_estudio.nombre if item.plan_estudio else "",
        }
    elif resource == "sesiones":
        values = {
            "Curso nombre": item.comision_curso.curso.nombre,
            "Presentes": (
                getattr(item, "presentes_count", 0)
                if item.estado == "realizada"
                else ""
            ),
            "Ausentes": (
                getattr(item, "ausentes_count", 0) if item.estado == "realizada" else ""
            ),
            "Estado visual": (
                "Completada"
                if item.estado == "realizada"
                else (
                    "Asistencia pendiente"
                    if item.estado == "programada" and item.fecha < timezone.localdate()
                    else item.get_estado_display()
                )
            ),
            "Desde": item.horario.hora_desde.strftime("%H:%M") if item.horario else "",
            "Hasta": item.horario.hora_hasta.strftime("%H:%M") if item.horario else "",
        }
    return [
        {"label": label, "value": str(value if value is not None else "")}
        for label, value in values.items()
    ]
