"""Private projection of the native Expediente detail for its React screen.

The projection renders nothing itself: it runs ``ExpedienteDetailView`` (scope,
404s, computed flags and enrichment included) and serializes the context the
template reads, plus the native URLs that each visible action posts to. Every
role/state condition below mirrors a condition of ``expediente_detail.html`` or
its included components; mutations keep going to the native endpoints.
"""

from django.contrib.messages import get_messages
from django.http import JsonResponse
from django.urls import reverse

from celiaquia.canonical_shell import canonical_screen
from celiaquia.views.expediente import ExpedienteDetailView
from core.templatetags.custom_filters import edad, es_mayor_65_menor_66, es_menor_18

_native_detail = ExpedienteDetailView.as_view()

PREVIEW_LIMIT_LABELS = {"all": "Todos"}
SUBSANACION_TIPO_LABELS = {
    "RENAPER": "Subsanación RENAPER solicitada",
    "ANSES": "Subsanación ANSES solicitada",
    "CONDICION_DIAGNOSTICA": "Subsanación por condición diagnóstica solicitada",
    "DOCUMENTACION": "Subsanación por documentación solicitada",
    "DATOS_PERSONALES": "Subsanación por datos personales solicitada",
    "OTROS": "Subsanación por otros motivos solicitada",
}
RENAPER_RECHAZADO = 2
RENAPER_SUBSANAR = 3


def _person(user):
    return (user.get_full_name() or user.username) if user else None


def _dt(value):
    return value.isoformat() if value else None


def _file_url(field):
    if not field:
        return None
    try:
        return field.url
    except ValueError:
        return None


def _estado_legajo(legajo):
    """Badge text shared by the row, the expanded detail and the family modal."""
    revision = legajo.revision_tecnico
    if revision == "APROBADO":
        return "Aprobado"
    if revision == "RECHAZADO" or legajo.estado_validacion_renaper == RENAPER_RECHAZADO:
        return "Rechazado"
    if revision == "SUBSANAR":
        return "Subsanar"
    if revision == "SUBSANADO":
        return "Subsanado"
    return "Pendiente"


def _badges(legajo):
    """Role and age badges, in the same order and branches as the template."""
    nacimiento = legajo.ciudadano.fecha_nacimiento
    hijos = len(legajo.hijos_a_cargo)
    hijos_text = (
        f"Tiene {hijos} hijo{'s' if hijos > 1 else ''} a cargo" if hijos else None
    )
    menor = (
        f"Responsable menor de 18 años ({edad(nacimiento)} años)"
        if es_menor_18(nacimiento)
        else None
    )
    mayor = (
        f"Adulto mayor de 65 años ({edad(nacimiento)} años)"
        if es_mayor_65_menor_66(nacimiento)
        else None
    )
    badges, notes = [], []
    if legajo.es_doble_rol:
        badges.append({"text": "Beneficiario y Responsable", "tone": "info"})
        notes = [hijos_text, menor, mayor]
    elif legajo.rol == "responsable":
        badges.append({"text": "Solo Responsable", "tone": "warning"})
        sin_menores = (
            None
            if es_menor_18(nacimiento) or hijos
            else "Responsable sin menores a cargo"
        )
        notes = [hijos_text, menor, sin_menores, mayor]
    elif hijos:
        badges.append({"text": "Beneficiario y Responsable", "tone": "warning"})
        notes = [hijos_text, menor, mayor]
    else:
        badges.append({"text": "Solo Beneficiario", "tone": "success"})
        notes = [mayor]
    alerts = [note for note in notes if note and note != hijos_text]
    if legajo.sin_responsable_alerta:
        alerts.append("Menor sin adulto responsable")
    return badges, hijos_text, alerts


def _archivo(arch):
    return {
        "id": arch.pk,
        "nombre": arch.nombre_archivo,
        "url": _file_url(arch.archivo),
        "origen": arch.get_origen_display(),
        "origen_codigo": arch.origen,
        "observacion": (
            arch.observacion.get_tipo_display() if arch.observacion else None
        ),
        "descripcion": arch.descripcion or "",
        "creado_en": _dt(arch.creado_en),
        "usuario": _person(arch.usuario),
    }


def _subsanacion(sub):
    return {
        "id": sub.pk,
        "estado": sub.estado,
        "estado_display": sub.get_estado_display(),
        "solicitada_por": _person(sub.solicitada_por),
        "solicitada_en": _dt(sub.solicitada_en),
        "respondida_por": _person(sub.respondida_por),
        "respondida_en": _dt(sub.respondida_en),
        "observaciones": [
            {"id": obs.pk, "tipo": obs.get_tipo_display(), "detalle": obs.detalle or ""}
            for obs in sub.observaciones.all()
        ],
        "archivos": [_archivo(arch) for arch in sub.archivos.all()],
    }


def _legajo(  # pylint: disable=too-many-locals
    legajo, ctx, expediente, responsables_de
):
    estado = expediente.estado.nombre
    is_tec, is_coord = ctx["is_tecnico_celiaquia"], ctx["is_coord_celiaquia"]
    is_prov, is_admin = ctx["is_provincial_celiaquia"], ctx["is_admin_celiaquia"]
    revision = legajo.revision_tecnico
    renaper = legajo.estado_validacion_renaper
    pk, legajo_pk = expediente.pk, legajo.pk
    badges, hijos_text, alerts = _badges(legajo)
    requeridos = legajo.archivos_requeridos
    can_upload = is_prov and estado == "EN_ESPERA" and revision != "SUBSANAR"
    archivos = [
        {
            "campo": campo,
            "label": requeridos[campo],
            "url": _file_url(getattr(legajo, campo)),
        }
        for campo in ("archivo2", "archivo3", "archivo1")
        if requeridos.get(campo)
    ]
    activa = legajo.subsanacion_activa
    show_activa = (
        revision == "SUBSANAR" and activa is not None and renaper != RENAPER_SUBSANAR
    )
    has_renaper_response = bool(
        legajo.subsanacion_renaper_comentario or legajo.subsanacion_renaper_archivo
    )
    revisable = (
        revision in {"PENDIENTE", "SUBSANADO"}
        and (is_coord or is_tec)
        and estado in {"EN_ESPERA", "ASIGNADO", "PROCESO_DE_CRUCE"}
    )
    return {
        "id": legajo_pk,
        "ciudadano_id": legajo.ciudadano_id,
        "nombre": legajo.ciudadano.nombre,
        "apellido": legajo.ciudadano.apellido,
        "documento": str(legajo.ciudadano.documento or ""),
        "rol": legajo.rol,
        "tipo_legajo": legajo.tipo_legajo,
        "es_responsable": legajo.es_responsable,
        "es_doble_rol": legajo.es_doble_rol,
        "es_hijo": not legajo.es_responsable and legajo.responsable_id is not None,
        "icono": (
            "familia"
            if legajo.es_doble_rol
            else (
                "adulto"
                if legajo.rol == "responsable" or legajo.hijos_a_cargo
                else "menor"
            )
        ),
        "hijos_a_cargo": [
            {
                "id": hijo.id,
                "nombre": hijo.nombre,
                "apellido": hijo.apellido,
                "documento": str(hijo.documento or ""),
            }
            for hijo in legajo.hijos_a_cargo
        ],
        "responsables": responsables_de.get(legajo.ciudadano_id, []),
        "badges": badges,
        "hijos_texto": hijos_text,
        "alertas": alerts,
        "revision_tecnico": revision,
        "estado_validacion_renaper": renaper,
        "estado": _estado_legajo(legajo),
        "documentos": legajo.doc_indicadores,
        "observacion": {
            "titulo": legajo.observacion_tecnica_titulo,
            "texto": legajo.observacion_tecnica_texto,
            "items": legajo.observacion_tecnica_items,
        },
        "subsanacion_motivo": legajo.subsanacion_motivo or "",
        "renaper": {
            "comentario": legajo.subsanacion_renaper_comentario or "",
            "archivo_url": _file_url(legajo.subsanacion_renaper_archivo),
            "respuesta_label": (
                legajo.subsanacion_respuesta_label if has_renaper_response else None
            ),
            "pendiente": renaper == RENAPER_SUBSANAR and not has_renaper_response,
            "solicitud_label": SUBSANACION_TIPO_LABELS.get(
                legajo.subsanacion_tipo, "Subsanación solicitada"
            ),
        },
        "archivos": archivos,
        "subsanacion_activa": (
            {
                **_subsanacion(activa),
                "archivos_de_nacion": [
                    _archivo(arch) for arch in activa.archivos_de_nacion
                ],
                "archivos_de_provincia": [
                    _archivo(arch) for arch in activa.archivos_de_provincia
                ],
                "observaciones_opciones": legajo.subsanacion_obs_data,
            }
            if show_activa
            else None
        ),
        "subsanaciones_historial": [
            _subsanacion(sub) for sub in legajo.subsanaciones_historial
        ],
        "comentarios_visibles": bool(
            is_tec or is_coord or (is_prov and legajo.comentarios_visibles_provincia)
        ),
        "actions": {
            "editar": (
                reverse("legajo_editar", args=[pk, legajo_pk])
                if is_tec
                or is_coord
                or (is_prov and estado in {"CREADO", "PROCESADO", "EN_ESPERA"})
                else None
            ),
            "eliminar": (
                reverse("legajo_revisar", args=[pk, legajo_pk])
                if is_coord or (is_prov and estado == "EN_ESPERA")
                else None
            ),
            "subir_archivo": (
                reverse("legajo_archivo_upload", args=[pk, legajo_pk])
                if can_upload
                else None
            ),
            "comentarios": reverse("legajo_comentarios_list", args=[pk, legajo_pk]),
            "agregar_comentario": (
                reverse("legajo_comentario_create", args=[pk, legajo_pk])
                if is_tec or is_coord
                else None
            ),
            "confirmar_subsanacion": (
                reverse("expediente_confirm_subsanacion", args=[pk])
                if is_prov
                and revision == "SUBSANAR"
                and renaper != RENAPER_SUBSANAR
                and legajo.archivo2
                and legajo.archivo3
                and legajo.subsanacion_tiene_evidencia
                else None
            ),
            "responder_subsanacion": (
                reverse("subsanacion_responder", args=[pk, legajo_pk])
                if show_activa and is_prov
                else None
            ),
            "responder_renaper": (
                reverse("respuesta_subsanacion_renaper", args=[pk, legajo_pk])
                if is_prov and revision != "SUBSANADO" and renaper == RENAPER_SUBSANAR
                else None
            ),
            "validar_renaper": (
                reverse("legajo_validar_renaper", args=[pk, legajo_pk])
                if revisable
                else None
            ),
            "revisar": (
                reverse("legajo_revisar", args=[pk, legajo_pk]) if revisable else None
            ),
            "motivo_preview": (
                reverse("legajo_motivo_preview", args=[pk, legajo_pk])
                if revisable
                else None
            ),
            "corregir_evaluacion": (
                reverse("legajo_corregir_evaluacion", args=[pk, legajo_pk])
                if (is_admin or is_coord)
                and revision in {"APROBADO", "RECHAZADO", "SUBSANADO"}
                else None
            ),
        },
    }


def _responsables(legajos):
    """'Responsable: …' relation of the family modal: who lists each child."""
    result = {}
    for legajo in legajos:
        if not legajo.es_responsable:
            continue
        nombre = f"{legajo.ciudadano.nombre} {legajo.ciudadano.apellido}"
        for hijo in legajo.hijos_a_cargo:
            result.setdefault(hijo.id, []).append(nombre)
    return result


def _historial(request, page):
    params = request.GET.copy()
    params.pop("historial_page", None)
    return {
        "items": [
            {
                "id": item.pk,
                "fecha": _dt(item.fecha),
                "estado_anterior": (
                    item.estado_anterior.display_name() if item.estado_anterior else ""
                ),
                "estado_nuevo": (
                    item.estado_nuevo.display_name() if item.estado_nuevo else ""
                ),
                "usuario": _person(item.usuario),
                "observaciones": item.observaciones_visibles or "",
            }
            for item in page.object_list
        ],
        "page": page.number,
        "num_pages": page.paginator.num_pages,
    }


def _registros(ctx, expediente):
    pk = expediente.pk
    return [
        {
            "id": registro.pk,
            "fila": registro.fila_excel,
            "datos_raw": {
                key: ("" if value is None else str(value))
                for key, value in (registro.datos_raw or {}).items()
            },
            "datos": {
                key: ("" if value is None else str(value))
                for key, value in registro.datos_render.items()
            },
            "mensaje_error": registro.mensaje_error,
            "invalid_fields": sorted(registro.invalid_fields),
            "responsable_requerido": bool(registro.responsable_requerido),
            "nacionalidad_id": str(registro.nacionalidad_autocomplete_id or ""),
            "municipio_id": str(registro.municipio_autocomplete_id or ""),
            "actualizar_url": reverse(
                "registro_erroneo_actualizar", args=[pk, registro.pk]
            ),
            "eliminar_url": reverse(
                "registro_erroneo_eliminar", args=[pk, registro.pk]
            ),
        }
        for registro in ctx["registros_erroneos"]
    ]


def _catalogos(ctx):
    return {
        "sexos": [{"id": sexo.pk, "label": sexo.sexo} for sexo in ctx["sexos"]],
        "nacionalidades": [
            {"id": n.pk, "label": n.nacionalidad} for n in ctx["nacionalidades"]
        ],
        "nacionalidad_argentina_id": ctx["nacionalidad_argentina_id"],
        "municipios": [{"id": m.pk, "label": m.nombre} for m in ctx["municipios"]],
        "localidades": [
            {
                "id": loc.pk,
                "label": loc.nombre,
                "municipio_id": loc.municipio_id,
                "municipio": loc.municipio.nombre,
            }
            for loc in ctx["localidades"]
        ],
    }


def _alertas(ctx):
    alertas = []
    for key in ("alerta_importacion_resumen", "alerta_importacion_excluidos"):
        if ctx[key]:
            alertas.append({"style": ctx[f"{key}_style"] or "info", "text": ctx[key]})
    return alertas


def _preview(ctx, expediente):
    if not ctx["preview"]:
        return None
    preview = ctx["preview"]
    headers = list(preview.get("headers", []))
    return {
        "headers": headers,
        "rows": [
            [("" if row.get(h) is None else str(row.get(h))) for h in headers]
            for row in preview.get("rows", [])
        ],
        "limit": ctx["preview_limit_actual"],
        "options": [
            {"value": v, "label": PREVIEW_LIMIT_LABELS.get(v, v)}
            for v in ctx["preview_limit_opciones"]
        ],
        "procesar": (
            reverse("expediente_procesar", args=[expediente.pk])
            if expediente.estado.nombre == "CREADO"
            else None
        ),
    }


def _expediente(expediente, ctx):
    excel = None
    if ctx["can_download_excel_masivo"] and expediente.excel_masivo:
        audit = ctx["can_manage_excel_masivo_audit"]
        excel = {
            "nombre": expediente.excel_masivo.name,
            "url": reverse("expediente_excel_masivo_descargar", args=[expediente.pk]),
            "audit": audit,
            "cargado_por": (
                _person(expediente.excel_masivo_cargado_por) if audit else None
            ),
            "cargado_en": _dt(expediente.excel_masivo_cargado_en) if audit else None,
            "procesado_por": (
                _person(expediente.excel_masivo_procesado_por) if audit else None
            ),
            "procesado_en": (
                _dt(expediente.excel_masivo_procesado_en) if audit else None
            ),
        }
    return {
        "id": expediente.pk,
        "numero": expediente.numero_expediente or "-",
        "estado": expediente.estado.nombre,
        "estado_display": expediente.estado.display_name(),
        "fecha_creacion": _dt(expediente.fecha_creacion),
        "provincia": (
            str(ctx["provincia_expediente"]) if ctx["provincia_expediente"] else "-"
        ),
        "tecnicos": [
            _person(a.tecnico) for a in expediente.asignaciones_tecnicos.all()
        ],
        "excel": excel,
        "documento_url": _file_url(expediente.documento),
    }


def _actions(expediente, ctx, legajos):
    pk, estado = expediente.pk, expediente.estado.nombre
    is_tec, is_coord = ctx["is_tecnico_celiaquia"], ctx["is_coord_celiaquia"]
    is_prov = ctx["is_provincial_celiaquia"]
    cruce_states = {"ASIGNADO", "PROCESO_DE_CRUCE"}
    nacion = is_tec or is_coord
    return {
        "editar": (
            reverse("expediente_update", args=[pk]) if estado == "CREADO" else None
        ),
        "nomina_sintys": (
            reverse("expediente_nomina_sintys_export", args=[pk])
            if nacion and estado in cruce_states
            else None
        ),
        "historial": bool(nacion and estado in cruce_states),
        "familias": bool(nacion and estado in cruce_states),
        "subir_cruce": (
            reverse("expediente_cruce_cuit", args=[pk])
            if nacion and estado in cruce_states
            else None
        ),
        "reprocesar_cruce": (
            reverse("expediente_cruce_cuit", args=[pk])
            if nacion
            and expediente.cruce_excel
            and estado in cruce_states | {"CRUCE_FINALIZADO"}
            else None
        ),
        "padron_final": (
            reverse("expediente_padron_final_export", args=[pk])
            if ctx["can_download_nomina_aprobados"]
            else None
        ),
        # The native button reads ``registros_erroneos.count`` on a list, which
        # renders empty, so it is never disabled: the endpoint validates.
        "confirmar_envio": (
            reverse("expediente_confirm", args=[pk])
            if legajos and is_prov and estado == "EN_ESPERA"
            else None
        ),
        "asignar_tecnico": (
            reverse("expediente_asignar_tecnico", args=[pk])
            if expediente.estado_id == 2 and is_coord
            else None
        ),
        "reprocesar_errores": (
            reverse("registros_erroneos_reprocesar", args=[pk])
            if ctx["registros_erroneos"] and ctx["can_manage_registros_erroneos"]
            else None
        ),
    }


def _messages(request):
    return [
        {"level": message.level_tag or "info", "text": str(message)}
        for message in get_messages(request)
    ]


def _projection(request, *args, **kwargs):
    response = _native_detail(request, *args, **kwargs)
    ctx = response.context_data
    expediente = ctx["expediente"]
    legajos = ctx["legajos_enriquecidos"]
    responsables_de = _responsables(legajos)
    projected_legajos = [
        _legajo(legajo, ctx, expediente, responsables_de) for legajo in legajos
    ]
    needs_catalogs = bool(ctx["registros_erroneos"]) or any(
        row["actions"]["editar"] for row in projected_legajos
    )
    cupo = ctx["cupo_metrics"]
    return JsonResponse(
        {
            "version": 1,
            "expediente": _expediente(expediente, ctx),
            "roles": {
                "tecnico": ctx["is_tecnico_celiaquia"],
                "coordinador": ctx["is_coord_celiaquia"],
                "provincial": ctx["is_provincial_celiaquia"],
                "admin": ctx["is_admin_celiaquia"],
            },
            "flags": {
                "can_manage_tecnicos": ctx["can_manage_tecnicos_celiaquia"],
                "can_manage_registros_erroneos": ctx["can_manage_registros_erroneos"],
                "can_manage_excel_masivo_audit": ctx["can_manage_excel_masivo_audit"],
                "can_download_excel_masivo": ctx["can_download_excel_masivo"],
                "can_download_nomina_aprobados": ctx["can_download_nomina_aprobados"],
                "hay_subsanar": ctx["hay_subsanar"],
                "faltan_archivos": ctx["faltan_archivos"],
            },
            "actions": _actions(expediente, ctx, legajos),
            "cupo": (
                {
                    "total_asignado": cupo["total_asignado"],
                    "usados": cupo["usados"],
                    "disponibles": cupo["disponibles"],
                    "fuera": ctx["fuera_count"],
                }
                if cupo
                else None
            ),
            "alertas": _alertas(ctx),
            "fuera_de_cupo": [
                {
                    "id": leg.pk,
                    "documento": str(leg.ciudadano.documento or ""),
                    "nombre": leg.ciudadano.nombre,
                    "apellido": leg.ciudadano.apellido,
                }
                for leg in ctx["fuera_de_cupo"]
            ],
            "preview": _preview(ctx, expediente),
            "preview_error": ctx["preview_error"],
            "legajos_total": ctx["legajos_total"],
            "legajos": projected_legajos,
            "historial": _historial(request, ctx["historial_page_obj"]),
            "registros_erroneos": _registros(ctx, expediente),
            "tecnicos": [{"id": t.pk, "name": _person(t)} for t in ctx["tecnicos"]],
            "catalogos": _catalogos(ctx) if needs_catalogs else None,
            "comentarios": {
                "catalogo": ctx["catalogo_comentarios_tecnicos"],
                "tipos_documento": [
                    {"value": value, "label": str(label)}
                    for value, label in ctx["tipos_documento_comentario"]
                ],
            },
            "complementaria": {
                "accept": ctx["complementaria_accept"],
                "max_archivos": ctx["complementaria_max_archivos"],
                "max_mb": ctx["complementaria_max_mb"],
            },
            "messages": _messages(request),
        }
    )


expediente_detalle = canonical_screen(_native_detail, "expediente-detalle", _projection)
