"""Recupero de contraseña para usuarios de las PWAs.

Sale de ``users.services_auth`` (kernel) porque necesita saber si el usuario
tiene acceso PWA, y eso es dominio del core (``pwa``).
"""

import logging

from django.contrib.auth import get_user_model
from django.utils import timezone

from core.internal_services import pedir_json_interno
from users.services_datacalle import tiene_acceso_datacalle
from users.services_inspecciones import tiene_acceso_inspecciones
from users.profile_utils import get_profile_or_none
from users.services_territorial_comedor import is_territorial_comedor_user
from users.services_auth import build_password_reset_link, send_password_reset_link

logger = logging.getLogger("django")
User = get_user_model()


def request_password_reset_for_username(*, username: str) -> None:
    normalized_username = (username or "").strip()
    if not normalized_username:
        return

    user = (
        User.objects.filter(username__iexact=normalized_username, is_active=True)
        .select_related("profile")
        .first()
    )
    if not user:
        return

    profile = getattr(user, "profile", None)
    if not profile:
        return

    profile.password_reset_requested_at = timezone.now()
    profile.save(update_fields=["password_reset_requested_at"])
    logger.info("Password reset mobile solicitado user_id=%s", user.id)


def request_password_reset_for_identity(
    *, username: str, email: str, request=None
) -> None:
    normalized_username = (username or "").strip()
    normalized_email = (email or "").strip()
    if not normalized_username or not normalized_email:
        return

    user = (
        User.objects.filter(
            username__iexact=normalized_username,
            email__iexact=normalized_email,
            is_active=True,
        )
        .order_by("id")
        .first()
    )
    if not user:
        return
    profile = get_profile_or_none(user)
    central = (
        bool(getattr(profile, "acceso_web", False))
        or bool(getattr(profile, "acceso_siis", False))
        or tiene_acceso_datacalle(user)
        or tiene_acceso_inspecciones(user)
        or is_territorial_comedor_user(user)
    )
    try:
        if central:
            reset_link = build_password_reset_link(
                user=user, request=request, front="sisoc"
            )
            send_password_reset_link(user=user, reset_link=reset_link)
        else:
            result = pedir_json_interno(
                request,
                "pwa",
                "/api/users/password-reset/request/",
                method="POST",
                data={"username": normalized_username, "email": normalized_email},
            )
            if result.status != 200:
                logger.warning("Recupero de Espacios no disponible user_id=%s", user.pk)
        logger.info("Password reset PWA solicitado user_id=%s", user.id)
    except Exception:  # pragma: no cover - depende de backend externo
        logger.exception("Fallo enviando password reset PWA user_id=%s", user.id)
