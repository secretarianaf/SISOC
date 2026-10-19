"""Formularios de autenticacion y datos propios, independientes del negocio."""

from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from core.validators import solo_digitos, validate_cuit
from users.models import Profile
from users.profile_utils import get_profile_or_none


class UsernameEmailPasswordResetForm(PasswordResetForm):
    username = forms.CharField(label="Usuario", max_length=150, required=True)

    def get_users(self, email):
        username = (self.cleaned_data.get("username") or "").strip()
        try:
            user = User.objects.get(username=username, is_active=True)
        except User.DoesNotExist:
            return ()

        email_matches = (user.email or "").casefold() == (email or "").casefold()
        if not email_matches:
            return ()
        return (user,)


class BackofficeAuthenticationForm(AuthenticationForm):
    """Exige la habilitación explícita de SISOC web."""

    error_messages = {
        **AuthenticationForm.error_messages,
        "invalid_login": "Usuario o contraseña inválidos.",
    }

    def __init__(self, *args, request=None, **kwargs):
        super().__init__(request=request, *args, **kwargs)
        self.fields[User.USERNAME_FIELD].error_messages[
            "required"
        ] = "Este campo es obligatorio."
        self.fields["password"].error_messages[
            "required"
        ] = "Este campo es obligatorio."

    def clean(self):
        username_field_name = User.USERNAME_FIELD
        username = self.data.get(username_field_name) or ""
        password = self.data.get("password") or ""
        mutable_data = self.data.copy()
        required_message = "Este campo es obligatorio."
        trimmed_username = username.strip()

        mutable_data[username_field_name] = trimmed_username
        self.data = mutable_data

        if not trimmed_username and username_field_name not in self.errors:
            self.add_error(username_field_name, required_message)
        if not password.strip() and "password" not in self.errors:
            self.add_error("password", required_message)
        if self.errors:
            self.data["password"] = ""
            return self.cleaned_data

        try:
            return super().clean()
        except forms.ValidationError:
            self.data["password"] = ""
            raise

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        profile = get_profile_or_none(user)
        if not getattr(profile, "acceso_web", False):
            raise forms.ValidationError(
                "Este usuario no tiene acceso SISOC web habilitado.",
                code="web_access_disabled",
            )
        expires_at = getattr(profile, "initial_password_expires_at", None)
        if (
            getattr(profile, "must_change_password", False)
            and expires_at
            and expires_at <= timezone.now()
        ):
            raise forms.ValidationError(
                "La contraseña inicial expiró. Solicite un reinicio a un administrador.",
                code="initial_password_expired",
            )


class UserLoginForm(BackofficeAuthenticationForm):
    """Compatibilidad para configuraciones existentes."""


class MiCuentaForm(forms.ModelForm):
    """Edición de los datos personales del propio usuario.

    Se comparte entre la vista persistente "Mi cuenta" y la confirmación
    obligatoria de primer ingreso, para que ambas apliquen exactamente la
    misma validación y el mismo guardado.

    A diferencia de ``CustomUserChangeForm``, acá no se exponen grupos,
    permisos, alcances territoriales ni delegación: el usuario solo edita sus
    propios datos identificatorios. ``tipo_usuario`` y ``rol`` quedan fuera a
    pedido de UX/UI: son datos de administración y el usuario final no los
    toca.

    Todos los campos son obligatorios salvo ``correo_institucional``.
    """

    dni = forms.CharField(
        max_length=16,
        label="DNI",
        help_text="Solo números, sin puntos.",
        error_messages={"required": "Ingrese su DNI."},
    )
    cuil = forms.CharField(
        max_length=16,
        label="CUIL",
        help_text="11 dígitos, con o sin guiones.",
        error_messages={"required": "Ingrese su CUIL."},
    )
    correo_institucional = forms.EmailField(
        required=False,
        label="Correo institucional",
        help_text="Opcional.",
    )

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]
        labels = {
            "first_name": "Nombre",
            "last_name": "Apellido",
            "email": "Mail",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for nombre in ("first_name", "last_name", "email"):
            self.fields[nombre].required = True
        # Hay usuarios históricos sin perfil; el form igual debe poder abrirse.
        profile = get_profile_or_none(self.instance)
        if profile:
            self.fields["dni"].initial = profile.dni
            self.fields["cuil"].initial = profile.cuil
            self.fields["correo_institucional"].initial = profile.correo_institucional

    def clean_dni(self):
        dni = solo_digitos(self.cleaned_data.get("dni"))
        if len(dni) < 6:
            raise forms.ValidationError("Ingrese un DNI válido (solo números).")
        return dni

    def clean_cuil(self):
        return validate_cuit((self.cleaned_data.get("cuil") or "").strip())

    def clean_email(self):
        # El mail es obligatorio en este formulario pero sigue sin ser único:
        # la unicidad vive en username.
        return (self.cleaned_data.get("email") or "").strip()

    def save(self, commit=True):
        if not commit:
            raise ValueError("MiCuentaForm requiere commit=True para ser atómico.")
        with transaction.atomic():
            user = super().save(commit=True)
            profile, _ = Profile.objects.get_or_create(user=user)
            profile.dni = self.cleaned_data["dni"]
            profile.cuil = self.cleaned_data["cuil"]
            profile.correo_institucional = self.cleaned_data["correo_institucional"]
            profile.needs_profile_confirmation = False
            profile.datos_confirmados_at = timezone.now()
            profile.save(
                update_fields=[
                    "dni",
                    "cuil",
                    "correo_institucional",
                    "needs_profile_confirmation",
                    "datos_confirmados_at",
                ]
            )
        return user
