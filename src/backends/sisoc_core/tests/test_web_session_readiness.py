"""Read-only web prerequisites shared by session context and INS-A APIs."""

from types import SimpleNamespace

import pytest
from django.contrib.auth.models import AnonymousUser, User
from django.test import RequestFactory

from users.models import Profile
from usuarios.web_session import resolve_web_access


def request_for_user(**profile_fields):
    user = User(username="synthetic_web_user", is_active=True)
    Profile(user=user, **profile_fields)
    request = RequestFactory().get("/api/web/session/")
    request.user = user
    return request


@pytest.mark.parametrize("user", [None, AnonymousUser(), User(is_active=False)])
def test_missing_or_inactive_session_cannot_read_web_context(user):
    request = RequestFactory().get("/api/web/session/")
    request.user = user

    result = resolve_web_access(request)

    assert result.state == "unauthenticated"
    assert result.required_action_url is None


@pytest.mark.parametrize(
    "access,password,confirmation,expected,url",
    [
        (False, False, False, "web_access_denied", None),
        (False, False, True, "web_access_denied", None),
        (False, True, False, "web_access_denied", None),
        (False, True, True, "web_access_denied", None),
        (True, True, False, "password_change_required", "/password/first-change/"),
        (True, True, True, "password_change_required", "/password/first-change/"),
        (True, False, True, "profile_confirmation_required", "/mi-cuenta/confirmar/"),
    ],
)
def test_prerequisites_keep_precedence_without_querying_surveys(
    access, password, confirmation, expected, url, monkeypatch
):
    request = request_for_user(
        acceso_web=access,
        must_change_password=password,
        needs_profile_confirmation=confirmation,
    )

    def unexpected_survey_read(_request):
        pytest.fail("Survey evaluation must follow earlier prerequisites.")

    monkeypatch.setattr(
        "usuarios.web_session.get_rondas_pendientes_para_request",
        unexpected_survey_read,
    )

    result = resolve_web_access(request)

    assert (result.state, result.required_action_url) == (expected, url)
    assert request.user.pk is None
    assert request.user.profile.pk is None


def test_missing_profile_is_denied_without_creating_one():
    request = request_for_user(acceso_web=True)
    request.user.profile = None

    result = resolve_web_access(request)

    assert (result.state, result.required_action_url) == ("web_access_denied", None)
    with pytest.raises(Profile.DoesNotExist):
        _ = request.user.profile


@pytest.mark.parametrize(
    "mandatory_flags,expected,url",
    [
        ([], "ready", None),
        ([False], "ready", None),
        ([True], "mandatory_survey_required", "/inicio/"),
        ([False, True], "mandatory_survey_required", "/inicio/"),
    ],
)
def test_only_pending_mandatory_surveys_block_ready(
    mandatory_flags, expected, url, monkeypatch
):
    request = request_for_user(
        acceso_web=True,
        must_change_password=False,
        needs_profile_confirmation=False,
    )
    rounds = [
        SimpleNamespace(encuesta=SimpleNamespace(es_obligatoria=flag))
        for flag in mandatory_flags
    ]
    monkeypatch.setattr(
        "usuarios.web_session.get_rondas_pendientes_para_request",
        lambda current: rounds if current is request else pytest.fail("Wrong actor"),
    )

    result = resolve_web_access(request)

    assert (result.state, result.required_action_url) == (expected, url)


def test_survey_failure_is_not_silently_reported_as_ready(monkeypatch):
    request = request_for_user(
        acceso_web=True,
        must_change_password=False,
        needs_profile_confirmation=False,
    )

    def unavailable(_request):
        raise RuntimeError("Synthetic survey dependency unavailable")

    monkeypatch.setattr(
        "usuarios.web_session.get_rondas_pendientes_para_request", unavailable
    )

    with pytest.raises(RuntimeError, match="Synthetic survey dependency unavailable"):
        resolve_web_access(request)
