"""Formularios para audiencias limitadas a tableros."""

from django import forms
from django.contrib.auth import get_user_model
from dashboard.models import AudienciaTableros


def usuarios_elegibles_para_audiencia():
    # El alta histórica admite cualquier cuenta existente, incluso inactiva.
    return get_user_model().objects.all()


class AudienciaForm(forms.ModelForm):
    class Meta:
        model = AudienciaTableros
        fields = ("nombre",)


class MiembroNombreForm(forms.Form):
    username = forms.CharField(max_length=150, label="Nombre de usuario")


class MiembroIdForm(forms.Form):
    usuario = forms.IntegerField(min_value=1)


class MiembrosLoteForm(forms.Form):
    usuarios = forms.Field(
        widget=forms.SelectMultiple(attrs={"class": "select2"}),
        label="Usuarios",
        help_text="Escriba un nombre de usuario y seleccione uno o más resultados.",
    )

    def clean_usuarios(self):
        valores = self.cleaned_data["usuarios"]
        if len(valores) > 100:
            raise forms.ValidationError("Seleccione hasta 100 usuarios.")
        if any(
            not valor.isascii()
            or not valor.isdecimal()
            or len(valor) > 19
            or not 0 < int(valor) < 2**63
            for valor in valores
        ):
            raise forms.ValidationError("Seleccione usuarios válidos.")

        ids = list(dict.fromkeys(int(valor) for valor in valores))
        usuarios = usuarios_elegibles_para_audiencia().only("username").in_bulk(ids)
        self.fields["usuarios"].widget.choices = [
            (valor, usuarios[int(valor)].username)
            for valor in dict.fromkeys(valores)
            if int(valor) in usuarios
        ]
        if len(usuarios) != len(ids):
            raise forms.ValidationError("Seleccione usuarios válidos.")
        return [usuarios[pk] for pk in ids]
