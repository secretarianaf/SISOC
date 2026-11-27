from django import forms
from django.contrib import admin
from django.contrib.auth.models import Group

from core.admin_base import SisocModelAdmin
from .models import Dashboard, Tablero


@admin.register(Dashboard)
class DashboardAdmin(SisocModelAdmin):
    list_display = ("llave", "cantidad")
    list_filter = ("llave",)
    search_fields = ("llave",)


class TableroAdminForm(forms.ModelForm):
    grupos = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        required=False,
        help_text="Selecciona los grupos con acceso al tablero.",
    )
    permisos_heredados = forms.MultipleChoiceField(
        label="Permisos heredados",
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Desmarca los permisos heredados que quieras revocar.",
    )
    visible_menu_presente = forms.BooleanField(
        required=False, initial=True, widget=forms.HiddenInput
    )

    class Meta:
        model = Tablero
        fields = (
            "nombre",
            "slug",
            "grupo_menu",
            "url",
            "ruta_interna",
            "mensaje_construccion",
            "orden",
            "activo",
            "visible_menu",
            "visible_menu_presente",
            "grupos",
            "permisos_heredados",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["url"].help_text = (
            "Usa la URL embebida del tablero. Para Looker Studio copia el link "
            "desde File > Embed report; la URL compartible normal se bloquea en "
            "iframes."
        )
        permisos = [str(p or "").strip() for p in (self.instance.permisos or [])]
        permisos = [p for p in permisos if p]
        self.fields["grupos"].queryset = Group.objects.exclude(
            name__in=[p for p in permisos if "." in p]
        )
        grupos = self.fields["grupos"].queryset.filter(name__in=permisos)
        nombres_grupos = set(grupos.values_list("name", flat=True))
        heredados = list(dict.fromkeys(p for p in permisos if p not in nombres_grupos))
        self.fields["grupos"].initial = grupos
        self.fields["permisos_heredados"].choices = [(p, p) for p in heredados]
        self.fields["permisos_heredados"].initial = heredados

    def clean_grupo_menu(self):
        return (self.cleaned_data.get("grupo_menu") or "").strip()

    def clean_visible_menu(self):
        if self.add_prefix("visible_menu_presente") not in self.data:
            return self.instance.visible_menu
        return self.cleaned_data["visible_menu"]

    def save(self, commit=True):
        instance = super().save(commit=False)
        grupos = self.cleaned_data.get("grupos")
        instance.permisos = self.cleaned_data["permisos_heredados"] + (
            list(grupos.values_list("name", flat=True)) if grupos else []
        )
        if commit:
            instance.save()
        return instance


@admin.register(Tablero)
class TableroAdmin(SisocModelAdmin):
    form = TableroAdminForm
    list_display = ("nombre", "grupo_menu", "slug", "activo", "visible_menu", "orden")
    list_filter = ("activo", "visible_menu", "grupo_menu")
    ordering = ("orden", "nombre")
    search_fields = ("nombre", "slug", "grupo_menu")
    prepopulated_fields = {"slug": ("nombre",)}
