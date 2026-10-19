"""Clasifica efectos del POST en el servidor; nunca confía en un flag de UI."""

from django.contrib.auth.models import Group, Permission

from core.constants import GROUP_INHERITANCE
from core.permissions.registry import (
    LEGACY_ALIAS_TO_PERMISSION_CODES,
    build_legacy_permission_code,
    permission_codes_for_bootstrap_group,
)
from users.bootstrap.groups_seed import (
    permission_codes_for_bootstrap_group as seeded_group_codes,
)
from users.form_sections import CAMPOS_POR_SECCION
from users.profile_utils import get_profile_or_none
from users.secciones_usuario import SECCIONES_COMEDORES

DOMAIN_FIELDS = frozenset(
    name for section in SECCIONES_COMEDORES for name in CAMPOS_POR_SECCION[section]
)
DOMAIN_APPS = frozenset(
    {
        "comedores",
        "pwa",
        "duplas",
        "admisiones",
        "relevamientos",
        "acompanamientos",
        "rendicioncuentasfinal",
        "rendicioncuentasmensual",
        "expedientespagos",
        "importarexpediente",
        "intervenciones",
        "gestion_organizaciones",
        "historial",
        "comunicados",
    }
)


def _permiso_requiere_dominio(code):
    app, _, codename = code.partition(".")
    if app in DOMAIN_APPS:
        return True
    # Un rol auth arbitrario puede ampliar capacidades de Espacios. No inferir
    # independencia por el app_label de su content type.
    independent_roles = {
        "role_usuarios_seccion_datacalle",
        "role_usuarios_seccion_inspecciones_escolares",
    }
    return (
        app == "auth"
        and codename.startswith("role_")
        and codename not in independent_roles
    )


def _grupo_requiere_dominio(group, visited=None):
    visited = set() if visited is None else visited
    if group.name in visited:
        return False
    visited.add(group.name)
    codes = set(permission_codes_for_bootstrap_group(group.name))
    codes.update(
        f"{app}.{code}"
        for app, code in group.permissions.values_list(
            "content_type__app_label", "codename"
        )
    )
    declared = set(
        seeded_group_codes(group.name)
        or LEGACY_ALIAS_TO_PERMISSION_CODES.get(group.name, ())
    )
    automatic_role = build_legacy_permission_code(group.name)
    if declared and automatic_role not in declared:
        # Sólo el alias automático de un grupo conocido y de efectos
        # comprobables. Un rol arbitrario o un Administrador sigue bloqueado.
        codes.discard(automatic_role)
    if any(_permiso_requiere_dominio(code) for code in codes):
        return True
    for inherited in Group.objects.filter(
        name__in=GROUP_INHERITANCE.get(group.name, ())
    ):
        if _grupo_requiere_dominio(inherited, visited):
            return True
    return False


def _ids(data, field):
    values = data.getlist(field) if hasattr(data, "getlist") else data.get(field, [])
    if not isinstance(values, (list, tuple)):
        values = [values]
    return {int(value) for value in values}


def operacion_requiere_espacios(data, instance=None):
    """Campos explícitos y efectos indirectos; omitir no significa revocar."""
    return (
        bool(DOMAIN_FIELDS.intersection(data))
        or _permission_changes_require_domain(data, instance)
        or (instance is not None and _profile_changes_require_domain(data, instance))
    )


def _permission_changes_require_domain(data, instance):
    for field, model, relation in (
        ("groups", Group, "groups"),
        ("grupos_asignables", Group, None),
        ("user_permissions", Permission, "user_permissions"),
        ("roles_asignables", Permission, None),
    ):
        if field not in data:
            continue
        try:
            selected = _ids(data, field)
        except (ValueError, TypeError):
            return True
        original = set()
        if instance is not None and relation:
            original = set(getattr(instance, relation).values_list("id", flat=True))
        elif instance is not None:
            profile = get_profile_or_none(instance)
            if profile is not None:
                original = set(getattr(profile, field).values_list("id", flat=True))
        changed = selected ^ original
        for item in model.objects.filter(pk__in=changed):
            if model is Group:
                if _grupo_requiere_dominio(item):
                    return True
            elif _permiso_requiere_dominio(
                f"{item.content_type.app_label}.{item.codename}"
            ):
                return True
    return False


def _profile_changes_require_domain(data, instance):
    profile = get_profile_or_none(instance)
    # Sin consultar el dueño no es posible excluir invariantes de usuarios
    # mixtos (p.ej. operador exclusivo). Bloquear sólo estas mutaciones.
    for field in (
        "es_relevador_calle",
        "datacalle_rol",
        "es_inspector_escolar",
        "inspecciones_rol",
        "es_usuario_provincial",
        "territorial_scopes",
    ):
        if field not in data:
            continue
        if field == "territorial_scopes":
            if _scope_changed(data[field], profile):
                return True
            continue
        current = getattr(profile, field, None)
        proposed = data[field]
        if isinstance(current, bool):
            proposed = str(proposed).lower() in {"1", "true", "on", "yes"}
        if proposed != current:
            return True
    if "provincia" in data and str(data["provincia"] or "") != str(
        getattr(profile, "provincia_id", "") or ""
    ):
        return True
    if (
        "provincias_datacalle" in data
        and getattr(profile, "datacalle_rol", "") == "coordinador"
    ):
        from users.territorial_scope import (
            get_full_province_scope_ids,
        )  # pylint: disable=import-outside-toplevel

        try:
            return _ids(data, "provincias_datacalle") != set(
                get_full_province_scope_ids(profile)
            )
        except (ValueError, TypeError):
            return True
    return False


def _scope_changed(raw_value, profile):
    import json  # pylint: disable=import-outside-toplevel
    from users.territorial_scope import (
        serialize_profile_scopes,
    )  # pylint: disable=import-outside-toplevel

    try:
        return json.loads(raw_value or "[]") != serialize_profile_scopes(profile)
    except (ValueError, TypeError):
        return True
