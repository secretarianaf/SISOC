"""Validación común de credenciales, sin dependencias de programas."""

from django.contrib.auth import authenticate, password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed

from users.services_auth import get_user_by_uid


class LoginSerializer(serializers.Serializer):
    app = serializers.ChoiceField(
        choices=["siis"],
        required=False,
        help_text="SIIS envía app=siis y API key. Omitir app conserva el login legacy.",
    )
    username = serializers.CharField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def create(self, validated_data):
        raise NotImplementedError("Serializer de solo lectura.")

    def update(self, instance, validated_data):
        raise NotImplementedError("Serializer de solo lectura.")

    def validate(self, attrs):
        user = authenticate(
            username=attrs.get("username"), password=attrs.get("password")
        )
        if not user or not user.is_active:
            raise AuthenticationFailed("Credenciales inválidas.")
        attrs["user"] = user
        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    username = serializers.CharField(required=True, max_length=150)

    def _raise_read_only(self):
        raise NotImplementedError("Serializer de solo lectura.")

    def create(self, validated_data):
        return self._raise_read_only()

    def update(self, instance, validated_data):
        return self._raise_read_only()

    def validate(self, attrs):
        email = (attrs.get("email") or "").strip()
        username = (attrs.get("username") or "").strip()

        attrs["username"] = username
        attrs["email"] = email
        return attrs


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)

    def _raise_read_only(self):
        raise NotImplementedError("Serializer de solo lectura.")

    def create(self, validated_data):
        return self._raise_read_only()

    def update(self, instance, validated_data):
        return self._raise_read_only()

    def validate(self, attrs):
        uid = attrs.get("uid")
        user = get_user_by_uid(uid)
        if not user:
            raise serializers.ValidationError({"detail": "Token inválido o expirado."})

        try:
            password_validation.validate_password(attrs.get("new_password"), user=user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(
                {"new_password": list(getattr(exc, "messages", [str(exc)]))}
            ) from exc
        return attrs


class PasswordChangeRequiredSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)

    def _raise_read_only(self):
        raise NotImplementedError("Serializer de solo lectura.")

    def create(self, validated_data):
        return self._raise_read_only()

    def update(self, instance, validated_data):
        return self._raise_read_only()

    def validate(self, attrs):
        user = self.context["request"].user
        try:
            password_validation.validate_password(attrs.get("new_password"), user=user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(
                {"new_password": list(getattr(exc, "messages", [str(exc)]))}
            ) from exc
        return attrs
