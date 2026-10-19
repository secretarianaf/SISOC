from rest_framework import serializers

from iam.services import get_effective_permission_codes, get_effective_role_names
from users.credentials import LoginSerializer
from users.credentials import (
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    PasswordChangeRequiredSerializer,
)
from users.services_territorial_comedor import get_territorial_comedor_provincias
from users.profile_utils import get_profile_or_none
from users.services_datacalle import (
    get_datacalle_rol,
    get_relevador_calle_provincias,
)
from users.services_inspecciones import get_inspecciones_rol
from users.territorial_scope import serialize_profile_scopes


class UserContextSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
    first_name = serializers.CharField(read_only=True)
    last_name = serializers.CharField(read_only=True)
    is_superuser = serializers.BooleanField(read_only=True)
    is_staff = serializers.BooleanField(read_only=True)
    groups = serializers.SerializerMethodField()
    profile = serializers.SerializerMethodField()
    scope = serializers.SerializerMethodField()
    pwa = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()
    espacios_comunitarios_disponible = serializers.SerializerMethodField()

    def _raise_read_only(self):
        raise NotImplementedError("Serializer de solo lectura.")

    def create(self, validated_data):
        return self._raise_read_only()

    def update(self, instance, validated_data):
        return self._raise_read_only()

    def get_groups(self, obj):
        if not getattr(obj, "is_authenticated", False):
            return []
        return list(obj.groups.values_list("name", flat=True))

    def get_profile(self, obj):
        profile = get_profile_or_none(obj)
        if not profile:
            return None
        return {
            "rol": profile.rol,
            "provincia_id": profile.provincia_id,
            "territorial_scopes": serialize_profile_scopes(profile),
            "es_usuario_provincial": profile.es_usuario_provincial,
            "es_coordinador": profile.es_coordinador,
            "es_territorial_comedor": profile.es_territorial_comedor,
            "territorial_comedor_provincias": get_territorial_comedor_provincias(obj),
            "es_relevador_calle": profile.es_relevador_calle,
            "datacalle_rol": get_datacalle_rol(obj),
            "datacalle_provincias": get_relevador_calle_provincias(obj),
            "es_inspector_escolar": profile.es_inspector_escolar,
            "inspecciones_rol": get_inspecciones_rol(obj),
            "duplas_asignadas": self.context.get("espacios", {}).get(
                "duplas_asignadas", []
            ),
        }

    def get_scope(self, obj):
        if not getattr(obj, "is_authenticated", False):
            return {}
        espacios = self.context.get("espacios", {})
        profile = get_profile_or_none(obj)
        return {
            "is_coordinador": bool(
                getattr(get_profile_or_none(obj), "es_coordinador", False)
            ),
            "duplas_ids": espacios.get("duplas_ids", []),
            "es_usuario_provincial": getattr(profile, "es_usuario_provincial", False),
            "provincia_id": getattr(profile, "provincia_id", None),
            "territorial_scopes": serialize_profile_scopes(profile),
        }

    def get_pwa(self, obj):
        return self.context.get("espacios", {}).get(
            "pwa",
            {
                "is_pwa_user": False,
                "roles": [],
                "comedores_representados": [],
                "comedor_operador_id": None,
                "tipo_asociacion": None,
                "organizaciones_ids": [],
                "read_only": True,
                "must_change_password": bool(
                    getattr(get_profile_or_none(obj), "must_change_password", False)
                ),
            },
        )

    def get_espacios_comunitarios_disponible(self, obj) -> bool:
        return self.context.get("espacios_disponible", False)

    def get_roles(self, obj):
        if not getattr(obj, "is_authenticated", False):
            return []
        return sorted(get_effective_role_names(obj))

    def get_permissions(self, obj):
        if not getattr(obj, "is_authenticated", False):
            return []
        return sorted(get_effective_permission_codes(obj))


__all__ = [
    "LoginSerializer",
    "PasswordResetRequestSerializer",
    "PasswordResetConfirmSerializer",
    "PasswordChangeRequiredSerializer",
    "UserContextSerializer",
    "contexto_espacios_valido",
]


def contexto_espacios_valido(data):
    """Valida el DTO completo antes de declarar disponible el contexto remoto."""
    if not isinstance(data, dict) or not isinstance(data.get("pwa"), dict):
        return False
    pwa = data["pwa"]

    def ids(value):
        return isinstance(value, list) and all(
            isinstance(item, int) and not isinstance(item, bool) and item > 0
            for item in value
        )

    bools_ok = all(
        isinstance(pwa.get(key), bool)
        for key in ("is_pwa_user", "read_only", "must_change_password")
    )
    lists_ok = all(
        ids(pwa.get(key)) for key in ("comedores_representados", "organizaciones_ids")
    ) and all(ids(data.get(key)) for key in ("duplas_asignadas", "duplas_ids"))
    operador = pwa.get("comedor_operador_id")
    return (
        bools_ok
        and lists_ok
        and "comedor_operador_id" in pwa
        and (
            operador is None
            or (
                isinstance(operador, int)
                and not isinstance(operador, bool)
                and operador > 0
            )
        )
        and "tipo_asociacion" in pwa
        and (pwa["tipo_asociacion"] is None or isinstance(pwa["tipo_asociacion"], str))
        and isinstance(pwa.get("roles"), list)
        and all(isinstance(role, str) for role in pwa["roles"])
    )
