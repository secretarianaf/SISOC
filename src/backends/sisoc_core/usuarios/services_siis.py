"""Identidad y altas SIIS; los roles operativos pertenecen a SIIS."""

import re

from django.contrib.auth import get_user_model, password_validation
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import CharField, Value
from django.db.models.functions import Lower, Replace, Trim
from rest_framework import serializers
from rest_framework.exceptions import APIException, PermissionDenied

from users.profile_utils import get_profile_or_none
from users.models import Profile

TOKEN_SALT = "usuarios.siis.admin-create.v1"
TOKEN_MAX_AGE = 3600
DUPLICATE_MESSAGE = (
    "La cuenta ya existe. Solicitá al soporte de SISOC su habilitación para SIIS."
)


def user_payload(user):
    profile = get_profile_or_none(user)
    return {
        "id": user.pk,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "dni": getattr(profile, "dni", ""),
        "acceso_siis": bool(getattr(profile, "acceso_siis", False)),
    }


def require_access(user, *, administrative=False):
    if not user.is_active or not getattr(
        get_profile_or_none(user), "acceso_siis", False
    ):
        raise PermissionDenied("Este usuario no tiene acceso SIIS habilitado.")
    if administrative and not user.has_perm("auth.add_user"):
        raise PermissionDenied("No tiene permiso para crear usuarios.")


def issue_admin_token(user):
    require_access(user, administrative=True)
    return signing.dumps({"user_id": user.pk}, salt=TOKEN_SALT)


class InvalidAdminToken(APIException):
    status_code = 401
    default_detail = "Token administrativo inválido o vencido."


def admin_from_token(token):
    try:
        payload = signing.loads(token, salt=TOKEN_SALT, max_age=TOKEN_MAX_AGE)
        user = get_user_model().objects.get(pk=payload["user_id"])
    except (
        signing.BadSignature,
        KeyError,
        TypeError,
        ValueError,
        get_user_model().DoesNotExist,
    ) as exc:
        raise InvalidAdminToken() from exc
    require_access(user, administrative=True)
    return user


class SIISCreateSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    email = serializers.EmailField(max_length=254)
    dni = serializers.CharField(max_length=32, trim_whitespace=False)

    def create(self, validated_data):
        raise NotImplementedError("El servicio SIIS se encarga de persistir el alta.")

    def update(self, instance, validated_data):
        raise NotImplementedError("La API SIIS no modifica cuentas existentes.")

    def to_internal_value(self, data):
        if isinstance(data, dict) and set(data) - set(self.fields):
            raise serializers.ValidationError(
                {"detail": "Solo se admiten los seis campos del alta SIIS."}
            )
        return super().to_internal_value(data)

    def validate_password(self, value):
        if not value.strip():
            raise serializers.ValidationError("Este campo es obligatorio.")
        return value

    def validate_dni(self, value):
        value = value.replace(".", "").replace(" ", "")
        if not re.fullmatch(r"[0-9]{7,8}", value):
            raise serializers.ValidationError(
                "El DNI debe contener entre 7 y 8 dígitos."
            )
        return value

    def validate(self, attrs):
        candidate = get_user_model()(
            **{
                key: attrs[key]
                for key in ("username", "first_name", "last_name", "email")
            }
        )
        try:
            candidate.full_clean(exclude=["password"], validate_unique=False)
            password_validation.validate_password(attrs["password"], user=candidate)
        except ValidationError as exc:
            errors = (
                exc.message_dict
                if hasattr(exc, "message_dict")
                else {"password": exc.messages}
            )
            raise serializers.ValidationError(errors) from exc
        return attrs


class SIISUserResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    email = serializers.EmailField()
    dni = serializers.CharField()
    acceso_siis = serializers.BooleanField()


    def create(self, validated_data):
        raise NotImplementedError("Serializer de solo lectura.")

    def update(self, instance, validated_data):
        raise NotImplementedError("Serializer de solo lectura.")


def account_exists(data):
    users = get_user_model().objects.annotate(
        normalized_username=Lower(Trim("username")),
        normalized_email=Lower(Trim("email")),
    )
    if users.filter(normalized_username=data["username"].lower()).exists():
        return True
    if users.filter(normalized_email=data["email"].lower()).exists():
        return True
    normalized_dni = Replace(
        Replace("dni", Value("."), Value("")),
        Value(" "),
        Value(""),
        output_field=CharField(),
    )
    return (
        Profile.objects.annotate(normalized_dni=normalized_dni)
        .filter(normalized_dni=data["dni"])
        .exists()
    )


@transaction.atomic
def create_account(data):
    user = get_user_model().objects.create_user(
        **{
            key: data[key]
            for key in ("username", "password", "first_name", "last_name", "email")
        },
        is_active=True,
        is_staff=False,
        is_superuser=False,
    )
    profile = user.profile
    profile.dni = data["dni"]
    profile.acceso_siis = True
    profile.acceso_web = False
    profile.source = "siis"
    profile.save(update_fields=["dni", "acceso_siis", "acceso_web", "source"])
    return user
