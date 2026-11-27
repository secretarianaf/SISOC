"""Private native-context projection for the canonical Expedientes list only."""

from django.http import JsonResponse
from django.urls import reverse

from celiaquia.views.expediente import ExpedienteListView
from celiaquia.canonical_shell import canonical_screen

_native_list = ExpedienteListView.as_view()


def _url(name, pk):
    return reverse(name, args=[pk])


def _person(user):
    return (user.get_full_name() or user.username) if user else None


def _row(expediente, context):
    state = expediente.estado.nombre
    provincial = context["is_provincial_celiaquia"]
    manager = context["can_manage_tecnicos_celiaquia"]
    actions = []
    if provincial and state == "CREADO":
        actions.extend(
            [
                {
                    "label": "Editar",
                    "url": _url("expediente_update", expediente.pk),
                    "method": "GET",
                },
                {
                    "label": "Procesar",
                    "url": _url("expediente_procesar", expediente.pk),
                    "method": "POST",
                },
            ]
        )
    if provincial and state == "EN_ESPERA":
        actions.append(
            {
                "label": "Confirmar envío",
                "url": _url("expediente_confirm", expediente.pk),
                "method": "GET",
            }
        )
    if manager and state == "CONFIRMACION_DE_ENVIO":
        actions.append(
            {
                "label": "Recepcionar",
                "url": _url("expediente_recepcionar", expediente.pk),
                "method": "POST",
            }
        )
    if manager:
        actions.append(
            {
                "label": "Eliminar",
                "url": _url("expediente_delete", expediente.pk),
                "method": "DELETE",
            }
        )
    assignments = [
        {"id": a.tecnico_id, "name": _person(a.tecnico)}
        for a in expediente.asignaciones_tecnicos.all()
    ]
    return {
        "id": expediente.pk,
        "numero": expediente.numero_expediente or "-",
        "fecha": expediente.fecha_creacion.isoformat(),
        "provincia": expediente.provincia_derivada or "-",
        "estado": expediente.estado.display_name(),
        "subsanar": expediente.legajos_subsanar_count,
        "subsanado": expediente.legajos_subsanado_count,
        "tecnicos": assignments,
        "can_assign": manager and state in {"RECEPCIONADO", "ASIGNADO"},
        "excel": (
            {
                "url": _url("expediente_excel_masivo_descargar", expediente.pk),
                "cargado_por": (
                    _person(expediente.excel_masivo_cargado_por)
                    if context["can_manage_excel_masivo_audit"]
                    else None
                ),
                "procesado_por": (
                    _person(expediente.excel_masivo_procesado_por)
                    if context["can_manage_excel_masivo_audit"]
                    else None
                ),
            }
            if context["can_download_excel_masivo"] and expediente.excel_masivo
            else None
        ),
        "actions": actions,
        "urls": {
            "detail": _url("expediente_detail", expediente.pk),
            "assign": _url("expediente_asignar_tecnico", expediente.pk),
        },
    }


def _projection(response):
    context = response.context_data
    return JsonResponse(
        {
            "version": 1,
            "title": context["titulo_listado"],
            "filters": context["filters_config"],
            "create_url": (
                reverse("expediente_create")
                if context["is_provincial_celiaquia"]
                else None
            ),
            "show_tecnicos": context["show_tecnico_column_celiaquia"],
            "show_excel": context["can_download_excel_masivo"],
            "show_audit": context["can_manage_excel_masivo_audit"],
            "tecnicos": [{"id": u.pk, "name": _person(u)} for u in context["tecnicos"]],
            # Native get_paginate_by returns None: do not truncate this list.
            "rows": [
                _row(expediente, context) for expediente in context["expedientes"]
            ],
        }
    )


canonical_expedientes = canonical_screen(
    _native_list,
    "expedientes",
    lambda request, *args, **kwargs: _projection(
        _native_list(request, *args, **kwargs)
    ),
)
