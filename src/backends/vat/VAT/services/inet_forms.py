"""Adaptación de los formularios legacy al contrato JSON de INET."""

from django import forms
from django.http import QueryDict
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied, ValidationError

from VAT import forms as vat_forms
from VAT import models
from VAT.services.access_scope import can_user_create_centro, get_user_provincia_id
from VAT.services.inet_queries import centros_for_actor, resource_queryset
from iam.services import user_has_permission_code
from ciudadanos.forms import CiudadanoForm
from ciudadanos.models import Ciudadano


class InetCiudadanoForm(vat_forms.CiudadanoInscripcionRapidaForm):
    """Alta rápida existente con los canales de contacto del nuevo frontend."""

    class Meta(vat_forms.CiudadanoInscripcionRapidaForm.Meta):
        fields = [
            *vat_forms.CiudadanoInscripcionRapidaForm.Meta.fields,
            "telefono",
            "email",
        ]


class InetSinDniForm(CiudadanoForm):
    """Circuito de identidad del kernel con los campos necesarios para INET."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        allowed = {
            "tipo_registro_identidad",
            "tipo_documento",
            "nombre",
            "apellido",
            "fecha_nacimiento",
            "motivo_sin_dni",
            "motivo_sin_dni_descripcion",
            "telefono",
            "email",
        }
        for name in list(self.fields):
            if name not in allowed:
                del self.fields[name]
        for name in ("nombre", "apellido", "fecha_nacimiento", "telefono"):
            self.fields[name].required = True
        self.fields["tipo_registro_identidad"].initial = Ciudadano.TIPO_REGISTRO_SIN_DNI
        self.fields["tipo_registro_identidad"].disabled = True
        self.fields["tipo_registro_identidad"].widget = forms.HiddenInput()
        self.fields["tipo_documento"].initial = Ciudadano.DOCUMENTO_DNI
        self.fields["tipo_documento"].disabled = True
        self.fields["tipo_documento"].widget = forms.HiddenInput()


FORM_CLASSES = {
    "centros": vat_forms.CentroAltaForm,
    "cursos": vat_forms.CursoForm,
    "comisiones": vat_forms.ComisionCursoForm,
    "horarios": vat_forms.ComisionCursoHorarioForm,
    "contactos": vat_forms.InstitucionContactoForm,
    "ubicaciones": vat_forms.InstitucionUbicacionForm,
    "planes": vat_forms.PlanVersionCurricularForm,
}


def form_data(values):
    """Preservar listas y booleanos con la misma semántica de un POST Django."""
    data = QueryDict(mutable=True)
    for key, value in values.items():
        if isinstance(value, list):
            data.setlist(key, [str(item) for item in value])
        elif value is not None:
            data[key] = (
                "on" if value is True else ("" if value is False else str(value))
            )
    return data


# Adaptador de los siete ModelForms existentes, con alcance explícito por recurso.
# pylint: disable-next=too-many-locals,too-many-branches
def build_form(resource, actor, *, item=None, values=None, initial=None):
    initial = initial.dict() if hasattr(initial, "dict") else dict(initial or {})
    data = form_data(values) if values is not None else None
    context = values if values is not None else initial
    for name in (
        "centro",
        "curso",
        "provincia",
        "municipio",
        "localidad",
        "sector",
        "departamento",
    ):
        if context.get(name) and not str(context[name]).isdigit():
            raise ValidationError({name: ["Seleccioná un elemento válido."]})
    kwargs = {"data": data, "initial": initial}
    if item is not None:
        kwargs["instance"] = item
    if resource == "centros":
        if data is not None and "activo" in values:
            data["activo_present"] = "1"
        province = item.provincia_id if item else get_user_provincia_id(actor)
        kwargs.update(
            actor=actor, hide_provincia=bool(province), provincia_inicial=province
        )
        if province:
            initial["provincia"] = province
            if data is not None:
                data["provincia"] = str(province)
    if resource == "planes":
        kwargs["actor"] = actor
    if resource == "cursos":
        centro_id = item.centro_id if item else (values or initial).get("centro")
        centro = get_object_or_404(centros_for_actor(actor), pk=centro_id)
        kwargs["instance"] = item or models.Curso(centro=centro)
        initial["centro"] = centro.pk
    if resource == "comisiones" and item is None:
        curso = get_object_or_404(
            resource_queryset("cursos", actor), pk=(values or initial).get("curso")
        )
        return vat_forms.ComisionCursoWizardStep1Form(
            data=data, initial=initial, curso=curso
        )
    if resource == "horarios":
        parent_id = (
            item.comision_curso_id
            if item
            else context.get("comision_curso", context.get("comision"))
        )
        if not str(parent_id or "").isdigit():
            raise ValidationError(
                {"comision_curso": ["Seleccioná una comisión válida."]}
            )
        parent = get_object_or_404(resource_queryset("comisiones", actor), pk=parent_id)
        initial["comision_curso"] = parent.pk
    form = FORM_CLASSES[resource](**kwargs)
    if resource == "horarios":
        form.fields["comision_curso"].queryset = resource_queryset(
            "comisiones", actor, management=True
        ).filter(pk=parent.pk)
        form.fields["comision_curso"].disabled = True
    if "centro" in form.fields:
        form.fields["centro"].queryset = centros_for_actor(actor, management=True)
        if item:
            form.fields["centro"].disabled = True
    if resource == "comisiones":
        form.fields["curso"].queryset = resource_queryset(
            "cursos", actor, management=True
        ).filter(centro_id=item.curso.centro_id)
        form.fields["ubicacion"].queryset = models.InstitucionUbicacion.objects.filter(
            centro_id=item.curso.centro_id
        )
    return form


def authorize_create(resource, actor, values):
    codename = {
        "centros": "centro",
        "cursos": "curso",
        "comisiones": "comisioncurso",
        "horarios": "comisionhorario",
        "contactos": "institucioncontacto",
        "ubicaciones": "institucionubicacion",
        "planes": "planversioncurricular",
    }[resource]
    if not user_has_permission_code(actor, f"VAT.add_{codename}"):
        raise PermissionDenied()
    if resource == "centros":
        allowed = can_user_create_centro(actor)
    elif resource == "planes":
        from VAT.services.access_scope import is_vat_provincial, is_vat_sse

        allowed = is_vat_sse(actor) or is_vat_provincial(actor)
    else:
        parent_resource = {"comisiones": "cursos", "horarios": "comisiones"}.get(
            resource, "centros"
        )
        parent_key = {"comisiones": "curso", "horarios": "comision"}.get(
            resource, "centro"
        )
        parent_id = values.get(parent_key)
        if not str(parent_id or "").isdigit():
            raise ValidationError({parent_key: ["Seleccioná un elemento válido."]})
        parent = get_object_or_404(
            resource_queryset(parent_resource, actor), pk=parent_id
        )
        # La autorización de alta corresponde al hijo; el centro delimita el alcance.
        from VAT.services.access_scope import can_user_edit_centro

        centro = (
            parent.centro if parent_resource in ("cursos", "comisiones") else parent
        )
        allowed = can_user_edit_centro(actor, centro)
    if not allowed:
        raise PermissionDenied()


def choice_queryset(field, *, query="", selected=None):
    queryset = field.queryset
    if selected is not None:
        ids = selected if isinstance(selected, list) else [selected]
        queryset = queryset.filter(
            pk__in=[value for value in ids if str(value).isdigit()]
        )
    elif query:
        names = {item.name for item in queryset.model._meta.fields}
        lookup = next(
            (
                name
                for name in ("nombre", "nombre_ubicacion", "username", "codigo")
                if name in names
            ),
            None,
        )
        if lookup:
            queryset = queryset.filter(**{f"{lookup}__icontains": query})
    return queryset.order_by("pk")


def choice_options(field, *, query="", selected=None):
    if isinstance(field, forms.ModelChoiceField):
        queryset = choice_queryset(field, query=query, selected=selected)
        return [
            {"value": str(item.pk), "label": field.label_from_instance(item)}
            for item in queryset[:200]
        ]
    return [
        {"value": str(value), "label": str(label)} for value, label in field.choices
    ]


# La discriminación corresponde a los tipos públicos de campos Django.
# pylint: disable-next=too-many-branches
def serialize_form(form):
    fields = []
    for name, field in form.fields.items():
        if field.widget.is_hidden:
            continue
        value = form[name].value()
        if isinstance(field, forms.BooleanField):
            kind, value = "checkbox", bool(value)
        elif isinstance(
            field, (forms.MultipleChoiceField, forms.ModelMultipleChoiceField)
        ):
            kind = "multiselect"
            value = [str(item) for item in (value or [])]
        elif isinstance(field, forms.ChoiceField):
            kind = "select"
        elif isinstance(field, forms.DateField):
            kind = "date"
        elif isinstance(field, forms.TimeField):
            kind = "time"
        elif isinstance(field, (forms.IntegerField, forms.DecimalField)):
            kind = "number"
        elif isinstance(field, forms.EmailField):
            kind = "email"
        elif isinstance(field.widget, forms.Textarea):
            kind = "textarea"
        else:
            kind = "text"
        if hasattr(value, "isoformat"):
            value = value.isoformat()
        options = []
        remote = isinstance(field, forms.ModelChoiceField)
        if remote:
            options = choice_options(field, selected=value) if value else []
        elif isinstance(field, forms.ChoiceField):
            options = choice_options(field)
        fields.append(
            {
                "name": name,
                "label": str(field.label or name),
                "kind": kind,
                "required": field.required,
                "disabled": field.disabled,
                "help_text": str(field.help_text),
                "value": value,
                "options": options,
                "remote_options": remote,
            }
        )
    return {"fields": fields}


def validate_form(form):
    if not form.is_valid():
        raise ValidationError(
            {
                name: [str(error) for error in errors]
                for name, errors in form.errors.items()
            }
        )
    return form
