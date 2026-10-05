"""JSON adapter for the existing VPSL forms and workflow views.

The legacy views remain the single implementation of each write. This adapter
only supplies form metadata and converts their responses for the React client.
"""

from datetime import date, datetime, time
import re
from functools import wraps

from django import forms
from django.contrib.messages import get_messages
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from core.models import Localidad
from core.soft_delete.preview import build_delete_preview
from iam.services import user_has_permission_code
from ver_para_ser_libre import views
from ver_para_ser_libre.forms import (
    CasoLaboratorioVPSLForm,
    ChecklistSedeVPSLForm,
    CierreDiarioVPSLForm,
    ItinerarioVPSLForm,
    JornadaVPSLForm,
    RegistroNominalVPSLForm,
    SedeCreateVPSLForm,
    SedeUpdateVPSLForm,
)
from ver_para_ser_libre.models import (
    CasoLaboratorioVPSL,
    CierreDiarioVPSL,
    ItinerarioVPSL,
    JornadaVPSL,
    RegistroNominalVPSL,
    SedeVPSL,
)
from ver_para_ser_libre.services import workflow
from ver_para_ser_libre.services import access


FORM_PERMISSIONS = {
    "itinerario-create": ("add_itinerariovpsl", "create_itinerarios_any_province_vpsl"),
    "itinerario-edit": ("change_itinerariovpsl",),
    "itinerario-subsanar": ("change_itinerariovpsl",),
    "sede-create": ("add_sedevpsl",),
    "sede-edit": ("change_sedevpsl",),
    "jornada-create": ("add_jornadavpsl",),
    "jornada-edit": ("change_jornadavpsl",),
    "checklist": ("add_checklistjornadavpsl",),
    "registro-create": ("add_registronominalvpsl",),
    "registro-edit": ("change_registronominalvpsl",),
    "laboratorio": ("change_casolaboratoriovpsl",),
    "cierre": ("add_cierrediariovpsl",),
}


def _json_not_found(handler):
    @wraps(handler)
    def wrapper(*args, **kwargs):
        try:
            return handler(*args, **kwargs)
        except Http404:
            return JsonResponse({"error": "Recurso no encontrado."}, status=404)

    return wrapper


ACTION_PERMISSIONS = {
    "presentar": "change_itinerariovpsl",
    "evaluar": "change_itinerariovpsl",
    "habilitar": "change_jornadavpsl",
    "cierre-definitivo": "change_jornadavpsl",
    "laboratorio-masivo": "change_casolaboratoriovpsl",
    "eliminar-itinerario": "delete_itinerariovpsl",
    "eliminar-sede": "delete_sedevpsl",
    "eliminar-jornada": "delete_jornadavpsl",
    "eliminar-registro": "delete_registronominalvpsl",
}


def _allowed(request, codenames):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Iniciá sesión en SISOC."}, status=401)
    if not any(
        user_has_permission_code(request.user, f"ver_para_ser_libre.{code}")
        for code in codenames
    ):
        return JsonResponse(
            {"error": "No tenés permiso para esta operación."}, status=403
        )
    return None


def _itinerario(pk, user):
    return get_object_or_404(
        access.filtrar_itinerarios_por_usuario(ItinerarioVPSL.objects.all(), user),
        pk=pk,
    )


def get_jornada(pk, user):
    return get_object_or_404(
        access.filtrar_jornadas_por_usuario(JornadaVPSL.objects.all(), user), pk=pk
    )


def _registro(pk, user):
    return get_object_or_404(
        RegistroNominalVPSL.objects.filter(
            jornada__in=access.filtrar_jornadas_por_usuario(
                JornadaVPSL.objects.all(), user
            )
        ),
        pk=pk,
    )


def _laboratorio(pk, user):
    return get_object_or_404(
        access.filtrar_casos_laboratorio_por_usuario(
            CasoLaboratorioVPSL.objects.all(), user
        ),
        pk=pk,
    )


def _value(value):
    if value is None:
        return ""
    if isinstance(value, (date, datetime, time)):
        return value.isoformat()
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value]
    return str(value)


def _schema(input_form):
    fields = []
    for name, field in input_form.fields.items():
        bound = input_form[name]
        widget = field.widget
        field_type = getattr(widget, "input_type", "text")
        if isinstance(widget, forms.Textarea):
            field_type = "textarea"
        elif isinstance(widget, forms.SelectMultiple):
            field_type = "multiselect"
        elif isinstance(widget, forms.Select):
            field_type = "select"
        choices = []
        if field_type in {"select", "multiselect"}:
            for choice_value, label in getattr(field, "choices", widget.choices):
                if isinstance(label, (list, tuple)):
                    choices.extend(
                        {"value": str(nested_value), "label": str(nested_label)}
                        for nested_value, nested_label in label
                    )
                else:
                    choices.append({"value": str(choice_value), "label": str(label)})
        fields.append(
            {
                "name": name,
                "label": str(field.label or name.replace("_", " ").title()),
                "type": field_type,
                "required": field.required,
                "disabled": field.disabled,
                "help": str(field.help_text or ""),
                "value": (
                    [str(value) for value in (bound.value() or [])]
                    if field_type == "multiselect"
                    else _value(bound.value())
                ),
                "choices": choices,
                "file_url": getattr(bound.value(), "url", "") if bound.value() else "",
                "min": _value(widget.attrs.get("min", "")),
                "max": _value(widget.attrs.get("max", "")),
                "step": _value(widget.attrs.get("step", "")),
                "graduacion_opcional": widget.attrs.get("data-graduacion-opcional")
                == "1",
            }
        )
    return fields


def _react_redirect(location):
    for pattern, target in (
        (r"/ver-para-ser-libre/jornadas/(\d+)/", "jornadas/{}/"),
        (r"/ver-para-ser-libre/sedes/(\d+)/", "sedes/{}/"),
        (r"/ver-para-ser-libre/(\d+)/", "itinerarios/{}/"),
    ):
        match = re.search(pattern, location)
        if match:
            return target.format(match.group(1))
    return ""


def _form_back(kind, pk, input_form):
    if kind == "registro-edit":
        return f"jornadas/{input_form.instance.jornada_id}/"
    if kind == "laboratorio":
        return f"jornadas/{input_form.instance.registro.jornada_id}/"
    targets = {
        "jornada-create": f"itinerarios/{pk}/",
        "jornada-edit": f"jornadas/{pk}/",
        "checklist": f"jornadas/{pk}/",
        "registro-create": f"jornadas/{pk}/",
        "cierre": f"jornadas/{pk}/",
        "sede-create": "sedes/",
        "sede-edit": f"sedes/{pk}/",
        "itinerario-edit": f"itinerarios/{pk}/",
        "itinerario-subsanar": f"itinerarios/{pk}/",
    }
    return targets.get(kind, "")


def _itinerario_context(kind, pk, request):
    user = request.user
    if kind == "itinerario-create":
        locked = None
        if not user_has_permission_code(
            user, "ver_para_ser_libre.create_itinerarios_any_province_vpsl"
        ):
            locked = access.provincia_usuario_provincial(user)
        return (
            ItinerarioVPSLForm(provincia_bloqueada=locked),
            views.ItinerarioCreateView,
            {},
        )
    if kind in {"itinerario-edit", "itinerario-subsanar"}:
        item = _itinerario(pk, user)
        form = ItinerarioVPSLForm(
            instance=item,
            freeze_completed_fields=(
                kind == "itinerario-edit" and item.estado == "aprobado"
            ),
            subsanacion_only=(kind == "itinerario-subsanar"),
        )
        return (
            form,
            (
                views.ItinerarioUpdateView
                if kind == "itinerario-edit"
                else views.ItinerarioSubsanarView
            ),
            {"pk": pk},
        )
    raise ValueError("Formulario desconocido.")


def _sede_context(kind, pk, request):
    if kind == "sede-create":
        form = SedeCreateVPSLForm()
        view, kwargs = views.SedeCreateView, {}
    else:
        form = SedeUpdateVPSLForm(instance=get_object_or_404(SedeVPSL, pk=pk))
        view, kwargs = views.SedeUpdateView, {"pk": pk}
    provincia_id = request.GET.get("provincia")
    if provincia_id and provincia_id.isdigit():
        localidades = (
            Localidad.objects.filter(municipio__provincia_id=provincia_id)
            .order_by("nombre")
            .values_list("nombre", flat=True)
            .distinct()
        )
        form.fields["localidad"].choices = [
            ("", "Seleccioná una localidad"),
            *((nombre, nombre) for nombre in localidades),
        ]
    return form, view, kwargs


def _jornada_context(kind, pk, request):
    user = request.user
    if kind == "jornada-create":
        item = _itinerario(pk, user)
        if item.estado != "aprobado":
            raise ValueError("El itinerario debe estar aprobado.")
        return (
            JornadaVPSLForm(itinerario=item),
            views.JornadaCreateView,
            {"itinerario_pk": pk},
        )
    if kind == "jornada-edit":
        item = get_jornada(pk, user)
        return (
            JornadaVPSLForm(instance=item, itinerario=item.itinerario),
            views.JornadaUpdateView,
            {"pk": pk},
        )
    if kind == "checklist":
        item = get_jornada(pk, user)
        return (
            ChecklistSedeVPSLForm(jornada=item),
            views.ChecklistCreateView,
            {"jornada_pk": pk},
        )
    raise ValueError("Formulario desconocido.")


def _registro_context(kind, pk, request):
    user = request.user
    if kind == "registro-create":
        item = get_jornada(pk, user)
        if item.estado not in workflow.JORNADA_ESTADOS_REGISTRO_PERMITIDO:
            raise ValueError(
                "La jornada debe estar habilitada para registrar personas."
            )
        return (
            RegistroNominalVPSLForm(jornada=item),
            views.RegistroNominalCreateView,
            {"jornada_pk": pk},
        )
    if kind == "registro-edit":
        return (
            RegistroNominalVPSLForm(instance=_registro(pk, user)),
            views.RegistroNominalUpdateView,
            {"pk": pk},
        )
    raise ValueError("Formulario desconocido.")


def _laboratorio_context(_kind, pk, request):
    user = request.user
    if _kind == "laboratorio":
        item = _laboratorio(pk, user)
        return (
            CasoLaboratorioVPSLForm(
                instance=item, next_state=workflow.siguiente_estado_laboratorio(item)
            ),
            views.CasoLaboratorioUpdateView,
            {"pk": pk},
        )
    raise ValueError("Formulario desconocido.")


def _cierre_context(_kind, pk, request):
    user = request.user
    if _kind == "cierre":
        item = get_jornada(pk, user)
        initial = {}
        try:
            cierre = item.cierre
        except CierreDiarioVPSL.DoesNotExist:
            cierre = None
        if cierre:
            for name in (
                "cantidad_atenciones_registradas",
                "cantidad_lentes_entregados_dia",
                "cantidad_casos_laboratorio_reportados",
                "responsable_cierre",
                "observaciones",
            ):
                initial[name] = getattr(cierre, name)
        return (
            CierreDiarioVPSLForm(initial=initial),
            views.CierreDiarioCreateView,
            {"jornada_pk": pk},
        )

    raise ValueError("Formulario desconocido.")


FORM_CONTEXTS = {
    **dict.fromkeys(
        ("itinerario-create", "itinerario-edit", "itinerario-subsanar"),
        _itinerario_context,
    ),
    **dict.fromkeys(("sede-create", "sede-edit"), _sede_context),
    **dict.fromkeys(("jornada-create", "jornada-edit", "checklist"), _jornada_context),
    **dict.fromkeys(("registro-create", "registro-edit"), _registro_context),
    "laboratorio": _laboratorio_context,
    "cierre": _cierre_context,
}


def _form_context(kind, pk, request):
    handler = FORM_CONTEXTS.get(kind)
    if handler is None:
        raise ValueError("Formulario desconocido.")
    return handler(kind, pk, request)


def _form_schema_response(instance, kind, pk):
    if kind in {"registro-create", "registro-edit"}:
        instance.fields["renaper_estado"] = forms.CharField(
            required=False,
            widget=forms.HiddenInput,
            initial="validado" if instance.instance.validado_renaper else "",
        )
    fields = _schema(instance)
    if kind in {"sede-create", "sede-edit"}:
        sede = instance.instance if instance.instance.pk else None
        fields.extend(_schema(ChecklistSedeVPSLForm(sede=sede, required=False)))
    return JsonResponse(
        {
            "fields": fields,
            "kind": kind,
            "back": _form_back(kind, pk, instance),
            "instrucciones": (
                getattr(instance.instance, "subsanacion_observaciones", "")
                if kind == "itinerario-subsanar"
                else ""
            ),
        }
    )


def _submit_form(request, view, kwargs):
    list(get_messages(request))  # Previous SISOC notices must not affect this result.
    response = view.as_view()(request, **kwargs)
    if response.status_code in (301, 302, 303):
        notices = list(get_messages(request))
        text = "; ".join(str(message) for message in notices)
        if any(message.level_tag == "error" for message in notices):
            return JsonResponse({"error": text}, status=400)
        return JsonResponse(
            {"ok": True, "message": text, "redirect": _react_redirect(response.url)}
        )
    context = getattr(response, "context_data", None) or {}
    errors = {}
    for key in ("form", "checklist_form"):
        invalid = context.get(key)
        if invalid is not None:
            errors.update(invalid.errors.get_json_data())
    if errors:
        return JsonResponse({"errors": errors}, status=400)
    return JsonResponse({"error": "Revisá los datos del formulario."}, status=400)


@_json_not_found
@require_http_methods(["GET", "POST"])
def workflow_form(request, kind, pk):
    permission = FORM_PERMISSIONS.get(kind)
    if permission is None:
        return JsonResponse({"error": "Formulario desconocido."}, status=404)
    denied = _allowed(request, permission)
    if denied:
        return denied
    try:
        instance, view, kwargs = _form_context(kind, pk, request)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    if request.method == "GET":
        return _form_schema_response(instance, kind, pk)
    return _submit_form(request, view, kwargs)


@require_POST
def ubicacion(request):
    denied = _allowed(request, ("add_jornadavpsl", "change_jornadavpsl"))
    if denied:
        return denied
    return views.buscar_ubicacion_google_maps(request)


def _delete_action(request, kind, pk):
    if kind == "eliminar-itinerario":
        item = _itinerario(pk, request.user)
    elif kind == "eliminar-sede":
        item = get_object_or_404(SedeVPSL, pk=pk)
    elif kind == "eliminar-jornada":
        item = get_jornada(pk, request.user)
    else:
        item = _registro(pk, request.user)
    if request.method == "GET":
        return JsonResponse({"preview": build_delete_preview(item)})
    item.delete(user=request.user, cascade=True)
    return JsonResponse({"ok": True})


def _run_action(request, kind, pk):
    list(get_messages(request))
    if kind in {"presentar", "evaluar"}:
        _itinerario(pk, request.user)
    else:
        get_jornada(pk, request.user)
    handlers = {
        "presentar": views.presentar_itinerario,
        "evaluar": views.aprobar_itinerario,
        "habilitar": views.habilitar_jornada,
        "cierre-definitivo": views.cierre_definitivo_jornada,
        "laboratorio-masivo": views.actualizar_laboratorio_masivo,
    }
    handlers[kind](request, pk)
    messages = list(get_messages(request))
    if any(message.level_tag == "error" for message in messages):
        return JsonResponse(
            {"error": "; ".join(str(message) for message in messages)}, status=400
        )
    return JsonResponse(
        {"ok": True, "message": "; ".join(str(message) for message in messages)}
    )


@_json_not_found
@require_http_methods(["GET", "POST"])
def action(request, kind, pk):
    permission = ACTION_PERMISSIONS.get(kind)
    if permission is None:
        return JsonResponse({"error": "Acción desconocida."}, status=404)
    denied = _allowed(request, (permission,))
    if denied:
        return denied
    if kind.startswith("eliminar-"):
        return _delete_action(request, kind, pk)
    if request.method != "POST":
        return JsonResponse({"error": "Método no permitido."}, status=405)
    return _run_action(request, kind, pk)


@_json_not_found
@require_GET
def renaper(request):
    denied = _allowed(
        request,
        (
            "add_registronominalvpsl",
            "change_registronominalvpsl",
            "add_jornadavpsl",
            "change_jornadavpsl",
        ),
    )
    if denied:
        return denied
    jornada = request.GET.get("jornada")
    if jornada:
        get_jornada(jornada, request.user)
    return views.consultar_renaper_vpsl(request)


@_json_not_found
@require_GET
def export(request, kind, pk):
    if kind not in {"itinerario", "jornada"}:
        return JsonResponse({"error": "Exportación desconocida."}, status=404)
    permission = f"view_{'itinerariovpsl' if kind == 'itinerario' else 'jornadavpsl'}"
    denied = _allowed(request, (permission,))
    if denied:
        return denied
    if not user_has_permission_code(request.user, "auth.role_exportar_a_csv"):
        return JsonResponse({"error": "No tenés permiso para exportar."}, status=403)
    if kind == "itinerario":
        _itinerario(pk, request.user)
        return views.ItinerarioExportView.as_view()(request, pk=pk)
    get_jornada(pk, request.user)
    return views.JornadaExportView.as_view()(request, pk=pk)
