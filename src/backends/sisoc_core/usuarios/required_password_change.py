"""Shared web-only action for the existing mandatory password form."""

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.utils import timezone


def complete_required_password_change(request, form):
    """Preserve the legacy save, flags, session and notice sequence exactly."""
    user = form.save()
    profile = getattr(user, "profile", None)
    if profile:
        profile.must_change_password = False
        profile.password_changed_at = timezone.now()
        profile.initial_password_expires_at = None
        profile.password_reset_requested_at = None
        profile.temporary_password_plaintext = None
        profile.save(
            update_fields=[
                "must_change_password",
                "password_changed_at",
                "initial_password_expires_at",
                "password_reset_requested_at",
                "temporary_password_plaintext",
            ]
        )
    update_session_auth_hash(request, user)
    messages.success(request, "Contraseña actualizada correctamente.")
    return user
