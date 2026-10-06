"""Contrato server-to-server SIIS, separado de los tokens legacy."""

from collections.abc import Mapping

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.db import IntegrityError
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    inline_serializer,
)
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api_auth import HasAPIKey
from audittrail.context import audit_context
from users.rate_limits import hit_rate_limit
from usuarios.auth_audit import (
    EVENTO_LOGIN_ERROR,
    EVENTO_LOGIN_OK,
    RESULTADO_ERROR,
    RESULTADO_OK,
    registrar_evento_auth,
)
from usuarios.services_siis import (
    DUPLICATE_MESSAGE,
    TOKEN_MAX_AGE,
    SIISCreateSerializer,
    SIISUserResponseSerializer,
    account_exists,
    admin_from_token,
    create_account,
    issue_admin_token,
    require_access,
    user_payload,
)

API_KEY_HEADER = OpenApiParameter(
    name="Authorization",
    location=OpenApiParameter.HEADER,
    required=True,
    type=str,
    description="Api-Key <clave válida de SISOC>",
)
ADMIN_TOKEN_HEADER = OpenApiParameter(
    name="X-SIIS-Admin-Token",
    location=OpenApiParameter.HEADER,
    required=True,
    type=str,
    description="Token firmado emitido por SISOC; vence en 3600 segundos.",
)


def _rate_limited(request, scope, identity):
    ip = request.META.get("REMOTE_ADDR", "anon")
    return hit_rate_limit(
        scope=scope,
        identity=f"{ip}:{identity}",
        limit=10,
        window_seconds=300,
    )


def _limited_response():
    return Response(
        {"detail": "Demasiados intentos. Intente nuevamente en unos minutos."},
        status=429,
    )


def authenticate_siis(request, *, administrative=False):
    # Import here because the shared login dispatches to this module.
    from usuarios.api_views import LoginSerializer

    if not isinstance(request.data, Mapping):
        return None, Response(
            {"detail": "El cuerpo debe ser un objeto JSON."}, status=400
        )
    scope = "siis_admin_auth" if administrative else "siis_login"
    identity = str(request.data.get("username", "")).strip().lower()
    if _rate_limited(request, scope, identity):
        return None, _limited_response()
    serializer = LoginSerializer(data=request.data)
    try:
        serializer.is_valid(raise_exception=True)
    except (AuthenticationFailed, DjangoPermissionDenied):
        response = Response({"detail": "Credenciales inválidas."}, status=401)
        registrar_evento_auth(
            request=request,
            evento=EVENTO_LOGIN_ERROR,
            resultado=RESULTADO_ERROR,
            codigo_respuesta=401,
            motivo_error="Credenciales inválidas.",
        )
        return None, response
    user = serializer.validated_data["user"]
    require_access(user, administrative=administrative)
    registrar_evento_auth(
        request=request,
        evento=EVENTO_LOGIN_OK,
        resultado=RESULTADO_OK,
        user=user,
        codigo_respuesta=200,
    )
    return user, None


def siis_login(request, view):
    if not HasAPIKey().has_permission(request, view):
        return Response({"detail": "API key ausente o inválida."}, status=403)
    user, response = authenticate_siis(request)
    return response if response is not None else Response(user_payload(user))


class SIISAdminTokenView(APIView):
    authentication_classes = []
    permission_classes = [HasAPIKey]

    @extend_schema(
        tags=["SIIS"],
        parameters=[API_KEY_HEADER],
        request=inline_serializer(
            name="SIISAdminCredentials",
            fields={
                "username": serializers.CharField(),
                "password": serializers.CharField(
                    write_only=True, trim_whitespace=False
                ),
            },
        ),
        responses={
            200: inline_serializer(
                name="SIISAdminToken",
                fields={
                    "admin_token": serializers.CharField(),
                    "expires_in": serializers.IntegerField(),
                },
            ),
            400: OpenApiResponse(description="Campos obligatorios inválidos."),
            401: OpenApiResponse(
                description="Credenciales inválidas o cuenta inactiva."
            ),
            403: OpenApiResponse(
                description="API key, habilitación o permiso inválidos."
            ),
            429: OpenApiResponse(description="Demasiados intentos para la identidad."),
        },
    )
    def post(self, request):
        user, response = authenticate_siis(request, administrative=True)
        if response is not None:
            return response
        return Response(
            {"admin_token": issue_admin_token(user), "expires_in": TOKEN_MAX_AGE}
        )


class SIISUserCreateView(APIView):
    authentication_classes = []
    permission_classes = [HasAPIKey]

    @extend_schema(
        tags=["SIIS"],
        parameters=[API_KEY_HEADER, ADMIN_TOKEN_HEADER],
        request=SIISCreateSerializer,
        responses={
            201: SIISUserResponseSerializer,
            400: OpenApiResponse(
                description="Campos obligatorios o adicionales inválidos."
            ),
            401: OpenApiResponse(
                description="Token administrativo inválido o vencido."
            ),
            403: OpenApiResponse(
                description="API key o autorización administrativa inválida."
            ),
            409: inline_serializer(
                name="SIISAccountExists",
                fields={
                    "error": serializers.ChoiceField(choices=["account_exists"]),
                    "message": serializers.CharField(),
                },
            ),
            429: OpenApiResponse(description="Demasiadas altas para el administrador."),
        },
    )
    def post(self, request):
        actor = admin_from_token(request.headers.get("X-SIIS-Admin-Token", ""))
        if _rate_limited(request, "siis_create", actor.pk):
            return _limited_response()
        serializer = SIISCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if account_exists(data):
            return Response(
                {"error": "account_exists", "message": DUPLICATE_MESSAGE}, status=409
            )
        try:
            with audit_context(actor=actor, source="siis"):
                user = create_account(data)
        except IntegrityError:
            # Username retains its database uniqueness. Do not hide other failures.
            if account_exists(data):
                return Response(
                    {"error": "account_exists", "message": DUPLICATE_MESSAGE},
                    status=409,
                )
            raise
        return Response(user_payload(user), status=201)
