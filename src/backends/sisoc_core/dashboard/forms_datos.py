"""Campos operativos del catálogo mantenidos por el equipo de Datos."""

from django import forms

from dashboard.models import Tablero


class TableroOperativoForm(forms.ModelForm):
    class Meta:
        model = Tablero
        fields = ("nombre", "activo", "visible_menu")
