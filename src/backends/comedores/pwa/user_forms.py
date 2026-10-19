# pylint: disable=too-many-lines
from datetime import timedelta

from django import forms
from django.conf import settings
from django.contrib.auth.models import Permission, User
from django.db import transaction
from django.utils.crypto import get_random_string
from django.utils import timezone


from core.models import Provincia

from users.form_sections import (
    TerritorialScopeFormMixin,
    DelegationScopeMixin,
    RelevadorCalleFormMixin,
    InspeccionesEscolaresFormMixin,
)

from users.identity_fields import IdentityFieldsForm
from users.form_catalogs import obtener_queryset_formulario
from users.models import Profile, TerritorialComedorProvincia
from users.profile_utils import get_profile_or_none
from users.services_datacalle import validar_alcance_coordinador
from users.territorial_scope import sync_profile_territorial_scopes
from pwa.models import (
    AccesoComedorPWA,
    CoordinadorEquipoTecnicoPWA,
)
from pwa.services.accesos import (
    PWA_ASSIGNABLE_PERMISSION_CODES,
    PWA_USUARIOS_PERMISSION_CODE,
    deactivate_coordinador_equipo_tecnico_pwa_access,
    deactivate_representante_accesses,
    get_organizacion_ids,
    sync_coordinador_equipo_tecnico_pwa_access,
    sync_representante_accesses,
)


MOBILE_RENDICION_PERMISSION_CODE = "rendicioncuentasmensual.manage_mobile_rendicion"
PWA_OPERATION_PERMISSION_CODES = PWA_ASSIGNABLE_PERMISSION_CODES | {
    PWA_USUARIOS_PERMISSION_CODE,
}
PWA_OPERATION_PERMISSION_FIELDS = {
    "puede_gestionar_colaboradores_pwa": (
        "pwa.manage_colaboradores_pwa",
        "Puede gestionar colaboradores mobile",
    ),
    "puede_gestionar_usuarios_pwa": (
        "pwa.manage_usuarios_pwa",
        "Puede crear y gestionar usuarios mobile",
    ),
    "puede_gestionar_nomina_pwa": (
        "pwa.manage_nomina_pwa",
        "Puede gestionar nomina mobile",
    ),
    "puede_gestionar_prestaciones_mensuales_pwa": (
        "pwa.manage_prestaciones_mensuales_pwa",
        "Puede gestionar prestaciones mensuales mobile",
    ),
}


PWA_SELECTION_FIELDS = (
    "es_coordinador_equipo_tecnico_pwa",
    "duplas_coordinador_pwa",
    "comedores_adicionales_coordinador_pwa",
    "puede_gestionar_rendiciones_mobile",
    *PWA_OPERATION_PERMISSION_FIELDS,
    "tipo_asociacion_pwa",
    "organizaciones_pwa",
    "comedores_pwa",
)


# Campos de cada sección del ABM habilitada por permiso (ver
# ``users.secciones_usuario``). Sin el permiso de la sección, sus campos quedan
# deshabilitados además de ocultos en el template: un POST construido a mano no
# puede modificarlos y en edición Django conserva los valores actuales.


class ComedorPWASelectMultiple(forms.SelectMultiple):
    """Agrega metadata de organización en las opciones para filtrado dinámico."""

    def create_option(  # pylint: disable=too-many-arguments
        self, name, value, label, selected, index, subindex=None, attrs=None
    ):
        option = super().create_option(
            name, value, label, selected, index, subindex=subindex, attrs=attrs
        )
        instance = getattr(value, "instance", None)
        if instance is not None:
            option["attrs"]["data-organizacion-id"] = str(
                instance.organizacion_id or ""
            )
            option["attrs"]["data-organizacion-nombre"] = (
                instance.organizacion.nombre if instance.organizacion_id else ""
            )
        return option


class PWAAccessMixin:
    @staticmethod
    def _get_mobile_rendicion_permission():
        return Permission.objects.get(
            content_type__app_label="rendicioncuentasmensual",
            codename="manage_mobile_rendicion",
        )

    @staticmethod
    def _get_permission_from_code(permission_code):
        app_label, codename = permission_code.split(".", 1)
        return Permission.objects.get(
            content_type__app_label=app_label,
            codename=codename,
        )

    @staticmethod
    def _set_initial_password_flags(
        profile,
        *,
        must_change_password: bool,
        temporary_password_plaintext: str | None = None,
        password_reset_requested_at=None,
    ):
        profile.must_change_password = must_change_password
        profile.password_changed_at = (
            None if must_change_password else profile.password_changed_at
        )
        profile.initial_password_expires_at = (
            timezone.now() + timedelta(hours=settings.INITIAL_PASSWORD_MAX_AGE_HOURS)
            if must_change_password
            else None
        )
        profile.password_reset_requested_at = password_reset_requested_at
        profile.temporary_password_plaintext = temporary_password_plaintext

    def _setup_pwa_fields(self):
        self.fields["es_representante_pwa"] = forms.BooleanField(
            required=False,
            label="Habilitar acceso a Espacios comunitarios",
        )
        self.fields["es_coordinador_equipo_tecnico_pwa"] = forms.BooleanField(
            required=False,
            label="Coordinador de Equipo Técnico",
            help_text="Acceso PWA exclusivo de solo lectura.",
        )
        self.fields["duplas_coordinador_pwa"] = forms.ModelMultipleChoiceField(
            queryset=obtener_queryset_formulario("duplas_asignadas"),
            required=False,
            widget=forms.SelectMultiple(attrs={"class": "select2"}),
            label="Equipos técnicos PWA",
            help_text="El alcance se actualiza automáticamente según sus comedores.",
        )
        self.fields["comedores_adicionales_coordinador_pwa"] = (
            forms.ModelMultipleChoiceField(
                queryset=obtener_queryset_formulario("comedores_pwa"),
                required=False,
                widget=forms.SelectMultiple(attrs={"class": "select2"}),
                label="Comedores adicionales PWA",
            )
        )
        self.fields["puede_gestionar_rendiciones_mobile"] = forms.BooleanField(
            required=False,
            label="Puede gestionar rendiciones mobile",
            help_text="Habilita el módulo Rendición de Cuentas en SISOC - Mobile.",
        )
        for field_name, (_, label) in PWA_OPERATION_PERMISSION_FIELDS.items():
            self.fields[field_name] = forms.BooleanField(
                required=False,
                label=label,
            )
        self.fields["tipo_asociacion_pwa"] = forms.ChoiceField(
            required=False,
            choices=(
                ("", "Seleccione una opción"),
                (
                    AccesoComedorPWA.TIPO_ASOCIACION_ORGANIZACION,
                    "Usuario asociado a Organización",
                ),
                (
                    AccesoComedorPWA.TIPO_ASOCIACION_ESPACIO,
                    "Usuario asociado a Espacio",
                ),
            ),
            widget=forms.Select(attrs={"class": "select2"}),
            label="Tipo de asociación mobile",
        )
        self.fields["organizaciones_pwa"] = forms.ModelMultipleChoiceField(
            queryset=obtener_queryset_formulario("organizaciones_pwa"),
            required=False,
            widget=forms.SelectMultiple(attrs={"class": "select2"}),
            label="Organizaciones",
            help_text=(
                "Cada organización habilita automáticamente todos sus comedores "
                "actuales y futuros."
            ),
        )
        self.fields["comedores_pwa"] = forms.ModelMultipleChoiceField(
            queryset=obtener_queryset_formulario("comedores_pwa"),
            required=False,
            widget=ComedorPWASelectMultiple(attrs={"class": "select2"}),
            label="Comedores PWA",
            help_text="Comedores que este usuario representa en la PWA.",
        )

    def _init_pwa_fields(self):
        if not self.instance or not self.instance.pk:
            return
        accesos = AccesoComedorPWA.objects.filter(
            user=self.instance,
            rol=AccesoComedorPWA.ROL_REPRESENTANTE,
            activo=True,
        )
        organizacion_ids = get_organizacion_ids(self.instance) or list(
            accesos.exclude(organizacion_id__isnull=True)
            .values_list("organizacion_id", flat=True)
            .distinct()
        )
        tipos_asociacion = sorted(
            {tipo for tipo in accesos.values_list("tipo_asociacion", flat=True) if tipo}
        )
        comedor_ids = list(accesos.values_list("comedor_id", flat=True))
        self.fields["es_representante_pwa"].initial = bool(
            comedor_ids or organizacion_ids
        )
        self.fields["puede_gestionar_rendiciones_mobile"].initial = (
            self.instance.has_perm(MOBILE_RENDICION_PERMISSION_CODE)
        )
        for field_name, (permission_code, _) in PWA_OPERATION_PERMISSION_FIELDS.items():
            self.fields[field_name].initial = self.instance.has_perm(permission_code)
        self.fields["tipo_asociacion_pwa"].initial = (
            tipos_asociacion[0]
            if len(tipos_asociacion) == 1
            else (
                AccesoComedorPWA.TIPO_ASOCIACION_ORGANIZACION
                if organizacion_ids and not tipos_asociacion
                else ""
            )
        )
        self.fields["organizaciones_pwa"].initial = organizacion_ids
        self.fields["comedores_pwa"].initial = comedor_ids
        coordinator_scope = CoordinadorEquipoTecnicoPWA.objects.filter(
            user=self.instance, activo=True
        ).first()
        if coordinator_scope:
            self.fields["es_representante_pwa"].initial = True
            self.fields["es_coordinador_equipo_tecnico_pwa"].initial = True
            self.fields["duplas_coordinador_pwa"].initial = (
                coordinator_scope.duplas.all()
            )
            self.fields["comedores_adicionales_coordinador_pwa"].initial = (
                coordinator_scope.comedores_adicionales.all()
            )

        profile = get_profile_or_none(self.instance)
        selections = getattr(profile, "configuracion_mobile", {})
        mobile_enabled = self.fields["es_representante_pwa"].initial
        for name in PWA_SELECTION_FIELDS:
            if name in selections and (
                not mobile_enabled
                or (
                    coordinator_scope
                    and name
                    in (
                        "puede_gestionar_rendiciones_mobile",
                        *PWA_OPERATION_PERMISSION_FIELDS,
                    )
                )
            ):
                self.fields[name].initial = selections[name]

    def _is_active_pwa_operator(self) -> bool:
        if not self.instance or not self.instance.pk:
            return False
        return AccesoComedorPWA.objects.filter(
            user=self.instance,
            rol=AccesoComedorPWA.ROL_OPERADOR,
            activo=True,
        ).exists()

    def _sync_mobile_rendicion_permission(self, user):
        permission = self._get_mobile_rendicion_permission()
        if self.cleaned_data.get("puede_gestionar_rendiciones_mobile"):
            user.user_permissions.add(permission)
            return
        user.user_permissions.remove(permission)

    def _sync_pwa_operation_permissions(self, user):
        for field_name, (permission_code, _) in PWA_OPERATION_PERMISSION_FIELDS.items():
            permission = self._get_permission_from_code(permission_code)
            if self.cleaned_data.get(field_name):
                user.user_permissions.add(permission)
            else:
                user.user_permissions.remove(permission)

    @staticmethod
    def _preserve_current_pwa_operation_permission_ids(user):
        permission_ids = []
        effective_codes = (
            set(user.get_all_permissions()) & PWA_OPERATION_PERMISSION_CODES
        )
        for permission_code in effective_codes:
            app_label, codename = permission_code.split(".", 1)
            permission = Permission.objects.filter(
                content_type__app_label=app_label,
                codename=codename,
            ).first()
            if permission:
                permission_ids.append(permission.id)
        return permission_ids

    def _clean_mobile_access_switch(self, cleaned):
        # The legacy field name now acts as the master mobile access switch.
        # Remember selections before normalizing inactive roles and permissions.
        self._mobile_selections = {}
        for name in PWA_SELECTION_FIELDS:
            value = cleaned.get(name)
            if isinstance(self.fields[name], forms.ModelMultipleChoiceField):
                value = (
                    list(value.values_list("pk", flat=True))
                    if value is not None
                    else []
                )
            self._mobile_selections[name] = value
        mobile_enabled = cleaned.get("es_representante_pwa", False)
        if not mobile_enabled:
            cleaned["es_coordinador_equipo_tecnico_pwa"] = False
        if not mobile_enabled or cleaned.get("es_coordinador_equipo_tecnico_pwa"):
            for name in (
                "puede_gestionar_rendiciones_mobile",
                *PWA_OPERATION_PERMISSION_FIELDS,
            ):
                cleaned[name] = False

    def _clean_pwa_fields(self, cleaned):
        self._clean_mobile_access_switch(cleaned)
        es_coordinador_pwa = cleaned.get("es_coordinador_equipo_tecnico_pwa", False)
        es_representante_pwa = (
            cleaned.get("es_representante_pwa", False) and not es_coordinador_pwa
        )
        tipo_asociacion_pwa = cleaned.get("tipo_asociacion_pwa")
        organizaciones_pwa = cleaned.get("organizaciones_pwa")
        comedores_pwa = cleaned.get("comedores_pwa")
        es_coordinador = cleaned.get("es_coordinador", False)

        if es_coordinador_pwa:
            if not cleaned.get("duplas_coordinador_pwa"):
                self.add_error(
                    "duplas_coordinador_pwa",
                    "Seleccione al menos un equipo técnico para el coordinador PWA.",
                )
            if es_coordinador:
                self.add_error(
                    "es_coordinador",
                    "El coordinador PWA es independiente del coordinador SISOC.",
                )
            if cleaned.get("es_territorial_comedor"):
                self.add_error(
                    "es_territorial_comedor",
                    "El coordinador PWA no puede tener acceso territorial.",
                )
            if self.instance and self.instance.pk and self._is_active_pwa_operator():
                self.add_error(
                    "es_coordinador_equipo_tecnico_pwa",
                    "El coordinador PWA no puede tener rol operador activo.",
                )

        if not es_representante_pwa:
            cleaned["tipo_asociacion_pwa"] = ""
            cleaned["organizaciones_pwa"] = self.fields[
                "organizaciones_pwa"
            ].queryset.none()
            cleaned["comedores_pwa"] = self.fields["comedores_pwa"].queryset.none()
            tipo_asociacion_pwa = ""
            organizaciones_pwa = cleaned["organizaciones_pwa"]
            comedores_pwa = cleaned["comedores_pwa"]

        if es_representante_pwa and not (comedores_pwa or organizaciones_pwa):
            self.add_error(
                "comedores_pwa",
                "Debe seleccionar al menos una organización o un comedor para un "
                "representante PWA.",
            )
        if not es_representante_pwa and (
            comedores_pwa or organizaciones_pwa or tipo_asociacion_pwa
        ):
            self.add_error(
                "es_representante_pwa",
                "Marque este campo para asignar comedores PWA.",
            )
        if es_representante_pwa and es_coordinador:
            self.add_error(
                "es_coordinador",
                "Un representante PWA no puede ser coordinador de equipo técnico.",
            )
        if es_representante_pwa and self.instance and self.instance.pk:
            if AccesoComedorPWA.objects.filter(
                user=self.instance,
                rol=AccesoComedorPWA.ROL_OPERADOR,
                activo=True,
            ).exists():
                self.add_error(
                    "es_representante_pwa",
                    "No se puede asignar representante PWA a un usuario operador activo.",
                )

        return cleaned

    def _sync_pwa_access(self, user):
        if not self._is_active_pwa_operator():
            Profile.objects.filter(user=user).update(
                configuracion_mobile=self._mobile_selections
            )
        if self.cleaned_data.get("es_coordinador_equipo_tecnico_pwa"):
            deactivate_representante_accesses(user)
            sync_coordinador_equipo_tecnico_pwa_access(
                user=user,
                duplas=self.cleaned_data["duplas_coordinador_pwa"],
                comedores_adicionales=self.cleaned_data[
                    "comedores_adicionales_coordinador_pwa"
                ],
            )
            return
        deactivate_coordinador_equipo_tecnico_pwa_access(user)
        if not self.cleaned_data.get(
            "es_representante_pwa"
        ) and self._mobile_selections.get("es_coordinador_equipo_tecnico_pwa"):
            scope, _ = CoordinadorEquipoTecnicoPWA.objects.get_or_create(
                user=user, defaults={"activo": False}
            )
            scope.duplas.set(self._mobile_selections["duplas_coordinador_pwa"])
            scope.comedores_adicionales.set(
                self._mobile_selections["comedores_adicionales_coordinador_pwa"]
            )
        if self.cleaned_data.get("es_representante_pwa"):
            organization_ids = set(
                self.cleaned_data["organizaciones_pwa"].values_list("id", flat=True)
            )
            selected_by_id = {
                comedor.id: comedor for comedor in self.cleaned_data["comedores_pwa"]
            }
            for comedor in self.fields["comedores_pwa"].queryset.filter(
                organizacion_id__in=organization_ids
            ):
                selected_by_id[comedor.id] = comedor

            access_specs = []
            for comedor in sorted(selected_by_id.values(), key=lambda item: item.id):
                association_type = (
                    AccesoComedorPWA.TIPO_ASOCIACION_ORGANIZACION
                    if comedor.organizacion_id in organization_ids
                    else AccesoComedorPWA.TIPO_ASOCIACION_ESPACIO
                )
                access_specs.append(
                    {
                        "comedor_id": comedor.id,
                        "tipo_asociacion": association_type,
                        "organizacion_id": (
                            comedor.organizacion_id
                            if association_type
                            == AccesoComedorPWA.TIPO_ASOCIACION_ORGANIZACION
                            else None
                        ),
                    }
                )
            sync_representante_accesses(
                user=user,
                access_specs=access_specs,
                organizacion_ids=organization_ids,
                actor=None,
            )
            return
        deactivate_representante_accesses(user)

    def _clean_optional_email(self, cleaned):
        # El email es opcional y puede repetirse entre usuarios; la unicidad
        # vive en username. Solo normalizamos espacios para evitar registros
        # inconsistentes.
        cleaned["email"] = (cleaned.get("email") or "").strip()
        return cleaned


class TerritorialComedorFormMixin:
    """Campos del rol "Territorial comedor" (SISOC - Mobile).

    Flag simple sobre ``Profile.es_territorial_comedor`` + alcance por provincia
    en ``TerritorialComedorProvincia``. Es mutuamente excluyente con el
    representante PWA (``es_representante_pwa``): un mismo usuario no puede ser
    ambos. No arrastra la maquinaria del representante (auto-password, limpieza
    de grupos, ocultamiento del backoffice): el territorial es un usuario normal
    con una marca de rol y su alcance provincial.
    """

    def _setup_territorial_comedor_fields(self):
        self.fields["es_territorial_comedor"] = forms.BooleanField(
            required=False,
            label="Habilitar acceso a SISOC - Mobile",
        )
        self.fields["provincias_territorial"] = forms.ModelMultipleChoiceField(
            queryset=Provincia.objects.all().order_by("nombre"),
            required=False,
            widget=forms.SelectMultiple(attrs={"class": "select2"}),
            label="Provincias",
            help_text="Provincias que cubre este territorial en SISOC - Mobile.",
        )

    def _init_territorial_comedor_fields(self, profile):
        if not profile:
            return
        self.fields["es_territorial_comedor"].initial = profile.es_territorial_comedor
        self.fields["provincias_territorial"].initial = list(
            profile.territorial_comedor_provincias.values_list(
                "provincia_id", flat=True
            )
        )

    def _clean_territorial_comedor_fields(self, cleaned):
        es_territorial = cleaned.get("es_territorial_comedor", False)
        es_representante_pwa = cleaned.get("es_representante_pwa", False)
        es_coordinador_pwa = cleaned.get("es_coordinador_equipo_tecnico_pwa", False)
        provincias = cleaned.get("provincias_territorial")

        if es_territorial and (es_representante_pwa or es_coordinador_pwa):
            self.add_error(
                "es_territorial_comedor",
                "Un usuario territorial no puede tener acceso PWA de coordinador "
                "ni representante a la vez.",
            )

        if not es_territorial:
            cleaned["provincias_territorial"] = Provincia.objects.none()
            return cleaned

        if not provincias:
            self.add_error(
                "provincias_territorial",
                "Seleccione al menos una provincia para el territorial.",
            )
        return cleaned

    def _sync_territorial_comedor_provincias(self, profile):
        if not profile.es_territorial_comedor:
            profile.territorial_comedor_provincias.all().delete()
            return
        selected_ids = {
            provincia.id
            for provincia in self.cleaned_data.get("provincias_territorial") or []
        }
        existing_ids = set(
            profile.territorial_comedor_provincias.values_list(
                "provincia_id", flat=True
            )
        )
        to_delete = existing_ids - selected_ids
        if to_delete:
            profile.territorial_comedor_provincias.filter(
                provincia_id__in=to_delete
            ).delete()
        for provincia_id in selected_ids - existing_ids:
            TerritorialComedorProvincia.objects.create(
                profile=profile, provincia_id=provincia_id
            )


class UserCreationForm(
    TerritorialScopeFormMixin,
    PWAAccessMixin,
    TerritorialComedorFormMixin,
    RelevadorCalleFormMixin,
    InspeccionesEscolaresFormMixin,
    DelegationScopeMixin,
    IdentityFieldsForm,
):
    es_coordinador = forms.BooleanField(
        required=False,
        label="Es Coordinador de Equipo Técnico",
    )
    duplas_asignadas = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "select2"}),
        label="Equipos técnicos (Duplas) asignadas",
        help_text="Duplas activas disponibles (con o sin comedores asignados)",
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
            "es_coordinador",
            "duplas_asignadas",
            "last_name",
            "first_name",
            "rol",
        ]

    def __init__(self, *args, **kwargs):
        self.actor = kwargs.pop("actor", None)
        super().__init__(*args, **kwargs)
        self.fields["duplas_asignadas"].queryset = obtener_queryset_formulario(
            "duplas_asignadas"
        )
        self._setup_pwa_fields()
        self._setup_territorial_comedor_fields()
        self._setup_relevador_calle_fields()
        self._setup_inspecciones_escolares_fields()
        self._setup_delegation_fields()
        self._scope_assignable_fields_for_actor()
        self.fields["email"].required = False
        self.fields["password"].required = False
        self.generated_password = None
        self.password_was_auto_generated = False
        self._setup_territorial_scope_fields()
        self._apply_section_restrictions()

    def clean(self):
        cleaned = super().clean()
        cleaned = self._clean_optional_email(cleaned)
        if (
            not cleaned.get("es_representante_pwa")
            and not (cleaned.get("password") or "").strip()
        ):
            self.add_error("password", "Este campo es obligatorio.")
        cleaned = self._clean_territorial_scope_fields(cleaned)
        if cleaned.get("es_coordinador") and not cleaned.get("duplas_asignadas"):
            self.add_error("duplas_asignadas", "Seleccione al menos una dupla.")
        self._validate_selected_within_allowed(cleaned)
        cleaned = self._clean_pwa_fields(cleaned)
        cleaned = self._clean_territorial_comedor_fields(cleaned)
        cleaned = self._clean_relevador_calle_fields(cleaned)
        cleaned = self._clean_inspecciones_escolares_fields(cleaned)
        cleaned = self._validar_provincia_unica_coordinador(cleaned)
        cleaned = self._clean_acceso_web_solo_app(cleaned)
        # SIMEPI - EGP se valida al final, después de DataCalle: el alcance
        # efectivo de un usuario de DataCalle lo decide el rol, así que correr
        # antes miraba el panel y no lo que realmente se va a guardar.
        return self._validate_simepi_egp_scope(cleaned)

    @staticmethod
    def _clean_acceso_web_solo_app(cleaned):
        """El alta de un usuario de app no habilita la web aunque quede tildada.

        La casilla arranca marcada y antes de ``acceso_web`` estos usuarios no
        entraban a la web. Habilitarla después, al editar, sigue siendo posible.
        """
        if (
            cleaned.get("es_representante_pwa")
            or cleaned.get("es_coordinador_equipo_tecnico_pwa")
            or cleaned.get("datacalle_rol") == Profile.DataCalleRol.ENTREVISTADOR
            or (
                cleaned.get("es_inspector_escolar")
                and cleaned.get("inspecciones_rol") == Profile.InspeccionesRol.INSPECTOR
            )
        ):
            cleaned["acceso_web"] = False
        return cleaned

    def save(self, commit=True):
        with transaction.atomic():
            return self._save_atomic(commit=commit)

    def _configure_created_user(self, user):
        if self.cleaned_data.get(
            "es_representante_pwa", False
        ) or self.cleaned_data.get("es_coordinador_equipo_tecnico_pwa", False):
            self.generated_password = get_random_string(12)
            user.set_password(self.generated_password)
            user.is_staff = False
            self.password_was_auto_generated = True
            return
        user.set_password(self.cleaned_data["password"])
        self.generated_password = None
        self.password_was_auto_generated = False
        # Solo el relevador es usuario sin backoffice (RN05). El coordinador y
        # el administrador tambien llevan `es_relevador_calle` —les habilita la
        # app— pero entran a SISOC.
        if self.cleaned_data.get("datacalle_rol") == "entrevistador":
            user.is_staff = False
            return
        # El inspector escolar también es usuario sólo de la app.
        if self._es_inspector_solo_app():
            user.is_staff = False
            return
        if self.cleaned_data.get("es_coordinador", False):
            user.is_staff = True

    def _save_user_security_and_permissions(self, user):
        # Generic assignments retain their actor-scoped delegation checks.
        pwa_permission_ids = self._preserve_current_pwa_operation_permission_ids(user)
        self._aplicar_grupos_y_permisos(user)
        if pwa_permission_ids:
            user.user_permissions.add(*pwa_permission_ids)
        self._sync_grupo_datacalle(user)
        self._sync_mobile_rendicion_permission(user)
        if self.cleaned_data.get("es_representante_pwa", False):
            self._sync_pwa_operation_permissions(user)

    def _save_user_profile(self, user):
        profile, _ = Profile.objects.get_or_create(user=user)
        profile.es_usuario_provincial = self.cleaned_data.get(
            "es_usuario_provincial", False
        )
        profile.acceso_web = self.cleaned_data.get("acceso_web", False)
        profile.acceso_siis = self.cleaned_data.get("acceso_siis", False)
        profile.dni = self.cleaned_data.get("dni", "")
        profile.cuil = self.cleaned_data.get("cuil", "")
        profile.tipo_usuario = self.cleaned_data["tipo_usuario"]
        profile.provincia = None
        profile.es_coordinador = self.cleaned_data.get("es_coordinador", False)
        profile.es_territorial_comedor = self.cleaned_data.get(
            "es_territorial_comedor", False
        )
        profile.es_relevador_calle = self.cleaned_data.get("es_relevador_calle", False)
        profile.datacalle_rol = self.cleaned_data.get("datacalle_rol", "")
        self._apply_inspecciones_escolares_to_profile(profile)
        profile.rol = self.cleaned_data.get("rol")
        profile.must_change_password = True
        profile.password_changed_at = None
        profile.initial_password_expires_at = timezone.now() + timedelta(
            hours=settings.INITIAL_PASSWORD_MAX_AGE_HOURS
        )
        profile.temporary_password_plaintext = self.generated_password
        profile.save()
        self._sync_territorial_comedor_provincias(profile)
        self._sync_relevador_calle_provincias(profile)
        sync_profile_territorial_scopes(
            profile,
            self.cleaned_data.get("territorial_scopes_data", []),
        )
        validar_alcance_coordinador(profile)
        # Evita devolver un profile cacheado con valores viejos tras el signal de User.
        user.refresh_from_db()
        profile.grupos_asignables.set(self.cleaned_data.get("grupos_asignables", []))
        profile.roles_asignables.set(self.cleaned_data.get("roles_asignables", []))
        return profile

    @staticmethod
    def _sync_coordinator_duplas(profile, duplas):
        if profile.es_coordinador and duplas:
            profile.duplas_asignadas.set(duplas)
            return
        profile.duplas_asignadas.clear()

    def _save_atomic(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data.get("email", "")
        self._configure_created_user(user)

        if commit:
            user.save()
            self._save_user_security_and_permissions(user)
            profile = self._save_user_profile(user)
            duplas = self.cleaned_data.get("duplas_asignadas", [])
            self._sync_coordinator_duplas(profile, duplas)
            self._sync_pwa_access(user)

        self._clear_permission_caches(user)
        return user


class CustomUserChangeForm(
    TerritorialScopeFormMixin,
    PWAAccessMixin,
    TerritorialComedorFormMixin,
    RelevadorCalleFormMixin,
    InspeccionesEscolaresFormMixin,
    DelegationScopeMixin,
    IdentityFieldsForm,
):
    password = forms.CharField(
        widget=forms.PasswordInput,
        label="Contraseña (dejar en blanco para no cambiarla)",
        required=False,
    )
    es_coordinador = forms.BooleanField(
        required=False,
        label="Es Coordinador de Equipo Técnico",
    )
    duplas_asignadas = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "select2"}),
        label="Equipos técnicos (Duplas) asignadas",
        help_text="Duplas activas disponibles (con o sin comedores asignados)",
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
            "es_coordinador",
            "duplas_asignadas",
            "last_name",
            "first_name",
            "rol",
        ]

    def __init__(self, *args, **kwargs):
        self.actor = kwargs.pop("actor", None)
        super().__init__(*args, **kwargs)
        self.fields["duplas_asignadas"].queryset = obtener_queryset_formulario(
            "duplas_asignadas"
        )
        self._setup_pwa_fields()
        self._setup_territorial_comedor_fields()
        self._setup_relevador_calle_fields()
        self._setup_inspecciones_escolares_fields()
        self._setup_delegation_fields()
        self._scope_assignable_fields_for_actor()
        self.fields["email"].required = False
        self._original_password_hash = self.instance.password
        self.fields["password"].initial = ""
        self._init_pwa_fields()

        try:
            prof = self.instance.profile
        except Profile.DoesNotExist:
            prof = None

        self._setup_territorial_scope_fields(prof)
        self._init_territorial_comedor_fields(prof)
        self._init_relevador_calle_fields(prof)
        self._init_inspecciones_escolares_fields(prof)
        if prof:
            self.fields["acceso_web"].initial = prof.acceso_web
            self.fields["acceso_siis"].initial = prof.acceso_siis
            self.fields["dni"].initial = prof.dni
            self.fields["cuil"].initial = prof.cuil
            self.fields["tipo_usuario"].initial = prof.tipo_usuario
            self.fields["es_usuario_provincial"].initial = prof.es_usuario_provincial
            self.fields["provincia"].initial = prof.provincia
            self.fields["es_coordinador"].initial = prof.es_coordinador
            self.fields["duplas_asignadas"].initial = prof.duplas_asignadas.all()
            self.fields["rol"].initial = prof.rol
            self._init_delegation_fields(prof)
        self._apply_section_restrictions()

    def clean(self):
        cleaned = super().clean()
        cleaned = self._clean_optional_email(cleaned)
        cleaned = self._clean_territorial_scope_fields(cleaned)
        if cleaned.get("es_coordinador") and not cleaned.get("duplas_asignadas"):
            self.add_error("duplas_asignadas", "Seleccione al menos una dupla.")
        self._validate_selected_within_allowed(cleaned)
        cleaned = self._clean_pwa_fields(cleaned)
        cleaned = self._clean_territorial_comedor_fields(cleaned)
        cleaned = self._clean_relevador_calle_fields(cleaned)
        cleaned = self._clean_inspecciones_escolares_fields(cleaned)
        cleaned = self._validar_provincia_unica_coordinador(cleaned)
        # SIMEPI - EGP se valida al final, después de DataCalle: el alcance
        # efectivo de un usuario de DataCalle lo decide el rol, así que correr
        # antes miraba el panel y no lo que realmente se va a guardar.
        return self._validate_simepi_egp_scope(cleaned)

    def save(self, commit=True):
        with transaction.atomic():
            return self._save_atomic(commit=commit)

    def _save_atomic(  # pylint: disable=too-many-branches,too-many-statements
        self, commit=True
    ):
        new_pwd = self.cleaned_data.get("password")
        user = super().save(commit=False)
        user.email = self.cleaned_data.get("email", "")

        if new_pwd:
            user.set_password(new_pwd)
        else:
            user.password = self._original_password_hash

        is_pwa_operator = self._is_active_pwa_operator()
        is_pwa_read_only_coordinator = self.cleaned_data.get(
            "es_coordinador_equipo_tecnico_pwa", False
        )
        if self.cleaned_data.get("es_coordinador", False):
            user.is_staff = True

        if commit:
            user.save()
            pwa_permission_ids = self._preserve_current_pwa_operation_permission_ids(
                user
            )
            self._aplicar_grupos_y_permisos(user)
            if pwa_permission_ids:
                user.user_permissions.add(*pwa_permission_ids)
            self._sync_grupo_datacalle(user)
            if not is_pwa_operator:
                self._sync_mobile_rendicion_permission(user)
                self._sync_pwa_operation_permissions(user)

            profile, _ = Profile.objects.get_or_create(user=user)
            profile.es_usuario_provincial = self.cleaned_data.get(
                "es_usuario_provincial", False
            )
            profile.acceso_web = self.cleaned_data.get("acceso_web", False)
            profile.acceso_siis = self.cleaned_data.get("acceso_siis", False)
            profile.dni = self.cleaned_data.get("dni", "")
            profile.cuil = self.cleaned_data.get("cuil", "")
            profile.tipo_usuario = self.cleaned_data["tipo_usuario"]
            profile.provincia = None
            profile.es_coordinador = self.cleaned_data.get("es_coordinador", False)
            profile.es_territorial_comedor = self.cleaned_data.get(
                "es_territorial_comedor", False
            )
            profile.es_relevador_calle = self.cleaned_data.get(
                "es_relevador_calle", False
            )
            profile.datacalle_rol = self.cleaned_data.get("datacalle_rol", "")
            self._apply_inspecciones_escolares_to_profile(profile)
            profile.rol = self.cleaned_data.get("rol")
            if new_pwd:
                self._set_initial_password_flags(
                    profile,
                    must_change_password=True,
                    temporary_password_plaintext=None,
                    password_reset_requested_at=None,
                )
            elif (
                not self.cleaned_data.get("es_representante_pwa", False)
                and not is_pwa_read_only_coordinator
                and not is_pwa_operator
            ):
                profile.password_reset_requested_at = None
                profile.must_change_password = False
                profile.password_changed_at = None
                profile.initial_password_expires_at = timezone.now() + timedelta(
                    hours=settings.INITIAL_PASSWORD_MAX_AGE_HOURS
                )
                profile.temporary_password_plaintext = None
            profile.save()
            self._sync_territorial_comedor_provincias(profile)
            self._sync_relevador_calle_provincias(profile)
            sync_profile_territorial_scopes(
                profile,
                self.cleaned_data.get("territorial_scopes_data", []),
            )
            validar_alcance_coordinador(profile)
            user.refresh_from_db()
            profile.grupos_asignables.set(
                self.cleaned_data.get("grupos_asignables", [])
            )
            profile.roles_asignables.set(self.cleaned_data.get("roles_asignables", []))

            duplas = self.cleaned_data.get("duplas_asignadas", [])
            if profile.es_coordinador and duplas:
                profile.duplas_asignadas.set(duplas)
            else:
                profile.duplas_asignadas.clear()

            self._sync_pwa_access(user)
            self._clear_permission_caches(user)

        return user


# Leyenda del checkbox de declaración. Es la redacción provisoria acordada con
# UX/UI: queda pendiente de un filtro de aprobación posterior, así que puede
# volver con cambios. Para modificarla alcanza con esta constante; no hay copia
# duplicada en templates ni en tests.
#
# El texto original de UX estaba redactado como aviso en segunda persona
# ("comprometiéndote a..."), que no funciona como leyenda de un checkbox: al
