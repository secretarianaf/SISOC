"""Campos comunes del ABM; los campos y reglas de Espacios están en su dueño."""

from django import forms
from django.contrib.auth.models import Group, Permission, User
from core.models import Provincia
from users.models import Profile


class IdentityFieldsForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label="Contraseña")

    acceso_web = forms.BooleanField(
        required=False,
        initial=True,
        label="Acceso SISOC web",
        help_text=(
            "Los representantes y coordinadores PWA y los relevadores DataCalle "
            "se crean sin acceso web; se puede habilitar después editando el "
            "usuario."
        ),
    )

    acceso_siis = forms.BooleanField(required=False, label="Acceso SIIS")

    dni = forms.CharField(max_length=16, required=False, label="DNI")

    cuil = forms.CharField(max_length=16, required=False, label="CUIL")

    tipo_usuario = forms.ChoiceField(
        choices=Profile.TipoUsuario.choices,
        widget=forms.RadioSelect,
        label="Tipo de usuario",
        help_text=(
            "De dónde viene la persona: interno del organismo, provincial o "
            "externo. Es informativo y no otorga permisos."
        ),
    )

    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "select2"}),
        label="Grupos",
    )

    user_permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.select_related("content_type").order_by(
            "content_type__app_label", "name"
        ),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "select2"}),
        label="Permisos directos",
        help_text=(
            "Permisos adicionales específicos para este usuario, "
            "independientes de sus grupos."
        ),
    )

    es_usuario_provincial = forms.BooleanField(
        required=False,
        label="Es usuario provincial",
    )

    provincia = forms.ModelChoiceField(
        queryset=Provincia.objects.all(),
        required=False,
        widget=forms.Select(attrs={"class": "select2"}),
        label="Provincia",
    )

    territorial_scopes = forms.CharField(
        required=False,
        widget=forms.HiddenInput,
        label="Alcances territoriales",
    )

    rol = forms.CharField(
        max_length=100,
        required=False,
        label="Rol (descriptivo)",
        help_text=(
            "Texto libre para describir el puesto. No define permisos: los "
            "permisos salen de los grupos."
        ),
    )

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "password",
            "dni",
            "acceso_web",
            "acceso_siis",
            "cuil",
            "tipo_usuario",
            "groups",
            "user_permissions",
            "es_usuario_provincial",
            "provincia",
            "territorial_scopes",
            "last_name",
            "first_name",
            "rol",
        ]
