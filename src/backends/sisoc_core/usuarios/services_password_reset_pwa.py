"""Recupero de contraseña para usuarios de las PWAs.

Sale de ``users.services_auth`` (kernel) porque necesita saber si el usuario
tiene acceso PWA, y eso es dominio del core (``pwa``).
"""

import logging

from django.contrib.auth import get_user_model
from django.utils import timezone

from pwa.services.accesos import is_pwa_user
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
    if not user or not is_pwa_user(user):
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
    if not user or not is_pwa_user(user):
        return

    reset_link = build_password_reset_link(user=user, request=request, front="pwa")
    try:
        send_password_reset_link(user=user, reset_link=reset_link)
        logger.info("Password reset PWA solicitado user_id=%s", user.id)
    except Exception:  # pragma: no cover - depende de backend externo
        logger.exception("Fallo enviando password reset PWA user_id=%s", user.id)
