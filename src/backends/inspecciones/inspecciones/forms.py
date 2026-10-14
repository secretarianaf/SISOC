"""Formularios del panel de Inspecciones escolares (backoffice)."""

import re

from django import forms
from django.contrib.auth import get_user_model
from django.core.validators import FileExtensionValidator

from core.models import Localidad, Provincia
from inspecciones.models import Escuela
from inspecciones.services.asignaciones import (
    ESTADOS,
    ESTADOS_ACTA,
    es_inspector,
    inspectores,
)
from inspecciones.services.catalogo import escuela_con_cueanexo
from inspecciones.services.formato import hoy
from inspecciones.services.planillas import MAX_BYTES_ARCHIVO

CUEANEXO = re.compile(r"^\d{9}$")
# Código postal viejo (1754) o CPA (B1754ABC).
CODIGO_POSTAL = re.compile(r"^[A-Z]?\d{4}[A-Z]{0,3}$")


class ImportarArchivoForm(forms.Form):
    archivo = forms.FileField(
        label="Archivo Excel o CSV",
        validators=[FileExtensionValidator(allowed_extensions=["xlsx", "csv"])],
        widget=forms.FileInput(attrs={"accept": ".xlsx,.csv", "class": "form-control"}),
    )

    def clean_archivo(self):
        archivo = self.cleaned_data["archivo"]
        if archivo.size > MAX_BYTES_ARCHIVO:
            raise forms.ValidationError("El archivo no puede superar los 25 MB.")
        return archivo


def _provincias():
    return Provincia.objects.order_by("nombre")


class EscuelaForm(forms.Form):
    """Alta y edición de una escuela (mismo formulario, en un modal)."""

    provincia = forms.ModelChoiceField(
        queryset=Provincia.objects.none(), empty_label="Elegí la provincia"
    )
    localidad = forms.ModelChoiceField(
        queryset=Localidad.objects.select_related("municipio"),
        error_messages={"invalid_choice": "Elegí una localidad de la lista."},
    )
    cueanexo = forms.CharField(label="Cueanexo", max_length=9)
    nombre = forms.CharField(max_length=255)
    domicilio = forms.CharField(max_length=255)
    cp = forms.CharField(label="C. P.", max_length=20, required=False)
    telefono = forms.CharField(label="Teléfono", max_length=255, required=False)
    mail = forms.EmailField(
        max_length=255,
        required=False,
        error_messages={"invalid": "Ingresá un mail válido."},
    )

    def __init__(self, *args, escuela=None, **kwargs):
        self.escuela = escuela or Escuela()
        self.escuela_duplicada = None
        if escuela is not None and "initial" not in kwargs:
            kwargs["initial"] = {
                "provincia": escuela.provincia_id,
                "localidad": escuela.localidad_vinculada_id,
                "cueanexo": escuela.cueanexo,
                "nombre": escuela.nombre,
                "domicilio": escuela.domicilio,
                "cp": escuela.cp,
                "telefono": escuela.telefono,
                "mail": escuela.mail,
            }
        super().__init__(*args, **kwargs)
        self.fields["provincia"].queryset = _provincias()

    def clean_cueanexo(self):
        cueanexo = re.sub(r"\s+", "", self.cleaned_data["cueanexo"])
        if not CUEANEXO.match(cueanexo):
            raise forms.ValidationError(
                "El Cueanexo lleva exactamente 9 dígitos (con los ceros iniciales)."
            )
        duplicada = escuela_con_cueanexo(cueanexo, excluir_id=self.escuela.pk)
        if duplicada is not None:
            self.escuela_duplicada = duplicada
            localidad = duplicada.localidad or "sin localidad"
            raise forms.ValidationError(f"Ya existe: {duplicada.nombre} ({localidad}).")
        return cueanexo

    def clean_cp(self):
        cp = re.sub(r"\s+", "", self.cleaned_data["cp"]).upper()
        if cp and not CODIGO_POSTAL.match(cp):
            raise forms.ValidationError("C. P. inválido: por ejemplo 1754 o B1754ABC.")
        return cp

    def clean_nombre(self):
        return re.sub(r"\s+", " ", self.cleaned_data["nombre"]).strip()

    def clean_domicilio(self):
        return re.sub(r"\s+", " ", self.cleaned_data["domicilio"]).strip()

    def clean(self):
        datos = super().clean()
        provincia, localidad = datos.get("provincia"), datos.get("localidad")
        if provincia and localidad:
            provincia_localidad = getattr(localidad.municipio, "provincia_id", None)
            if provincia_localidad != provincia.pk:
                self.add_error("localidad", "La localidad no es de esa provincia.")
        return datos


class _UsuarioInspectorField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.get_full_name() or obj.get_username()


class AsignacionForm(forms.Form):
    fecha = forms.DateField(
        label="Jornada",
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )
    inspector = _UsuarioInspectorField(
        queryset=get_user_model().objects.none(),
        error_messages={"invalid_choice": "Elegí un inspector de la lista."},
    )
    escuela = forms.ModelChoiceField(
        queryset=Escuela.objects.all(),
        error_messages={"invalid_choice": "Elegí una escuela de la lista."},
    )

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("initial", {}).setdefault("fecha", hoy())
        super().__init__(*args, **kwargs)
        self.fields["inspector"].queryset = inspectores()

    def clean_inspector(self):
        inspector = self.cleaned_data["inspector"]
        if not es_inspector(inspector):
            raise forms.ValidationError(
                "El usuario no es inspector de Inspecciones escolares."
            )
        return inspector


class _FiltroForm(forms.Form):
    """Filtros por GET: un valor inválido se ignora, no rompe el listado."""

    def valor(self, campo):
        if not self.is_bound:
            return None
        if not hasattr(self, "cleaned_data"):
            self.is_valid()
        if campo in self.errors:
            return None
        return self.cleaned_data.get(campo)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "provincia" in self.fields:
            self.fields["provincia"].queryset = _provincias()


def _id_opcional(label):
    return forms.IntegerField(label=label, required=False, min_value=1)


def _provincia_opcional():
    return forms.ModelChoiceField(
        queryset=Provincia.objects.none(),
        required=False,
        empty_label="Todas las provincias",
    )


class EscuelasFiltroForm(_FiltroForm):
    q = forms.CharField(label="Buscar", required=False, max_length=100)
    provincia = _provincia_opcional()
    localidad = _id_opcional("Localidad")
    a_revisar = forms.BooleanField(required=False)


class AsignacionesFiltroForm(_FiltroForm):
    fecha = forms.DateField(required=False)
    inspector = _id_opcional("Inspector")
    provincia = _provincia_opcional()
    estado = forms.ChoiceField(
        choices=[("", "Todos los estados"), *ESTADOS], required=False
    )
    estado_acta = forms.ChoiceField(
        choices=[("", "Todas las actas"), *ESTADOS_ACTA], required=False
    )


class ActasFiltroForm(_FiltroForm):
    fecha = forms.DateField(required=False)
    inspector = _id_opcional("Inspector")
    provincia = _provincia_opcional()
    estado = forms.ChoiceField(
        choices=[("", "Todas las actas"), *ESTADOS_ACTA], required=False
    )
