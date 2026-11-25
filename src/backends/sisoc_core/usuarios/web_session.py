"""Read-only prerequisites for the core's session-authenticated web APIs."""

from dataclasses import dataclass

from encuestas.services import get_rondas_pendientes_para_request
from users.profile_utils import get_profile_or_none, needs_profile_confirmation


@dataclass(frozen=True)
class WebAccess:
    """First unmet prerequisite, not a business permission or a stored result."""

    state: str
    required_action_url: str | None = None


def resolve_web_access(request) -> WebAccess:
    """Evaluate existing web controls in order, without repairing user state.

    Callers must separately enforce session authentication, action permissions
    and object scope. Dependency failures deliberately propagate: unavailable
    survey evaluation must never grant access by default.
    """
    user = getattr(request, "user", None)
    if (
        not user
        or not getattr(user, "is_authenticated", False)
        or not getattr(user, "is_active", False)
    ):
        return WebAccess("unauthenticated")

    profile = get_profile_or_none(user)
    if not getattr(profile, "acceso_web", False):
        return WebAccess("web_access_denied")
    if profile.must_change_password:
        return WebAccess("password_change_required", "/password/first-change/")
    if needs_profile_confirmation(user):
        return WebAccess("profile_confirmation_required", "/mi-cuenta/confirmar/")
    if any(
        ronda.encuesta.es_obligatoria
        for ronda in get_rondas_pendientes_para_request(request)
    ):
        return WebAccess("mandatory_survey_required", "/inicio/")
    return WebAccess("ready")
