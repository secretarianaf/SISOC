"""Secciones administrativas de identidad reutilizadas por portal y Comedores."""

# pylint: disable=too-many-lines
import json
from django import forms
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import FileExtensionValidator
from core.constants import UserGroups
from core.models import Provincia
from users.models import Profile, RelevadorCalleProvincia
from users.profile_utils import get_profile_or_none
from users.services_datacalle import es_administrador_datacalle
from users.services_delegation import effective_delegatable_groups_qs
from users.services_bulk_credentials import get_bulk_credentials_send_type_choices
from users.secciones_usuario import (
    SECCION_ADMINISTRACION,
    SECCION_DATACALLE,
    SECCION_EQUIPOS_TECNICOS,
    SECCION_INSPECCIONES_ESCOLARES,
    SECCION_MOBILE_COMEDORES,
    SECCION_TERRITORIAL_COMEDOR,
    secciones_habilitadas,
)
from users.territorial_scope import (
    clean_territorial_scope_payload,
    get_full_province_scope_ids,
    serialize_profile_scopes,
)

PWA_SELECTION_FIELDS = (
    "es_coordinador_equipo_tecnico_pwa",
    "duplas_coordinador_pwa",
    "comedores_adicionales_coordinador_pwa",
    "puede_gestionar_rendiciones_mobile",
    "puede_gestionar_colaboradores_pwa",
    "puede_gestionar_usuarios_pwa",
    "puede_gestionar_nomina_pwa",
    "puede_gestionar_prestaciones_mensuales_pwa",
    "tipo_asociacion_pwa",
    "organizaciones_pwa",
    "comedores_pwa",
)

CAMPOS_POR_SECCION = {
    SECCION_MOBILE_COMEDORES: ("es_representante_pwa", *PWA_SELECTION_FIELDS),
    SECCION_TERRITORIAL_COMEDOR: ("es_territorial_comedor", "provincias_territorial"),
    SECCION_EQUIPOS_TECNICOS: ("es_coordinador", "duplas_asignadas"),
    SECCION_DATACALLE: ("es_relevador_calle", "datacalle_rol", "provincias_datacalle"),
    SECCION_INSPECCIONES_ESCOLARES: ("es_inspector_escolar", "inspecciones_rol"),
    SECCION_ADMINISTRACION: (
        "user_permissions",
        "acceso_web",
        "acceso_siis",
        "grupos_asignables",
        "roles_asignables",
    ),
}


ROLE_PERMISSION_QUERYSET = (
    Permission.objects.select_related("content_type")
    .filter(
        content_type__app_label="auth",
        codename__startswith="role_",
    )
    .order_by("name")
)


def _validation_error_messages(error):
    if hasattr(error, "messages"):
        return error.messages
    return [str(error)]


class TerritorialScopeFormMixin:
    def _es_autoedicion_provincial(self, profile=None):
        """RN02: nadie provincial se cambia su propia provincia.

        El único campo que estaba ``disabled`` era ``provincias_datacalle``, que
        es la tabla del entrevistador; la provincia del coordinador vive en
        ``ProfileTerritorialScope``, así que un coordinador editándose a sí
        mismo podía mudarse de provincia (por pantalla o por POST) y llevarse
        el alcance de los operativos con él.
        """
        actor = getattr(self, "actor", None)
        instance = getattr(self, "instance", None)
        if actor is None or instance is None or not getattr(instance, "pk", None):
            return False
        if getattr(actor, "pk", None) != instance.pk:
            return False
        if profile is None:
            profile = get_profile_or_none(instance)
        return bool(getattr(profile, "es_usuario_provincial", False))

    def _setup_territorial_scope_fields(self, profile=None):
        initial_scopes = serialize_profile_scopes(profile)
        self.initial_territorial_scopes = initial_scopes
        initial_json = json.dumps(initial_scopes)
        self.fields["territorial_scopes"].initial = initial_json
        if not self.is_bound:
            self.initial["territorial_scopes"] = initial_json
        if self._es_autoedicion_provincial(profile):
            # ``disabled`` no es sólo cosmético: Django ignora lo que llegue por
            # POST y usa el initial, así que la guarda vale también contra un
            # payload armado a mano.
            for nombre in ("territorial_scopes", "es_usuario_provincial"):
                self.fields[nombre].disabled = True
            self.fields["es_usuario_provincial"].initial = True
            self.fields["territorial_scopes"].help_text = (
                "No podés cambiar tu propia provincia."
            )

    def _clean_territorial_scope_fields(self, cleaned):
        if not cleaned.get("es_usuario_provincial"):
            cleaned["territorial_scopes_data"] = []
            return cleaned

        raw_scopes = cleaned.get("territorial_scopes") or "[]"
        try:
            payload = json.loads(raw_scopes)
        except json.JSONDecodeError:
            self.add_error(
                "territorial_scopes",
                "El formato de alcances territoriales no es válido.",
            )
            cleaned["territorial_scopes_data"] = []
            return cleaned

        if payload in (None, [], "") and cleaned.get("provincia"):
            payload = [
                {
                    "provincia_id": cleaned["provincia"].pk,
                    "municipio_id": None,
                    "localidad_id": None,
                }
            ]

        try:
            cleaned["territorial_scopes_data"] = clean_territorial_scope_payload(
                payload
            )
        except DjangoValidationError as error:
            for message in _validation_error_messages(error):
                self.add_error("territorial_scopes", message)
            cleaned["territorial_scopes_data"] = []
        return cleaned

    def _validate_simepi_egp_scope(self, cleaned):
        groups = cleaned.get("groups")
        if not groups or not groups.filter(name=UserGroups.SIMEPI_EGP).exists():
            return cleaned

        scopes = cleaned.get("territorial_scopes_data", [])
        has_only_full_provinces = (
            cleaned.get("es_usuario_provincial")
            and bool(scopes)
            and all(
                scope.get("municipio_id") is None and scope.get("localidad_id") is None
                for scope in scopes
            )
        )
        if not has_only_full_provinces:
            self.add_error(
                "territorial_scopes",
                "El grupo SIMEPI - EGP requiere al menos una provincia completa.",
            )
        return cleaned


class DelegationScopeMixin:
    actor = None

    def _setup_delegation_fields(self):
        self.fields["grupos_asignables"] = forms.ModelMultipleChoiceField(
            queryset=Group.objects.all().order_by("name"),
            required=False,
            widget=forms.SelectMultiple(attrs={"class": "select2"}),
            label="Grupos que puede asignar",
            help_text=(
                "Define qué grupos podrá asignar este usuario al crear/editar "
                "otros usuarios."
            ),
        )
        self.fields["roles_asignables"] = forms.ModelMultipleChoiceField(
            queryset=ROLE_PERMISSION_QUERYSET,
            required=False,
            widget=forms.SelectMultiple(attrs={"class": "select2"}),
            label="Roles que puede asignar",
            help_text="Permisos auth.role_* delegables a terceros.",
        )

    def _apply_section_restrictions(self):
        """Habilita cada sección del ABM según los permisos del actor."""
        self.secciones_habilitadas = secciones_habilitadas(self.actor)
        habilitadas = self.secciones_habilitadas
        self.can_manage_mobile_access = SECCION_MOBILE_COMEDORES in habilitadas
        self.can_manage_territorial_comedor = SECCION_TERRITORIAL_COMEDOR in habilitadas
        self.can_manage_technical_teams = SECCION_EQUIPOS_TECNICOS in habilitadas
        self.can_manage_datacalle = SECCION_DATACALLE in habilitadas
        self.can_manage_inspecciones_escolares = (
            SECCION_INSPECCIONES_ESCOLARES in habilitadas
        )
        self.can_manage_direct_permissions = SECCION_ADMINISTRACION in habilitadas
        self.can_manage_delegation = SECCION_ADMINISTRACION in habilitadas

        for clave, campos in CAMPOS_POR_SECCION.items():
            if clave in habilitadas:
                continue
            for field_name in campos:
                if field_name in self.fields:
                    self.fields[field_name].disabled = True

    def _is_unrestricted_actor(self):
        return not self.actor or self.actor.is_superuser

    def _allowed_groups_for_actor(self):
        if self._is_unrestricted_actor():
            return Group.objects.all().order_by("name")

        return effective_delegatable_groups_qs(self.actor).order_by("name")

    def _allowed_roles_for_actor(self):
        if self._is_unrestricted_actor():
            return ROLE_PERMISSION_QUERYSET

        profile = getattr(self.actor, "profile", None)
        if not profile:
            return Permission.objects.none()
        return profile.roles_asignables.filter(
            content_type__app_label="auth",
            codename__startswith="role_",
        ).order_by("name")

    def _scope_assignable_fields_for_actor(self):
        allowed_groups = self._allowed_groups_for_actor()
        allowed_roles = self._allowed_roles_for_actor()
        all_permissions = Permission.objects.select_related("content_type").order_by(
            "content_type__app_label",
            "name",
        )

        # El campo de grupos debe MOSTRAR los grupos actuales del usuario aunque
        # estén fuera del alcance del actor; el alcance real de edición se valida
        # y se preserva por separado (un actor con alcance no puede quitar grupos
        # que no administra). user_permissions ya muestra el catálogo completo.
        if self.instance and self.instance.pk:
            groups_field_qs = (allowed_groups | self.instance.groups.all()).distinct()
        else:
            groups_field_qs = allowed_groups

        self.fields["groups"].queryset = groups_field_qs
        self.fields["user_permissions"].queryset = all_permissions
        self.fields["grupos_asignables"].queryset = allowed_groups
        self.fields["roles_asignables"].queryset = allowed_roles

    def _init_delegation_fields(self, profile):
        if not profile:
            return
        self.fields["grupos_asignables"].initial = profile.grupos_asignables.all()
        self.fields["roles_asignables"].initial = profile.roles_asignables.filter(
            content_type__app_label="auth",
            codename__startswith="role_",
        )

    def _validate_selected_within_allowed(self, cleaned):
        if self._is_unrestricted_actor():
            return

        # Valores actuales del usuario: se permiten conservar aunque estén fuera
        # del alcance del actor (no se pueden AGREGAR nuevos fuera de alcance).
        original_group_ids = (
            set(self.instance.groups.values_list("id", flat=True))
            if self.instance and self.instance.pk
            else set()
        )
        original_perm_ids = (
            set(self.instance.user_permissions.values_list("id", flat=True))
            if self.instance and self.instance.pk
            else set()
        )

        allowed_group_ids = set(
            self._allowed_groups_for_actor().values_list("id", flat=True)
        )
        selected_group_ids = set(
            cleaned.get("groups", Group.objects.none()).values_list("id", flat=True)
        )
        selected_assignable_group_ids = set(
            cleaned.get("grupos_asignables", Group.objects.none()).values_list(
                "id", flat=True
            )
        )

        if not selected_group_ids.issubset(allowed_group_ids | original_group_ids):
            self.add_error(
                "groups",
                "Solo puede asignar grupos habilitados para su usuario.",
            )
        if not selected_assignable_group_ids.issubset(allowed_group_ids):
            self.add_error(
                "grupos_asignables",
                "Solo puede delegar grupos que usted mismo puede asignar.",
            )

        allowed_role_ids = set(
            self._allowed_roles_for_actor().values_list("id", flat=True)
        )
        selected_role_ids = set(
            cleaned.get("user_permissions", Permission.objects.none()).values_list(
                "id", flat=True
            )
        )
        selected_assignable_role_ids = set(
            cleaned.get("roles_asignables", Permission.objects.none()).values_list(
                "id", flat=True
            )
        )

        if not selected_role_ids.issubset(allowed_role_ids | original_perm_ids):
            self.add_error(
                "user_permissions",
                "Solo puede asignar roles habilitados para su usuario.",
            )
        if not selected_assignable_role_ids.issubset(allowed_role_ids):
            self.add_error(
                "roles_asignables",
                "Solo puede delegar roles que usted mismo puede asignar.",
            )

    @staticmethod
    def _clear_permission_caches(user):
        for attr in ("_perm_cache", "_user_perm_cache", "_group_perm_cache"):
            if hasattr(user, attr):
                delattr(user, attr)

    def _aplicar_grupos_y_permisos(self, user):
        """Asigna grupos y permisos directos preservando los que están fuera del
        alcance del actor: un actor con alcance administra solo lo habilitado y
        no puede quitar grupos/roles que no le corresponden. Un actor sin
        restricción (superusuario) asigna exactamente lo seleccionado."""
        selected_groups = self.cleaned_data.get("groups", [])
        selected_permissions = self.cleaned_data.get("user_permissions", [])

        if self._is_unrestricted_actor():
            user.groups.set(selected_groups)
            user.user_permissions.set(selected_permissions)
            return

        allowed_group_ids = set(
            self._allowed_groups_for_actor().values_list("id", flat=True)
        )
        allowed_role_ids = set(
            self._allowed_roles_for_actor().values_list("id", flat=True)
        )
        original_group_ids = set(user.groups.values_list("id", flat=True))
        original_permission_ids = set(
            user.user_permissions.values_list("id", flat=True)
        )
        selected_group_ids = {group.pk for group in selected_groups}
        selected_permission_ids = {perm.pk for perm in selected_permissions}

        final_group_ids = (selected_group_ids & allowed_group_ids) | (
            original_group_ids - allowed_group_ids
        )
        final_permission_ids = (selected_permission_ids & allowed_role_ids) | (
            original_permission_ids - allowed_role_ids
        )

        user.groups.set(list(final_group_ids))
        user.user_permissions.set(list(final_permission_ids))


class RelevadorCalleFormMixin:
    """Campos del rol "Relevador DataCalle" (SISOC - Mobile).

    Flag ``Profile.es_relevador_calle`` + rol en ``Profile.datacalle_rol`` +
    alcance por provincia en ``RelevadorCalleProvincia``.

    A diferencia del territorial de comedores, el relevador de DataCalle es un
    usuario *solo de la app*: no entra al backoffice (ver
    ``BackofficeAuthenticationForm.confirm_login_allowed``) y por eso es
    excluyente con los otros roles de SISOC - Mobile.
    """

    # Se enciende cuando el rol elegido chocaría con el alcance territorial que
    # el usuario ya tiene cargado: apaga la derivación y las validaciones que
    # dependen de ella, para que el operador lea un solo error y no tres.
    _conflicto_alcance_datacalle = False

    def _setup_relevador_calle_fields(self):
        # QA-0015: los tres roles de DataCalle no se eligen en el mismo lugar, y
        # eso es lo que confundía. El entrevistador se marca acá porque es un
        # usuario *sólo de la app*; el coordinador y el administrador son
        # usuarios del backoffice y salen del grupo, no de este campo.
        self.fields["es_relevador_calle"] = forms.BooleanField(
            required=False,
            label="Habilitar acceso a SISOC - Mobile DataCalle",
            help_text=(
                "Habilita el acceso a DataCalle para los tres roles. Elegí el "
                "rol acá abajo y el sistema arma el resto: le asigna el grupo "
                "('Coordinador DataCalle' o 'Administrador DataCalle') y el "
                "alcance territorial. Sólo el relevador queda fuera del "
                "backoffice."
            ),
        )
        self.fields["datacalle_rol"] = forms.ChoiceField(
            choices=[("", "---------")] + self._roles_datacalle_para_el_actor(),
            required=False,
            widget=forms.Select(attrs={"class": "select2"}),
            label="Rol en DataCalle",
            help_text=(
                "Administrador Nacional (todo el país), Coordinador Provincial "
                "(su provincia, entra al backoffice y a la app) o Relevador "
                "(sólo la app). Crear coordinadores y elegir provincia es "
                "exclusivo del Administrador Nacional."
            ),
        )
        self.fields["provincias_datacalle"] = forms.ModelMultipleChoiceField(
            queryset=Provincia.objects.all().order_by("nombre"),
            required=False,
            widget=forms.SelectMultiple(attrs={"class": "select2"}),
            label="Provincias",
            help_text="Provincias que releva este usuario en DataCalle.",
        )
        self._acotar_provincias_datacalle_al_actor()

    def _rol_datacalle_actual(self) -> str:
        """Rol que el perfil editado ya tiene (``""`` en un alta)."""
        instance = getattr(self, "instance", None)
        if instance is None or not getattr(instance, "pk", None):
            return ""
        profile = get_profile_or_none(instance)
        return getattr(profile, "datacalle_rol", "") or ""

    def _roles_datacalle_para_el_actor(self):
        """RN02: solo el Administrador Nacional crea roles superiores.

        Un coordinador da de alta relevadores de su provincia y nada mas.

        Dos matices que costaron caro:

        - El rol que el perfil **ya tiene** siempre viaja en las choices. Si no,
          el ``<select>`` no contiene el valor actual, el browser postea ``""``
          y el formulario se rechaza con "Seleccione una opción válida": un
          coordinador no podía ni corregirse el mail, y la única opción que la
          pantalla le ofrecía ("Relevador") lo degradaba a no-staff y lo dejaba
          fuera de SISOC sin vuelta atrás.
        - Sin actor es **fail-closed**. Antes devolvía los tres roles, de modo
          que cualquier camino que instanciara el formulario sin actor podía
          asignar el rol más alto. El superusuario y el administrador siguen
          viendo los tres.
        """
        actor = getattr(self, "actor", None)
        todos = list(Profile.DataCalleRol.choices)
        if getattr(actor, "is_superuser", False) or es_administrador_datacalle(actor):
            return todos
        permitidos = {Profile.DataCalleRol.ENTREVISTADOR, self._rol_datacalle_actual()}
        return [
            (codigo, etiqueta) for codigo, etiqueta in todos if codigo in permitidos
        ]

    def _acotar_provincias_datacalle_al_actor(self):
        """QA-0016: la provincia del entrevistador sale del coordinador.

        Un coordinador provincial no elige en qué provincia da de alta: se
        deriva de su alcance. Con una sola provincia el campo queda fijo y
        deshabilitado, así Django ignora lo que llegue por POST.
        """
        actor = getattr(self, "actor", None)
        if actor is None or getattr(actor, "is_superuser", False):
            return
        if SECCION_DATACALLE not in secciones_habilitadas(actor):
            # Sin la sección el campo queda deshabilitado con la provincia que
            # el perfil ya tiene; fijarla al alcance del actor la pisaría.
            return
        provincia_ids = get_full_province_scope_ids(actor)
        if not provincia_ids:
            return
        propias = Provincia.objects.filter(id__in=provincia_ids).order_by("nombre")
        self.fields["provincias_datacalle"].queryset = propias
        if len(provincia_ids) == 1:
            self._provincias_datacalle_fijas = list(provincia_ids)
            self.fields["provincias_datacalle"].initial = list(propias)
            self.fields["provincias_datacalle"].disabled = True
            self.fields["provincias_datacalle"].help_text = (
                "Se deriva de tu alcance territorial."
            )

    @staticmethod
    def _provincias_datacalle_del_perfil(profile):
        """Provincia que el perfil ya tiene, leída de donde vive según el rol.

        El entrevistador la tiene en ``RelevadorCalleProvincia`` y el
        coordinador en ``ProfileTerritorialScope``; el administrador es
        nacional y no tiene ninguna. Leer siempre la primera tabla dejaba el
        campo vacío al editar a un coordinador y el ``clean`` lo rechazaba por
        "Seleccione la provincia".
        """
        if profile.datacalle_rol == Profile.DataCalleRol.COORDINADOR:
            return get_full_province_scope_ids(profile)
        if profile.datacalle_rol == Profile.DataCalleRol.ADMINISTRADOR:
            return []
        return list(
            profile.relevador_calle_provincias.values_list("provincia_id", flat=True)
        )

    def _init_relevador_calle_fields(self, profile):
        if not profile:
            return
        self.fields["es_relevador_calle"].initial = profile.es_relevador_calle
        self.fields["datacalle_rol"].initial = profile.datacalle_rol
        actuales = self._provincias_datacalle_del_perfil(profile)
        fijas = getattr(self, "_provincias_datacalle_fijas", None)
        if not fijas:
            self.fields["provincias_datacalle"].initial = actuales
            return

        # El campo quedó fijo al alcance del actor, así que el initial es esa
        # provincia y nada más. Antes se unía con las que el perfil ya tuviera,
        # para no borrarle a un relevador una provincia que el actor no
        # administra; con RN01 —una sola provincia por usuario— esa unión daría
        # dos y bloquearía la edición. El caso que protegía tampoco deberia
        # existir: la RN03 limita al coordinador a su provincia y
        # `get_relevadores_administrables` ya se lo impone.
        self.fields["provincias_datacalle"].initial = fijas
        self.fields["provincias_datacalle"].queryset = Provincia.objects.filter(
            id__in=fijas
        ).order_by("nombre")

    def _clean_relevador_calle_fields(self, cleaned):
        es_relevador = cleaned.get("es_relevador_calle", False)
        provincias = cleaned.get("provincias_datacalle")

        if not es_relevador:
            cleaned["datacalle_rol"] = ""
            cleaned["provincias_datacalle"] = Provincia.objects.none()
            return cleaned

        rol = cleaned.get("datacalle_rol")
        if not rol:
            self.add_error(
                "datacalle_rol",
                "Seleccione el rol del relevador de DataCalle.",
            )

        if rol == Profile.DataCalleRol.ADMINISTRADOR:
            # El Administrador Nacional no tiene provincia: pedirle una y
            # después ignorarla sólo confunde al operador.
            cleaned["provincias_datacalle"] = Provincia.objects.none()
            provincias = cleaned["provincias_datacalle"]
        # RN01: exactamente una. El mensaje dice el porque, no solo el limite.
        elif not provincias:
            self.add_error(
                "provincias_datacalle",
                "Seleccione la provincia del usuario de DataCalle.",
            )
        elif len(provincias) > 1:
            self.add_error(
                "provincias_datacalle",
                "Un usuario de DataCalle pertenece a una sola provincia.",
            )

        # RN08: no alcanza con no ofrecer la opcion en el selector. Se rechaza
        # sólo cuando el rol *cambia* a uno que el actor no puede asignar:
        # reenviar el rol que el perfil ya tenía no es una escalada, y tratarlo
        # como tal dejaba a los coordinadores sin poder guardar su propio
        # registro.
        rol_actual = self._rol_datacalle_actual()
        permitidos = {codigo for codigo, _ in self._roles_datacalle_para_el_actor()}
        if rol and rol != rol_actual and rol not in permitidos:
            self.add_error(
                "datacalle_rol",
                "No tenes permiso para asignar ese rol de DataCalle.",
            )
        cleaned = self._validar_conflicto_alcance_datacalle(cleaned)
        if self._conflicto_alcance_datacalle:
            # Se rechaza el guardado entero: derivar acá sería justamente lo
            # que el error está impidiendo.
            return cleaned
        return self._derivar_alcance_datacalle(cleaned)

    def _alcance_territorial_guardado(self):
        """Alcance que el usuario **ya tiene** en el panel territorial.

        Se lee de la base y no del POST: la pantalla puede mandar el panel
        vacío (campos ``disabled``, un formulario parcial) y ese silencio no
        puede valer como "no tenía nada", porque es justo el caso en el que la
        derivación borraba provincias sin que nadie se enterara.

        Con ``es_usuario_provincial`` apagado las filas no restringen nada, así
        que no cuentan como alcance cargado.
        """
        instance = getattr(self, "instance", None)
        if instance is None or not getattr(instance, "pk", None):
            return []
        profile = get_profile_or_none(instance)
        if profile is None or not profile.es_usuario_provincial:
            return []
        return [
            (scope.provincia_id, scope.municipio_id, scope.localidad_id)
            for scope in profile.territorial_scopes.all()
        ]

    @staticmethod
    def _alcance_territorial_del_panel(cleaned):
        """Alcance que viene en este mismo POST desde el panel territorial."""
        if not cleaned.get("es_usuario_provincial"):
            return []
        return [
            (
                scope.get("provincia_id"),
                scope.get("municipio_id"),
                scope.get("localidad_id"),
            )
            for scope in cleaned.get("territorial_scopes_data") or []
        ]

    def _validar_conflicto_alcance_datacalle(self, cleaned):
        """Asignar un rol de DataCalle no puede pisar el alcance de los demás módulos.

        ``es_usuario_provincial`` y ``ProfileTerritorialScope`` son el panel
        territorial **genérico** del backoffice: lo comparten comedores,
        admisiones y SIMEPI. ``_derivar_alcance_datacalle`` los reescribe según
        el rol, así que un usuario con tres provincias al que se le asigna
        ``coordinador`` de Córdoba perdía Salta y Jujuy en todos esos módulos
        sin un solo mensaje, y uno al que se le asignaba ``administrador``
        quedaba irrestricto en todo el backoffice, no sólo en DataCalle.

        La decisión es rechazar, no pisar: el alcance existente se resuelve en
        una edición aparte, a la vista del operador. No hay conflicto cuando el
        alcance actual ya es exactamente el que el rol derivaría (el caso del
        coordinador que se reedita) ni cuando el usuario no tiene ninguno (el
        caso común del alta).
        """
        rol = cleaned.get("datacalle_rol")
        if rol not in (
            Profile.DataCalleRol.COORDINADOR,
            Profile.DataCalleRol.ADMINISTRADOR,
        ):
            return cleaned

        actuales = set(self._alcance_territorial_guardado()) | set(
            self._alcance_territorial_del_panel(cleaned)
        )
        if not actuales:
            return cleaned

        if rol == Profile.DataCalleRol.COORDINADOR:
            provincias = list(cleaned.get("provincias_datacalle") or [])
            elegida = provincias[0].pk if len(provincias) == 1 else None
            if elegida is not None and actuales == {(elegida, None, None)}:
                return cleaned

        self._conflicto_alcance_datacalle = True
        self.add_error("datacalle_rol", self._mensaje_conflicto_alcance(rol, actuales))
        return cleaned

    @staticmethod
    def _mensaje_conflicto_alcance(rol, actuales):
        """Mensaje accionable: qué tiene hoy, qué le pasaría y qué hacer."""
        provincia_ids = sorted({provincia_id for provincia_id, _m, _l in actuales})
        nombres = ", ".join(
            Provincia.objects.filter(id__in=provincia_ids)
            .order_by("nombre")
            .values_list("nombre", flat=True)
        )
        cantidad = len(provincia_ids)
        tiene = (
            f"Este usuario ya tiene alcance territorial propio en el backoffice: "
            f"{cantidad} "
            f"{'provincia' if cantidad == 1 else 'provincias'} ({nombres}), "
            "que también usan comedores, admisiones y SIMEPI."
        )
        if rol == Profile.DataCalleRol.ADMINISTRADOR:
            consecuencia = (
                " El Administrador Nacional de DataCalle no tiene alcance, así "
                "que asignarle ese rol se lo borraría y lo dejaría sin "
                "restricción territorial en todo el backoffice, no sólo en "
                "DataCalle."
            )
            arreglo = (
                " Quitale primero el alcance en el panel de alcance territorial, "
                "guardá ese cambio, y recién después convertilo en usuario de "
                "DataCalle."
            )
        else:
            solo_municipal = all(
                municipio_id or localidad_id
                for _p, municipio_id, localidad_id in actuales
            )
            if solo_municipal:
                consecuencia = (
                    " Su alcance actual es municipal y el Coordinador Provincial "
                    "de DataCalle necesita la provincia completa, así que "
                    "asignarle ese rol le ensancharía el acceso en esos módulos."
                )
            else:
                consecuencia = (
                    " Convertirlo en Coordinador Provincial de DataCalle le "
                    "dejaría una sola provincia y le sacaría el acceso a las "
                    "demás en esos módulos."
                )
            arreglo = (
                " Dejá su alcance en la provincia que va a coordinar (o vacío) "
                "en el panel de alcance territorial, guardá ese cambio, y recién "
                "después convertilo en usuario de DataCalle."
            )
        return tiene + consecuencia + arreglo

    def _derivar_alcance_datacalle(self, cleaned):
        """D1: el operador elige un rol y el sistema arma el alcance.

        Esto nunca se había implementado, y el agujero era grave: la provincia
        elegida se escribía en ``RelevadorCalleProvincia``, que sólo lee el
        entrevistador. Un coordinador creado por el formulario quedaba con
        ``es_usuario_provincial=False`` y sin ``ProfileTerritorialScope``, o
        sea **sin restricción** en el backoffice (veía, editaba, borraba y
        cerraba operativos de todo el país, con el equipo y sus DNI) y con
        alcance vacío en la app.

        Se corre después de las validaciones de rol y provincia, y pisa lo que
        haya dejado ``_clean_territorial_scope_fields``: el alcance de un
        usuario de DataCalle lo decide el rol, no el panel territorial.
        """
        rol = cleaned.get("datacalle_rol")
        if rol == Profile.DataCalleRol.COORDINADOR:
            provincias = list(cleaned.get("provincias_datacalle") or [])
            if len(provincias) != 1:
                return cleaned
            cleaned["es_usuario_provincial"] = True
            cleaned["territorial_scopes_data"] = [
                {
                    "provincia_id": provincias[0].pk,
                    "municipio_id": None,
                    "localidad_id": None,
                }
            ]
        elif rol == Profile.DataCalleRol.ADMINISTRADOR:
            # El alcance nacional es, literalmente, no tener alcance: así lo
            # leen `get_datacalle_provincia_ids` y `_provincia_ids_del_usuario`.
            cleaned["es_usuario_provincial"] = False
            cleaned["territorial_scopes_data"] = []
        return cleaned

    def _validar_provincia_unica_coordinador(self, cleaned):
        """RN01/D3 en el formulario: el coordinador tiene una provincia completa.

        El servicio la vuelve a validar al guardar (``validar_alcance_coordinador``);
        acá el error se muestra en el campo en vez de reventar la transacción.
        """
        if cleaned.get("datacalle_rol") != Profile.DataCalleRol.COORDINADOR:
            return cleaned
        if self._conflicto_alcance_datacalle:
            # El alcance no se derivó a propósito; repetir acá "le falta una
            # provincia completa" sólo taparía el error que explica por qué.
            return cleaned
        scopes = cleaned.get("territorial_scopes_data") or []
        completos = [
            scope
            for scope in scopes
            if not scope.get("municipio_id") and not scope.get("localidad_id")
        ]
        if len(completos) != 1 or not cleaned.get("es_usuario_provincial"):
            self.add_error(
                "provincias_datacalle",
                "Un Coordinador Provincial de DataCalle debe tener exactamente "
                "una provincia completa como alcance territorial.",
            )
        return cleaned

    def _sync_grupo_datacalle(self, user):
        """D1: el grupo del backoffice sale del rol, no de una carga manual.

        La ayuda del formulario promete que el sistema lo asigna solo; antes
        había que acordarse de tildar el grupo a mano y, si el operador no lo
        hacía, el coordinador entraba a SISOC sin permisos de DataCalle.

        La automatización tiene que ser simétrica: sólo agregaba, así que
        degradar un coordinador a relevador le dejaba puesto "Coordinador
        DataCalle", y destildar el acceso a DataCalle lo dejaba con el grupo y
        el rol vacío, o sea viendo y editando operativos en el backoffice sin
        tener ningún rol. Se tocan únicamente los dos grupos de DataCalle: el
        resto de los grupos los administra el operador.
        """
        grupos_por_rol = {
            Profile.DataCalleRol.COORDINADOR: "Coordinador DataCalle",
            Profile.DataCalleRol.ADMINISTRADOR: "Administrador DataCalle",
        }
        nombre = grupos_por_rol.get(self.cleaned_data.get("datacalle_rol"))
        sobrantes = [valor for valor in grupos_por_rol.values() if valor != nombre]
        a_quitar = Group.objects.filter(name__in=sobrantes)
        if a_quitar:
            user.groups.remove(*a_quitar)
        if not nombre:
            return
        grupo = Group.objects.filter(name=nombre).first()
        if grupo is not None:
            user.groups.add(grupo)

    def _sync_relevador_calle_provincias(self, profile):
        # ``RelevadorCalleProvincia`` es la tabla del entrevistador y de nadie
        # más: el coordinador tiene su provincia en ``ProfileTerritorialScope``
        # y el administrador no tiene ninguna. Escribir filas acá para los tres
        # roles era la mitad del bug de alcance, así que además se limpian las
        # que hubiera dejado un guardado anterior.
        rol = self.cleaned_data.get("datacalle_rol", "")
        if not profile.es_relevador_calle or rol != Profile.DataCalleRol.ENTREVISTADOR:
            profile.relevador_calle_provincias.all().delete()
            return
        selected_ids = {
            provincia.id
            for provincia in self.cleaned_data.get("provincias_datacalle") or []
        }
        existing_ids = set(
            profile.relevador_calle_provincias.values_list("provincia_id", flat=True)
        )
        to_delete = existing_ids - selected_ids
        if to_delete:
            profile.relevador_calle_provincias.filter(
                provincia_id__in=to_delete
            ).delete()
        for provincia_id in selected_ids - existing_ids:
            RelevadorCalleProvincia.objects.create(
                profile=profile, provincia_id=provincia_id
            )


class InspeccionesEscolaresFormMixin:
    """Campos de la sección "Inspecciones escolares" (PWA Sisoc Inspecciones).

    Flag ``Profile.es_inspector_escolar`` + rol en ``Profile.inspecciones_rol``,
    con el mismo patrón que DataCalle: el flag habilita la app y el rol decide
    qué puede hacer. El inspector es usuario sólo de la app (se crea sin acceso
    SISOC web ni backoffice); coordinación puede además entrar a SISOC para
    administrar el catálogo de escuelas y las asignaciones.
    """

    def _setup_inspecciones_escolares_fields(self):
        self.fields["es_inspector_escolar"] = forms.BooleanField(
            required=False,
            label="Pertenece a Inspecciones escolares",
            help_text="Habilita el acceso a la PWA Sisoc Inspecciones.",
        )
        self.fields["inspecciones_rol"] = forms.ChoiceField(
            choices=[("", "---------")] + list(Profile.InspeccionesRol.choices),
            required=False,
            widget=forms.Select(attrs={"class": "select2"}),
            label="Rol en Inspecciones escolares",
            help_text=(
                "Inspector: registra visitas y ve sólo sus actas (sólo la app). "
                "Coordinación: ve todas las actas y borradores y administra el "
                "catálogo de escuelas y las asignaciones."
            ),
        )

    def _init_inspecciones_escolares_fields(self, profile):
        if not profile:
            return
        self.fields["es_inspector_escolar"].initial = profile.es_inspector_escolar
        self.fields["inspecciones_rol"].initial = profile.inspecciones_rol

    def _clean_inspecciones_escolares_fields(self, cleaned):
        if not cleaned.get("es_inspector_escolar", False):
            cleaned["inspecciones_rol"] = ""
            return cleaned
        if not cleaned.get("inspecciones_rol"):
            self.add_error(
                "inspecciones_rol",
                "Elegí el rol del usuario en Inspecciones escolares.",
            )
        return cleaned

    def _es_inspector_solo_app(self) -> bool:
        return bool(
            self.cleaned_data.get("es_inspector_escolar")
            and self.cleaned_data.get("inspecciones_rol")
            == Profile.InspeccionesRol.INSPECTOR
        )

    def _apply_inspecciones_escolares_to_profile(self, profile):
        profile.es_inspector_escolar = self.cleaned_data.get(
            "es_inspector_escolar", False
        )
        profile.inspecciones_rol = (
            self.cleaned_data.get("inspecciones_rol", "")
            if profile.es_inspector_escolar
            else ""
        )


class GroupForm(forms.ModelForm):
    permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.select_related("content_type").order_by(
            "content_type__app_label", "name"
        ),
        required=False,
        widget=FilteredSelectMultiple("Permisos", is_stacked=False),
        label="Permisos (roles)",
        help_text=(
            "Selecciona los permisos del grupo. "
            "Estos permisos se aplican a todos los usuarios del grupo."
        ),
    )

    class Meta:
        model = Group
        fields = ["name", "permissions"]

    def clean_name(self):
        name = (self.cleaned_data.get("name") or "").strip()
        if not name:
            raise forms.ValidationError("Este campo es obligatorio.")

        qs = Group.objects.filter(name__iexact=name)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Ya existe un grupo con ese nombre.")
        return name


class BulkCredentialsUploadForm(forms.Form):
    tipo_envio = forms.ChoiceField(
        label="Tipo de envio",
        choices=(),
        initial="standard",
        widget=forms.Select(attrs={"class": "form-control"}),
        help_text="Seleccione el tipo de envio para descargar la plantilla correcta.",
    )
    archivo = forms.FileField(
        label="Archivo Excel",
        validators=[FileExtensionValidator(["xlsx"])],
        widget=forms.ClearableFileInput(attrs={"accept": ".xlsx"}),
        help_text="Cargue un archivo .xlsx con el formato esperado para el tipo de envio seleccionado.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tipo_envio"].choices = get_bulk_credentials_send_type_choices()


class UserImportForm(forms.Form):
    archivo = forms.FileField(
        label="Archivo Excel",
        validators=[FileExtensionValidator(["xlsx"])],
        widget=forms.ClearableFileInput(attrs={"accept": ".xlsx"}),
        help_text=(
            "Archivo .xlsx con columnas: Username, Nombre, Apellido, Correo, "
            "Permisos, Provincias, Rol, Organizaciones, Comedores."
        ),
    )
    enviar_credenciales = forms.BooleanField(
        label="Enviar credenciales por email",
        required=False,
        initial=True,
        help_text="Si esta marcado, se enviara un email con usuario y contrasena temporal a cada usuario creado.",
    )
    es_pwa = forms.BooleanField(
        label="Usuarios de la PWA",
        required=False,
        initial=False,
        help_text="Los usuarios importados son usuarios de la app movil (PWA).",
    )
