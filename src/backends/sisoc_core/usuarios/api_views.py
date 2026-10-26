import logging
from collections.abc import Mapping

from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    PolymorphicProxySerializer,
    extend_schema,
    inline_serializer,
)
from django.core.exceptions import PermissionDenied
from django.db import transaction
from rest_framework import serializers, status, viewsets
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from usuarios.api_serializers import (
    LoginSerializer,
    PasswordChangeRequiredSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    UserContextSerializer,
    contexto_espacios_valido,
)
from usuarios.auth_audit import (
    EVENTO_LOGIN_ERROR,
    EVENTO_LOGIN_OK,
    EVENTO_LOGOUT,
    EVENTO_ME_OK,
    RESULTADO_ERROR,
    RESULTADO_OK,
    registrar_evento_auth,
)
from usuarios.services_password_reset_pwa import request_password_reset_for_identity
from usuarios.services_siis import SIISUserResponseSerializer
from core.internal_services import pedir_json_interno

from users.rate_limits import hit_rate_limit
from users.services_auth import (
    change_password_for_authenticated_user,
    confirm_password_reset,
)
from users.services_datacalle import tiene_acceso_datacalle
from users.services_inspecciones import tiene_acceso_inspecciones
from users.services_territorial_comedor import is_territorial_comedor_user

logger = logging.getLogger("django")


@extend_schema(tags=["Auth"])
class UserLoginViewSet(viewsets.ViewSet):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        request=LoginSerializer,
        parameters=[
            OpenApiParameter(
                name="Authorization",
                location=OpenApiParameter.HEADER,
                type=str,
                description="Api-Key <clave válida>, obligatoria solo para app=siis.",
            )
        ],
        responses={
            200: PolymorphicProxySerializer(
                component_name="UserLoginResponse",
                resource_type_field_name=None,
                serializers=[
                    SIISUserResponseSerializer,
                    inline_serializer(
                        name="LegacyUserLoginResponse",
                        fields={
                            "token": serializers.CharField(),
                            "token_type": serializers.CharField(),
                            "user_id": serializers.IntegerField(),
                            "username": serializers.CharField(),
                        },
                    ),
                ],
            ),
            400: OpenApiResponse(description="Payload o aplicación inválidos."),
            401: OpenApiResponse(
                description="Credenciales inválidas o rechazo legacy."
            ),
            403: OpenApiResponse(description="SIIS: API key o habilitación inválidas."),
            503: OpenApiResponse(
                description="Espacios comunitarios no disponible; elegibilidad sin confirmar."
            ),
            429: OpenApiResponse(
                description="SIIS: demasiados intentos por identidad."
            ),
        },
    )
    def create(self, request):
        if not isinstance(request.data, Mapping):
            return Response(
                {"detail": "El cuerpo debe ser un objeto JSON."}, status=400
            )
        if request.data.get("app") == "siis":
            from usuarios.siis_api_views import siis_login

            return siis_login(request, self)
        if "app" in request.data:
            return Response({"detail": "Aplicación no admitida."}, status=400)
        serializer = LoginSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except (AuthenticationFailed, PermissionDenied) as exc:
            detail = (
                str(exc)
                if isinstance(exc, AuthenticationFailed)
                else "Credenciales inválidas."
            )
            response = Response(
                {"detail": detail},
                status=status.HTTP_401_UNAUTHORIZED,
            )
            registrar_evento_auth(
                request=request,
                evento=EVENTO_LOGIN_ERROR,
                resultado=RESULTADO_ERROR,
                username_intentado=request.data.get("username"),
                codigo_respuesta=response.status_code,
                motivo_error=detail,
            )
            return response
        user = serializer.validated_data["user"]
        # Las capacidades de los demás programas se resuelven en identidad.
        # No consultar Comedores como condición de éxito de esos usuarios.
        if not (
            tiene_acceso_datacalle(user)
            or tiene_acceso_inspecciones(user)
            or is_territorial_comedor_user(user)
        ):
            return self._login_espacios(request, user, serializer.validated_data)

        token, _ = Token.objects.get_or_create(user=user)
        response = Response(
            {
                "token": token.key,
                "token_type": "Token",
                "user_id": user.id,
                "username": user.username,
            },
            status=status.HTTP_200_OK,
        )
        registrar_evento_auth(
            request=request,
            evento=EVENTO_LOGIN_OK,
            resultado=RESULTADO_OK,
            user=user,
            username_intentado=request.data.get("username"),
            codigo_respuesta=response.status_code,
        )
        return response

    def _login_espacios(self, request, user, credentials):
        result = pedir_json_interno(
            request,
            "pwa",
            "/interno/espacios/login/",
            method="POST",
            data={
                "username": credentials["username"],
                "password": credentials["password"],
            },
        )
        if result.status == 200 and isinstance(result.data, dict):
            payload = result.data.get("login", {})
            if not isinstance(payload, dict):
                payload = {}
            if (
                payload.get("user_id") == user.id
                and payload.get("username") == user.username
                and payload.get("token_type") == "Token"
                and isinstance(payload.get("token"), str)
                and Token.objects.filter(key=payload["token"], user=user).exists()
            ):
                registrar_evento_auth(
                    request=request,
                    evento=EVENTO_LOGIN_OK,
                    resultado=RESULTADO_OK,
                    user=user,
                    username_intentado=user.username,
                    codigo_respuesta=200,
                    contexto=result.data.get("pwa"),
                )
                return Response(
                    {
                        key: payload[key]
                        for key in ("token", "token_type", "user_id", "username")
                    }
                )
        code = 401 if result.status == 401 else 503
        detail = (
            "Este usuario no tiene acceso PWA activo."
            if code == 401
            else "Espacios comunitarios no está disponible. Intente nuevamente."
        )
        registrar_evento_auth(
            request=request,
            evento=EVENTO_LOGIN_ERROR,
            resultado=RESULTADO_ERROR,
            user=user,
            username_intentado=user.username,
            codigo_respuesta=code,
            motivo_error=detail,
        )
        return Response({"detail": detail}, status=code)


@extend_schema(tags=["Auth"])
class UserLogoutViewSet(viewsets.ViewSet):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(request=None)
    def create(self, request):
        token = getattr(request, "auth", None)
        if isinstance(token, Token):
            token.delete()
        else:
            Token.objects.filter(user=request.user).delete()
        response = Response({"detail": "Logout exitoso."}, status=status.HTTP_200_OK)
        registrar_evento_auth(
            request=request,
            evento=EVENTO_LOGOUT,
            resultado=RESULTADO_OK,
            user=request.user,
            codigo_respuesta=response.status_code,
        )
        return response


@extend_schema(tags=["Auth"])
class UserContextViewSet(viewsets.ViewSet):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=UserContextSerializer)
    def list(self, request):
        result = pedir_json_interno(request, "pwa", "/interno/espacios/contexto/")
        data = result.data
        available = result.status == 200 and contexto_espacios_valido(data)
        if not available:
            logger.warning(
                "Contexto de Espacios no disponible para user_id=%s", request.user.pk
            )
        payload = UserContextSerializer(
            request.user,
            context={
                "espacios": data if available else {},
                "espacios_disponible": available,
            },
        ).data
        response = Response(payload, status=status.HTTP_200_OK)
        registrar_evento_auth(
            request=request,
            evento=EVENTO_ME_OK,
            resultado=RESULTADO_OK,
            user=request.user,
            codigo_respuesta=response.status_code,
            contexto=data["pwa"] if available else None,
        )
        return response


@extend_schema(tags=["Auth"])
class PasswordResetRequestViewSet(viewsets.ViewSet):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(request=PasswordResetRequestSerializer)
    def create(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ip = request.META.get("REMOTE_ADDR", "anon")
        email = serializer.validated_data.get("email")
        username = serializer.validated_data.get("username")
        identity_value = f"{username}:{email}".lower()
        if hit_rate_limit(
            scope="password_reset_request",
            identity=f"{ip}:{identity_value}",
            limit=5,
            window_seconds=900,
        ):
            return Response(
                {
                    "detail": (
                        "Demasiados intentos. Intente nuevamente en unos minutos."
                    )
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        request_password_reset_for_identity(
            username=username,
            email=email,
            request=request,
        )
        return Response(
            {
                "detail": (
                    "Si los datos son correctos, recibirás un enlace de recuperación."
                )
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Auth"])
class PasswordResetConfirmViewSet(viewsets.ViewSet):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(request=PasswordResetConfirmSerializer)
    @transaction.atomic
    def create(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ip = request.META.get("REMOTE_ADDR", "anon")
        if hit_rate_limit(
            scope="password_reset_confirm",
            identity=ip,
            limit=10,
            window_seconds=900,
        ):
            return Response(
                {
                    "detail": (
                        "Demasiados intentos. Intente nuevamente en unos minutos."
                    )
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        user = confirm_password_reset(
            uid=serializer.validated_data["uid"],
            token=serializer.validated_data["token"],
            new_password=serializer.validated_data["new_password"],
        )
        if not user:
            return Response(
                {"detail": "Token inválido o expirado."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        Token.objects.filter(user=user).delete()
        return Response(
            {"detail": "Contraseña actualizada correctamente."},
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Auth"])
class PasswordChangeRequiredViewSet(viewsets.ViewSet):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(request=PasswordChangeRequiredSerializer)
    @transaction.atomic
    def create(self, request):
        serializer = PasswordChangeRequiredSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        profile = getattr(request.user, "profile", None)
        if not getattr(profile, "must_change_password", False):
            return Response(
                {"detail": "El usuario no requiere cambio obligatorio de contraseña."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        change_password_for_authenticated_user(
            user=request.user,
            new_password=serializer.validated_data["new_password"],
        )
        return Response(
            {"detail": "Contraseña actualizada correctamente."},
            status=status.HTTP_200_OK,
        )
