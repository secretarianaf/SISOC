from django import forms
from django.core.validators import FileExtensionValidator


class ImportarCSVForm(forms.Form):
    archivo = forms.FileField(
        label="Archivo CSV",
        validators=[FileExtensionValidator(allowed_extensions=["csv"])],
        widget=forms.FileInput(attrs={"accept": ".csv", "class": "form-control"}),
    )
