"""Capacidades de Espacios consumidas por la identidad central."""

import logging

from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.internal_services import RespuestaInterna, registrar_servicio_interno
from pwa.services.accesos import get_pwa_context, is_pwa_user
from users.credentials import LoginSerializer, PasswordResetRequestSerializer
from users.rate_limits import hit_rate_limit
from users.profile_utils import get_profile_or_none
from users.services import UserPermissionService
from users.services_auth import build_password_reset_link, send_password_reset_link
from users.services_territorial_comedor import is_territorial_comedor_user

LOGIN_PATH = "/interno/espacios/login/"
CONTEXT_PATH = "/interno/espacios/contexto/"
RESET_PATH = "/api/users/password-reset/request/"
RESET_DETAIL = "Si los datos son correctos, recibirás un enlace de recuperación."


def login_espacios(_request, data):
    serializer = LoginSerializer(data=data)
    try:
        serializer.is_valid(raise_exception=True)
    except AuthenticationFailed:
        return RespuestaInterna(401, {"detail": "Credenciales inválidas."})
    user = serializer.validated_data["user"]
    if not (is_pwa_user(user) or is_territorial_comedor_user(user)):
        return RespuestaInterna(
            401, {"detail": "Este usuario no tiene acceso PWA activo."}
        )
    contexto = get_pwa_context(user)
    token, _ = Token.objects.get_or_create(user=user)
    return RespuestaInterna(
        200,
        {
            "login": {
                "token": token.key,
                "token_type": "Token",
                "user_id": user.id,
                "username": user.username,
            },
            "pwa": contexto,
        },
    )


def contexto_espacios(request, _data=None):
    user = request.user
    if not user.is_authenticated:
        return RespuestaInterna(401, None)
    profile = get_profile_or_none(user)
    _, duplas_ids = UserPermissionService.get_coordinador_duplas(user)
    return RespuestaInterna(
        200,
        {
            "pwa": get_pwa_context(user),
            "duplas_asignadas": (
                list(profile.duplas_asignadas.values_list("id", flat=True))
                if profile
                else []
            ),
            "duplas_ids": duplas_ids,
        },
    )


def recuperar_password_espacios(request, data):
    """Mismo contrato público antienumeración, ejecutado por su dueño."""
    user = (
        get_user_model()
        .objects.filter(
            username__iexact=(data.get("username") or "").strip(),
            email__iexact=(data.get("email") or "").strip(),
            is_active=True,
        )
        .first()
    )
    if user and is_pwa_user(user):
        link = build_password_reset_link(user=user, request=request, front="pwa")
        try:
            send_password_reset_link(user=user, reset_link=link)
        except Exception:  # Mantener respuesta antienumeración ante fallas del correo.
            logging.getLogger(__name__).exception(
                "Fallo enviando recupero de Espacios user_id=%s", user.pk
            )
    return RespuestaInterna(200, {"detail": RESET_DETAIL})


def registrar_servicios_identidad():
    registrar_servicio_interno(LOGIN_PATH, login_espacios)
    registrar_servicio_interno(CONTEXT_PATH, contexto_espacios)
    registrar_servicio_interno(RESET_PATH, recuperar_password_espacios)


@extend_schema(exclude=True)
class EspaciosLoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        result = login_espacios(request, request.data)
        return Response(result.data, status=result.status)


@extend_schema(exclude=True)
class EspaciosContextView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        result = contexto_espacios(request)
        return Response(result.data, status=result.status)


@extend_schema(exclude=True)
class EspaciosPasswordResetView(APIView):
    """El mismo contrato de recupero, alcanzable sólo en la red del dueño."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        identity = f"{data['username']}:{data['email']}".lower()
        if hit_rate_limit(
            scope="password_reset_request",
            identity=f"{request.META.get('REMOTE_ADDR', 'anon')}:{identity}",
            limit=5,
            window_seconds=900,
        ):
            return Response(
                {"detail": "Demasiados intentos. Intente nuevamente en unos minutos."},
                status=429,
            )
        result = recuperar_password_espacios(request, data)
        return Response(result.data, status=result.status)
