"""Minimal session context composed only from the core's existing services."""

from dataclasses import asdict

from core.context_processors import footer_version
from core.templatetags.custom_filters import has_perm_code
from users.profile_utils import get_profile_or_none
from usuarios.web_navigation import build_web_navigation
from usuarios.web_session import resolve_web_access


def build_web_context(request):
    """Return private context, or None when there is no active session.

    Business APIs must independently re-evaluate prerequisites and permissions.
    This projection neither grants actions nor repairs incomplete profiles.
    """
    access = resolve_web_access(request)
    if access.state == "unauthenticated":
        return None

    user = request.user
    identity = None
    if access.state != "web_access_denied":
        profile = get_profile_or_none(user)
        identity = {
            "username": user.username,
            "display_name": user.get_full_name() or user.username,
            "avatar_initial": user.username[:1].upper(),
            "role_label": getattr(profile, "rol", None) or "-",
        }

    ready = access.state == "ready"
    capabilities = {
        "can_view": ready and has_perm_code(user, "insumos.view_insumo"),
        "show_management": ready and user.has_perm("insumos.add_insumo"),
        "show_categories": ready and user.has_perm("insumos.add_insumocategoria"),
    }
    return {
        "user": identity,
        "access": asdict(access),
        "navigation": build_web_navigation(request) if ready else [],
        "capabilities": {"insumos": capabilities},
        "footer_version_label": footer_version(request)["footer_version_label"],
    }
