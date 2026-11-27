"""Validación de asignaciones individuales disponibles."""

from django import forms

from core.models import Provincia
from dashboard.models import ConcesionTablero, Tablero
from dashboard.services.gestion_concesiones import agregar_lote_concesiones


class AsignacionIndividualForm(forms.Form):
    tablero = forms.ModelChoiceField(queryset=Tablero.objects.all())
    tipo = forms.ChoiceField(
        choices=(
            (ConcesionTablero.Tipo.NACIONAL, "Nacional"),
            (ConcesionTablero.Tipo.PROVINCIA, "Provincial"),
        ),
        label="Alcance",
    )
    provincias = forms.ModelMultipleChoiceField(
        queryset=Provincia.objects.all(), required=False
    )

    def clean(self):
        datos = super().clean()
        tipo = datos.get("tipo")
        provincias = datos.get("provincias")
        if tipo == ConcesionTablero.Tipo.PROVINCIA and not provincias:
            self.add_error("provincias", "Seleccione al menos una provincia.")
        if tipo == ConcesionTablero.Tipo.NACIONAL and provincias:
            self.add_error("provincias", "El alcance nacional no admite provincias.")
        return datos


class RevocarIndividualForm(forms.Form):
    tablero = forms.ModelChoiceField(queryset=Tablero.objects.all())
    concesion = forms.IntegerField(min_value=1)


class AsignacionLoteForm(forms.Form):
    tableros = forms.ModelMultipleChoiceField(
        queryset=Tablero.objects.order_by("nombre", "pk"),
        widget=forms.SelectMultiple(attrs={"class": "select2"}),
    )
    tipo = forms.ChoiceField(choices=ConcesionTablero.Tipo.choices, label="Alcance")
    provincias = forms.ModelMultipleChoiceField(
        queryset=Provincia.objects.order_by("nombre", "pk"),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "select2"}),
    )
    cdis = forms.TypedMultipleChoiceField(
        label="CDI",
        coerce=int,
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "select2"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.is_bound:
            valores = self["cdis"].value() or []
            self.fields["cdis"].choices = [
                (valor, f"CDI {valor}")
                for valor in dict.fromkeys(valores[:100])
                if valor.isascii() and valor.isdecimal() and len(valor) <= 19
            ]

    def clean(self):
        datos = super().clean()
        for nombre in ("tableros", "provincias", "cdis"):
            valores = (
                self.fields[nombre].widget.value_from_datadict(
                    self.data, self.files, self.add_prefix(nombre)
                )
                or []
            )
            if len(valores) > 100 or len(set(valores)) != len(valores):
                self.add_error(nombre, "Seleccione hasta 100 opciones sin repetir.")
        tipo = datos.get("tipo")
        for campo, alcance in (
            ("provincias", ConcesionTablero.Tipo.PROVINCIA),
            ("cdis", ConcesionTablero.Tipo.CDI),
        ):
            if campo not in datos or not tipo:
                continue
            if tipo == alcance and not datos[campo]:
                self.add_error(campo, "Seleccione al menos una opción.")
            elif tipo != alcance and datos[campo]:
                self.add_error(campo, "Este alcance no admite esta selección.")
        return datos

    def guardar(self, request, **sujeto):
        agregar_lote_concesiones(request, self.cleaned_data, **sujeto)
