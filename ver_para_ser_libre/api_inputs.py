"""Contratos de escritura derivados de los formularios, sin otra regla de negocio."""

from django import forms
from rest_framework import serializers
from drf_spectacular.utils import PolymorphicProxySerializer

from ver_para_ser_libre.api_serializers import ReadOnlySerializer
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


def input_field(field):
    """Los ModelForms siguen validando; este mapeo describe el transporte."""
    options = {"required": field.required}
    if isinstance(field, forms.ModelMultipleChoiceField):
        result = serializers.ListField(child=serializers.IntegerField(), **options)
    elif isinstance(field, forms.ModelChoiceField):
        result = serializers.IntegerField(allow_null=not field.required, **options)
    elif isinstance(field, forms.FileField):
        result = serializers.FileField(**options)
    elif isinstance(field, forms.BooleanField):
        result = serializers.BooleanField(**options)
    elif isinstance(field, forms.DecimalField):
        result = serializers.DecimalField(
            max_digits=field.max_digits or 12,
            decimal_places=field.decimal_places or 2,
            allow_null=not field.required,
            **options,
        )
    elif isinstance(field, forms.IntegerField):
        result = serializers.IntegerField(allow_null=not field.required, **options)
    elif isinstance(field, forms.DateField):
        result = serializers.DateField(allow_null=not field.required, **options)
    elif isinstance(field, forms.TimeField):
        result = serializers.TimeField(allow_null=not field.required, **options)
    else:
        result = serializers.CharField(allow_blank=not field.required, **options)
    return result


def form_input(name, fields, **extra):
    return type(
        name,
        (ReadOnlySerializer,),
        {
            **{key: input_field(field) for key, field in fields.items()},
            **extra,
            "__module__": __name__,
        },
    )


ItinerarioInput = form_input(
    "ItinerarioInput", getattr(ItinerarioVPSLForm, "base_fields")
)
SedeInput = form_input(
    "SedeInput",
    {
        **getattr(SedeCreateVPSLForm, "base_fields"),
        **ChecklistSedeVPSLForm(required=False).fields,
    },
)
JornadaInput = form_input(
    "JornadaInput",
    getattr(JornadaVPSLForm, "base_fields"),
    renaper_estado=serializers.CharField(required=False, allow_blank=True),
    referente_nombre_renaper=serializers.CharField(required=False, allow_blank=True),
    referente_apellido_renaper=serializers.CharField(required=False, allow_blank=True),
)
RegistroInput = form_input(
    "RegistroInput",
    getattr(RegistroNominalVPSLForm, "base_fields"),
    renaper_estado=serializers.CharField(required=False, allow_blank=True),
    guardar_continuar=serializers.CharField(required=False),
)
ChecklistInput = form_input("ChecklistInput", ChecklistSedeVPSLForm().fields)
LaboratorioInput = form_input(
    "LaboratorioInput", getattr(CasoLaboratorioVPSLForm, "base_fields")
)
CierreInput = form_input("CierreInput", getattr(CierreDiarioVPSLForm, "base_fields"))

SubsanacionInput = form_input(
    "SubsanacionInput", {"carta_archivo": forms.FileField(required=True)}
)
SedeUpdateInput = form_input(
    "SedeUpdateInput", getattr(SedeUpdateVPSLForm, "base_fields")
)

# The requiredness for an existing record is also returned by GET form metadata.
ItinerarioEditInput = form_input(
    "ItinerarioEditInput", getattr(ItinerarioVPSLForm, "base_fields")
)
RegistroHistoricalInput = form_input(
    "RegistroHistoricalInput", getattr(RegistroNominalVPSLForm, "base_fields")
)
JornadaHistoricalInput = form_input(
    "JornadaHistoricalInput", getattr(JornadaVPSLForm, "base_fields")
)
for input_class, optional_names in (
    (ItinerarioEditInput, tuple(getattr(ItinerarioVPSLForm, "base_fields"))),
    (RegistroHistoricalInput, ("graduacion_izquierda", "graduacion_derecha")),
    (JornadaHistoricalInput, ("localidad", "direccion", "ubicacion_url")),
):
    for optional_name in optional_names:
        getattr(input_class, "_declared_fields")[optional_name].required = False

FORM_INPUT = PolymorphicProxySerializer(
    component_name="VpslFormInput",
    serializers=[
        ItinerarioInput,
        SedeInput,
        JornadaInput,
        RegistroInput,
        ChecklistInput,
        LaboratorioInput,
        CierreInput,
        SubsanacionInput,
        ItinerarioEditInput,
        SedeUpdateInput,
        RegistroHistoricalInput,
        JornadaHistoricalInput,
    ],
    resource_type_field_name=None,
)


class ActionInput(ReadOnlySerializer):
    accion_evaluacion = serializers.ChoiceField(
        choices=["aprobar", "subsanar", "rechazar"], required=False
    )
    carta_archivo_estado = serializers.CharField(required=False)
    carta_referencia_estado = serializers.CharField(required=False)
    subsanacion_observaciones = serializers.CharField(required=False, allow_blank=True)
    casos = serializers.ListField(child=serializers.IntegerField(), required=False)
    fecha = serializers.DateField(required=False)
    responsable = serializers.CharField(required=False)
