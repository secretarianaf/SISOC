import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django import forms

from comedores.models import ComedorDatosConvenioPnud
from comedores.utils import (
    is_abordaje_comunitario_linea_secos_program,
    is_abordaje_comunitario_linea_tradicional_program,
)

PRESTACIONES_APROBADAS_DIAS = (
    "lunes",
    "martes",
    "miercoles",
    "jueves",
    "viernes",
    "sabado",
    "domingo",
)
PRESTACIONES_APROBADAS_COMIDAS = (
    "desayuno",
    "almuerzo",
    "merienda",
    "merienda_reforzada",
    "cena",
)
PRESTACIONES_APROBADAS_FIELDS = [
    f"aprobadas_{comida}_{dia}"
    for dia in PRESTACIONES_APROBADAS_DIAS
    for comida in PRESTACIONES_APROBADAS_COMIDAS
]


SOLO_NUMEROS_ATTRS = {
    "class": "form-control",
    "min": "0",
    "step": "1",
    "inputmode": "numeric",
    "data-solo-numeros": "true",
}


class MontoConvenioWidget(forms.TextInput):
    def format_value(self, value):
        if value in (None, ""):
            return ""
        if isinstance(value, str):
            return value
        try:
            entero = Decimal(value).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
            return format(entero, ",.0f").replace(",", ".")
        except (InvalidOperation, ValueError, TypeError):
            return value


class MontoConvenioField(forms.DecimalField):
    def to_python(self, value):
        if isinstance(value, str) and value.strip():
            value = value.strip().lstrip("$").strip()
            if not re.fullmatch(r"-?(?:[0-9]+|[0-9]{1,3}(?:\.[0-9]{3})+)", value):
                raise forms.ValidationError(
                    "Ingresá un monto sin decimales, por ejemplo 100.000.000."
                )
            value = value.replace(".", "")
        return super().to_python(value)


class ComedorDatosConvenioPnudForm(forms.ModelForm):
    MONTOS_FIELDS = (
        "monto_convenio_prestaciones_alimentarias",
        "monto_convenio_siph",
    )
    PRESTACIONES_DIARIAS_FIELDS = [
        "prestaciones_financiadas_diarias_desayuno",
        "prestaciones_financiadas_diarias_almuerzo",
        "prestaciones_financiadas_diarias_merienda",
        "prestaciones_financiadas_diarias_merienda_reforzada",
        "prestaciones_financiadas_diarias_cena",
    ]
    ENTEROS_FIELDS = (
        "prestaciones_financiadas_mensuales",
        *PRESTACIONES_DIARIAS_FIELDS,
        "personas_conveniadas",
        "personas_identidad_reservada",
        "personas_declaradas_siph",
        "cantidad_modulos",
    )

    def __init__(self, *args, comedor=None, **kwargs):
        super().__init__(*args, **kwargs)
        for name in self.MONTOS_FIELDS:
            original = self.fields[name]
            self.fields[name] = MontoConvenioField(
                label=original.label,
                required=original.required,
                max_digits=original.max_digits,
                decimal_places=original.decimal_places,
                widget=MontoConvenioWidget(
                    attrs={
                        "class": "form-control",
                        "inputmode": "numeric",
                        "data-monto-entero": "true",
                    }
                ),
            )
        for name in self.ENTEROS_FIELDS:
            self.fields[name].widget = forms.NumberInput(attrs=SOLO_NUMEROS_ATTRS)
        self.fields["nro_convenio"].widget.attrs["class"] = "form-control"
        if is_abordaje_comunitario_linea_secos_program(comedor):
            for field_name in [
                "prestaciones_financiadas_mensuales",
                *PRESTACIONES_APROBADAS_FIELDS,
                *self.PRESTACIONES_DIARIAS_FIELDS,
            ]:
                self.fields.pop(field_name, None)

        elif is_abordaje_comunitario_linea_tradicional_program(comedor):
            self.fields.pop("prestaciones_financiadas_mensuales", None)
            self.fields.pop("cantidad_modulos", None)
        else:
            for field_name in [
                # #2917: identidad reservada solo aplica a Abordaje Comunitario.
                "personas_identidad_reservada",
                *self.PRESTACIONES_DIARIAS_FIELDS,
                *[
                    name
                    for name in PRESTACIONES_APROBADAS_FIELDS
                    if "merienda_reforzada" in name
                ],
            ]:
                self.fields.pop(field_name, None)

    def clean(self):
        cleaned = super().clean()
        # Mostrar pesos enteros no debe borrar centavos históricos al guardar
        # otro campo del convenio sin modificar su monto.
        for name in self.MONTOS_FIELDS:
            inicial = self.initial.get(name)
            if name in cleaned and inicial is not None:
                visible = self.fields[name].widget.format_value(inicial)
                if cleaned[name] == self.fields[name].to_python(visible):
                    cleaned[name] = inicial
        if "personas_identidad_reservada" in self.fields:
            self._clean_identidad_reservada(cleaned)
        return cleaned

    def _clean_identidad_reservada(self, cleaned):
        """#2917: vacío equivale a 0 y no puede superar a las conveniadas."""
        if "personas_identidad_reservada" in self.errors:
            return
        reservadas = cleaned.get("personas_identidad_reservada") or 0
        cleaned["personas_identidad_reservada"] = reservadas
        conveniadas = cleaned.get("personas_conveniadas")
        if conveniadas is not None and reservadas > conveniadas:
            self.add_error(
                "personas_identidad_reservada",
                "No puede superar la cantidad de Personas Conveniadas "
                f"({conveniadas}).",
            )

    class Meta:
        model = ComedorDatosConvenioPnud
        # Orden de carga pedido en #2843; la vista de edición y el legajo lo siguen.
        fields = [
            "nro_convenio",
            "monto_convenio_prestaciones_alimentarias",
            "monto_convenio_siph",
            "prestaciones_financiadas_mensuales",
            "prestaciones_financiadas_diarias_desayuno",
            "prestaciones_financiadas_diarias_almuerzo",
            "prestaciones_financiadas_diarias_merienda",
            "prestaciones_financiadas_diarias_merienda_reforzada",
            "prestaciones_financiadas_diarias_cena",
            "personas_conveniadas",
            "personas_identidad_reservada",
            "cantidad_modulos",
            "personas_declaradas_siph",
        ] + PRESTACIONES_APROBADAS_FIELDS
        labels = {
            "nro_convenio": "Número de Convenio",
            "monto_convenio_prestaciones_alimentarias": "Monto total del Convenio por Espacio - Prestaciones Alimentarias",
            "monto_convenio_siph": "Monto total del Convenio por Espacio - Servicio Integral de Promoción Humana",
            "prestaciones_financiadas_mensuales": "Prestaciones financiadas mensuales",
            "prestaciones_financiadas_diarias_desayuno": "Prestaciones Financiadas Diarias - Desayuno",
            "prestaciones_financiadas_diarias_almuerzo": "Prestaciones Financiadas Diarias - Almuerzo",
            "prestaciones_financiadas_diarias_merienda": "Prestaciones Financiadas Diarias - Merienda",
            "prestaciones_financiadas_diarias_merienda_reforzada": "Prestaciones Financiadas Diarias - Merienda Reforzada",
            "prestaciones_financiadas_diarias_cena": "Prestaciones Financiadas Diarias - Cena",
            "personas_conveniadas": "Personas Conveniadas",
            "personas_identidad_reservada": "Cantidad de personas con identidad reservada",
            "cantidad_modulos": "Cantidad de Módulos Mensuales",
            "personas_declaradas_siph": "Total de personas declaradas en Servicio Integral de Promoción Humana",
        }
        widgets = {
            field_name: forms.NumberInput(
                attrs={**SOLO_NUMEROS_ATTRS, "class": "form-control form-control-sm"}
            )
            for field_name in PRESTACIONES_APROBADAS_FIELDS
        }
