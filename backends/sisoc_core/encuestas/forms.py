from django import forms

from .models import Encuesta


class RechazoEncuestaForm(forms.Form):
    motivo = forms.CharField(
        label="Motivo del rechazo",
        max_length=2000,
        strip=True,
        error_messages={"required": "Indicá qué debe corregir el gestor."},
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 5,
                "placeholder": "Explicá qué debe corregirse antes de volver a solicitar la publicación.",
                "aria-describedby": "motivo-rechazo-ayuda motivo-rechazo-error",
            }
        ),
    )


class EncuestaForm(forms.ModelForm):
    modalidad = forms.ChoiceField(
        choices=[
            ("obligatoria", "Obligatoria"),
            ("opcional", "Opcional"),
            ("postergable", "Postergable"),
        ],
        widget=forms.Select(attrs={"class": "form-select"}),
        initial="postergable",
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.initial["modalidad"] = self.instance.modalidad

    def clean(self):
        cleaned = super().clean()
        modalidad = cleaned.pop("modalidad", None)
        if not modalidad:
            modalidad = (
                "obligatoria"
                if cleaned.get("es_obligatoria")
                else "opcional" if cleaned.get("es_opcional") else "postergable"
            )
        cleaned["es_obligatoria"] = modalidad == "obligatoria"
        cleaned["es_opcional"] = modalidad == "opcional"
        if modalidad != "postergable":
            cleaned["intervalo_recordatorio_dias"] = None
        return cleaned

    class Meta:
        model = Encuesta
        fields = [
            "titulo",
            "descripcion",
            "es_anonima",
            "es_obligatoria",
            "es_opcional",
            "intervalo_recordatorio_dias",
            "es_recurrente",
            "intervalo_recurrencia_dias",
            "duracion_ronda_dias",
        ]
        widgets = {
            "titulo": forms.TextInput(attrs={"class": "form-control"}),
            "descripcion": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "es_anonima": forms.CheckboxInput(
                attrs={"class": "form-check-input", "role": "switch"}
            ),
            "es_obligatoria": forms.CheckboxInput(
                attrs={"class": "form-check-input", "role": "switch"}
            ),
            "es_recurrente": forms.CheckboxInput(
                attrs={"class": "form-check-input", "role": "switch"}
            ),
            "intervalo_recordatorio_dias": forms.NumberInput(
                attrs={"class": "form-control"}
            ),
            "intervalo_recurrencia_dias": forms.NumberInput(
                attrs={"class": "form-control"}
            ),
            "duracion_ronda_dias": forms.NumberInput(attrs={"class": "form-control"}),
        }
