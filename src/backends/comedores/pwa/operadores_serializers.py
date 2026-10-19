"""Serializers de operadores de Espacios comunitarios."""

from rest_framework import serializers

from iam.services import get_effective_permission_codes
from pwa.models import AccesoComedorPWA


class OperadorCreateSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    comedor_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=False,
    )
    permission_codes = serializers.ListField(
        child=serializers.CharField(max_length=150),
        required=False,
        allow_empty=True,
    )

    def _raise_read_only(self):
        raise NotImplementedError("Serializer de solo lectura.")

    def create(self, validated_data):
        return self._raise_read_only()

    def update(self, instance, validated_data):
        return self._raise_read_only()


class OperadorPermissionsUpdateSerializer(serializers.Serializer):
    permission_codes = serializers.ListField(
        child=serializers.CharField(max_length=150),
        required=False,
        allow_empty=True,
    )

    def _raise_read_only(self):
        raise NotImplementedError("Serializer de solo lectura.")

    def create(self, validated_data):
        return self._raise_read_only()

    def update(self, instance, validated_data):
        return self._raise_read_only()


class OperadorListSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="user_id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    creado_por_id = serializers.IntegerField(source="creado_por.id", read_only=True)
    creado_por_username = serializers.CharField(
        source="creado_por.username",
        read_only=True,
    )
    permission_codes = serializers.SerializerMethodField()
    comedor_ids = serializers.SerializerMethodField()

    class Meta:
        model = AccesoComedorPWA
        fields = (
            "id",
            "username",
            "email",
            "creado_por_id",
            "creado_por_username",
            "permission_codes",
            "comedor_ids",
            "activo",
            "fecha_creacion",
        )

    def get_permission_codes(self, obj):
        return sorted(get_effective_permission_codes(obj.user))

    def get_comedor_ids(self, obj):
        return sorted(
            obj.user.accesos_pwa.filter(
                rol=AccesoComedorPWA.ROL_OPERADOR,
                activo=True,
            ).values_list("comedor_id", flat=True)
        )


class OperadorCreateResponseSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="user_id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    comedor_id = serializers.IntegerField(read_only=True)
    creado_por_id = serializers.IntegerField(source="creado_por.id", read_only=True)
    creado_por_username = serializers.CharField(
        source="creado_por.username",
        read_only=True,
    )
    permission_codes = serializers.SerializerMethodField()
    comedor_ids = serializers.SerializerMethodField()

    class Meta:
        model = AccesoComedorPWA
        fields = (
            "id",
            "username",
            "email",
            "comedor_id",
            "comedor_ids",
            "creado_por_id",
            "creado_por_username",
            "permission_codes",
            "rol",
            "activo",
        )

    def get_permission_codes(self, obj):
        return sorted(get_effective_permission_codes(obj.user))

    def get_comedor_ids(self, obj):
        return sorted(
            obj.user.accesos_pwa.filter(
                rol=AccesoComedorPWA.ROL_OPERADOR,
                activo=True,
            ).values_list("comedor_id", flat=True)
        )
