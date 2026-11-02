"""Form del Formulario de Calidad de los CDI, generado desde el schema."""

from django import forms

from centrodeinfancia.formulario_calidad_schema import (
    CHECKBOX,
    GRILLA,
    MATRIZ_NUMERICA,
    NUMERO,
    PREGUNTAS,
    RADIO,
    SECCIONES,
    campos_respuesta,
)
from centrodeinfancia.models import FormularioCalidadCDI


class FormularioCalidadCDIForm(forms.ModelForm):
    """Todos los campos son opcionales: la obligatoriedad se exige al enviar."""

    class Meta:
        model = FormularioCalidadCDI
        fields = campos_respuesta()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for pregunta in PREGUNTAS:
            self._configurar_pregunta(pregunta)
        for field in self.fields.values():
            field.required = False

    def _configurar_pregunta(self, pregunta):
        for nombre in pregunta.campos:
            field = self.fields[nombre]
            if pregunta.tipo in (RADIO, GRILLA):
                self.fields[nombre] = forms.TypedChoiceField(
                    choices=pregunta.choices,
                    coerce=int,
                    empty_value=None,
                    widget=forms.RadioSelect(attrs={"class": "form-check-input"}),
                )
            elif pregunta.tipo == NUMERO:
                field.widget.attrs.update({"class": "form-control", "min": 0})
            elif pregunta.tipo == MATRIZ_NUMERICA:
                field.widget.attrs.update(
                    {"class": "form-control", "min": 0, "step": "0.01"}
                )
            elif pregunta.tipo == CHECKBOX:
                field.widget.attrs.update({"class": "form-check-input"})
        if pregunta.campo_especificar:
            self.fields[pregunta.campo_especificar].widget.attrs.update(
                {
                    "class": "form-control",
                    "placeholder": pregunta.especificar.etiqueta,
                    "maxlength": 255,
                }
            )

    def _error_de_campos(self, pregunta):
        """Primer error de validación del form en los campos de la pregunta."""
        if not self.is_bound:
            return None
        nombres = list(pregunta.campos)
        if pregunta.campo_especificar:
            nombres.append(pregunta.campo_especificar)
        for nombre in nombres:
            if self.errors.get(nombre):
                return self.errors[nombre][0]
        return None

    def secciones(self, errores=None):
        """Estructura para el template: secciones > preguntas > campos."""
        errores = errores or {}
        resultado = []
        for seccion in SECCIONES:
            preguntas = []
            for pregunta in seccion.preguntas:
                preguntas.append(
                    {
                        "pregunta": pregunta,
                        "campo": (
                            self[pregunta.campos[0]] if not pregunta.filas else None
                        ),
                        "filas": [
                            {
                                "etiqueta": etiqueta,
                                "campo": self[pregunta.nombre_campo(fila)],
                            }
                            for fila, etiqueta in pregunta.filas
                        ],
                        "especificar": (
                            self[pregunta.campo_especificar]
                            if pregunta.campo_especificar
                            else None
                        ),
                        "error": errores.get(pregunta.numero)
                        or self._error_de_campos(pregunta),
                    }
                )
            resultado.append(
                {
                    "seccion": seccion,
                    "preguntas": preguntas,
                    "con_errores": any(item["error"] for item in preguntas),
                }
            )
        return resultado
