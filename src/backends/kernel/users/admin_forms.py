"""ABM de identidad sin modelos ni consultas de Comedores."""

from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from users.form_sections import (
    DelegationScopeMixin,
    InspeccionesEscolaresFormMixin,
    RelevadorCalleFormMixin,
    TerritorialScopeFormMixin,
)
from users.identity_fields import IdentityFieldsForm
from users.admin_operations import (
    normalizar_controles_vaciados,
    operacion_requiere_espacios,
)
from users.models import Profile
from users.profile_utils import get_profile_or_none
from users.services_datacalle import validar_alcance_coordinador
from users.territorial_scope import sync_profile_territorial_scopes


class IdentityAdminForm(
    TerritorialScopeFormMixin,
    RelevadorCalleFormMixin,
    InspeccionesEscolaresFormMixin,
    DelegationScopeMixin,
    IdentityFieldsForm,
):
    """Usa las mismas reglas de identidad; nunca sincroniza accesos de Espacios."""

    def __init__(self, *args, **kwargs):
        self.actor = kwargs.pop("actor", None)
        super().__init__(*args, **kwargs)
        if self.is_bound:
            self.data = normalizar_controles_vaciados(self.data)
        self.generated_password = None
        self.password_was_auto_generated = False
        self.fields["email"].required = False
        self.fields["password"].required = not bool(self.instance.pk)
        self._setup_relevador_calle_fields()
        self._setup_inspecciones_escolares_fields()
        self._setup_delegation_fields()
        self._scope_assignable_fields_for_actor()
        profile = get_profile_or_none(self.instance) if self.instance.pk else None
        self._setup_territorial_scope_fields(profile)
        self._init_relevador_calle_fields(profile)
        self._init_inspecciones_escolares_fields(profile)
        if profile:
            for name in (
                "acceso_web",
                "acceso_siis",
                "dni",
                "cuil",
                "tipo_usuario",
                "es_usuario_provincial",
                "provincia",
                "rol",
            ):
                self.fields[name].initial = getattr(profile, name)
            self._init_delegation_fields(profile)
        self.fields["password"].initial = ""
        self.initial["password"] = ""
        self._apply_section_restrictions()
        self.can_manage_mobile_access = False
        self.can_manage_territorial_comedor = False
        self.can_manage_technical_teams = False
        # En edición, un campo omitido no revoca estado. Django ignora además
        # valores manipulados de las secciones que el actor no puede gestionar.
        if self.is_bound and self.instance.pk:
            for name, field in self.fields.items():
                if name not in self.data and name != "password":
                    field.disabled = True
                    # Perfiles históricos pueden tener valores vacíos en campos
                    # hoy obligatorios. Omitirlos no exige repararlos de rebote.
                    field.required = False

    def clean(self):
        cleaned = super().clean()
        if operacion_requiere_espacios(
            self.data, self.instance if self.instance.pk else None
        ):
            raise ValidationError(
                "La operación requiere validar Espacios comunitarios. Recargá el formulario."
            )
        cleaned["email"] = (cleaned.get("email") or "").strip()
        cleaned = self._clean_territorial_scope_fields(cleaned)
        self._validate_selected_within_allowed(cleaned)
        cleaned = self._clean_relevador_calle_fields(cleaned)
        cleaned = self._clean_inspecciones_escolares_fields(cleaned)
        cleaned = self._validar_provincia_unica_coordinador(cleaned)
        if not self.instance.pk and (
            cleaned.get("datacalle_rol") == Profile.DataCalleRol.ENTREVISTADOR
            or (
                cleaned.get("es_inspector_escolar")
                and cleaned.get("inspecciones_rol") == Profile.InspeccionesRol.INSPECTOR
            )
        ):
            cleaned["acceso_web"] = False
        return self._validate_simepi_egp_scope(cleaned)

    def save(self, commit=True):
        if not commit:
            raise ValueError(
                "El ABM de identidad requiere commit=True para ser atómico."
            )
        with transaction.atomic():
            creating = not bool(self.instance.pk)
            if not creating:
                current = User.objects.select_for_update().get(pk=self.instance.pk)
                if operacion_requiere_espacios(self.data, current):
                    raise ValidationError(
                        "Las asignaciones cambiaron. Recargá el formulario antes de guardar."
                    )
            user = super().save(commit=False)
            if not creating and not self.cleaned_data.get("password"):
                user.password = current.password
            changed = set(self.changed_data)
            self._save_identity(user, creating, changed)
            self._save_permissions(user, creating, changed)
            self._save_profile(user, creating, changed)
            self._clear_permission_caches(user)
            return user

    def _save_identity(self, user, creating, changed):
        password = self.cleaned_data.get("password")
        if password:
            user.set_password(password)
        if creating:
            if (
                self.cleaned_data.get("datacalle_rol")
                == Profile.DataCalleRol.ENTREVISTADOR
                or self._es_inspector_solo_app()
            ):
                user.is_staff = False
            user.save()
            return
        fields = changed.intersection({"username", "first_name", "last_name", "email"})
        if password:
            fields.add("password")
        if fields:
            user.save(update_fields=fields)

    def _save_permissions(self, user, creating, changed):
        if creating or changed.intersection({"groups", "user_permissions"}):
            for name in ("groups", "user_permissions"):
                if not creating and name not in changed:
                    self.cleaned_data[name] = getattr(user, name).all()
            self._aplicar_grupos_y_permisos(user)
        if creating or changed.intersection({"es_relevador_calle", "datacalle_rol"}):
            self._sync_grupo_datacalle(user)

    def _save_profile(self, user, creating, changed):
        profile, _ = Profile.objects.get_or_create(user=user)
        fields = set()
        for name in (
            "acceso_web",
            "acceso_siis",
            "dni",
            "cuil",
            "tipo_usuario",
            "es_usuario_provincial",
            "rol",
            "es_relevador_calle",
            "datacalle_rol",
        ):
            if creating or name in changed:
                setattr(profile, name, self.cleaned_data.get(name))
                fields.add(name)
        scope_changed = creating or bool(
            changed.intersection(
                {"es_usuario_provincial", "provincia", "territorial_scopes"}
            )
        )
        datacalle_changed = creating or bool(
            changed.intersection({"es_relevador_calle", "datacalle_rol"})
        )
        if scope_changed or datacalle_changed:
            profile.provincia = None
            profile.es_usuario_provincial = self.cleaned_data.get(
                "es_usuario_provincial", False
            )
            fields.update({"provincia", "es_usuario_provincial"})
        if creating or changed.intersection(
            {"es_inspector_escolar", "inspecciones_rol"}
        ):
            self._apply_inspecciones_escolares_to_profile(profile)
            fields.update({"es_inspector_escolar", "inspecciones_rol"})
        if creating or self.cleaned_data.get("password"):
            profile.must_change_password = True
            profile.password_changed_at = None
            profile.initial_password_expires_at = timezone.now() + timedelta(
                hours=settings.INITIAL_PASSWORD_MAX_AGE_HOURS
            )
            profile.password_reset_requested_at = None
            profile.temporary_password_plaintext = None
            fields.update(
                {
                    "must_change_password",
                    "password_changed_at",
                    "initial_password_expires_at",
                    "password_reset_requested_at",
                    "temporary_password_plaintext",
                }
            )
        if fields:
            profile.save(update_fields=fields)
        if creating or changed.intersection(
            {"es_relevador_calle", "datacalle_rol", "provincias_datacalle"}
        ):
            self._sync_relevador_calle_provincias(profile)
        if scope_changed or datacalle_changed:
            sync_profile_territorial_scopes(
                profile, self.cleaned_data.get("territorial_scopes_data", [])
            )
            validar_alcance_coordinador(profile)
        for name in ("grupos_asignables", "roles_asignables"):
            if creating or name in changed:
                getattr(profile, name).set(self.cleaned_data.get(name, []))


class UserCreationForm(IdentityAdminForm):
    """Alta independiente de identidad y programas compartidos."""


class CustomUserChangeForm(IdentityAdminForm):
    """Edición independiente: conserva las asignaciones del dominio omitidas."""
