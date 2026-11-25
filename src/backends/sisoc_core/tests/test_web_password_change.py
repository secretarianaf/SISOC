"""Public session API parity for Django's voluntary password change."""

import hashlib
import json
from types import SimpleNamespace
from urllib.parse import urlencode

import pytest
from django.contrib.auth import SESSION_KEY, HASH_SESSION_KEY, get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

User = get_user_model()
PATH = "/api/web/password/change/"
PUBLIC_IP = "203.0.113.42"
OLD = "Synthetic-Old-Password-739!"
NEW = "Synthetic-New-Password-482!"
FIELDS = ("old_password", "new_password1", "new_password2")
pytestmark = pytest.mark.django_db


def digest(user):
    profile = user.profile
    data = {
        "user": list(User.objects.filter(pk=user.pk).values()),
        "profile": list(type(profile).objects.filter(pk=profile.pk).values()),
        "tokens": list(Token.objects.filter(user=user).values()),
    }
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, default=str).encode()
    ).hexdigest()


def profile_digest(user):
    profile = user.profile
    data = list(type(profile).objects.filter(pk=profile.pk).values())
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, default=str).encode()
    ).hexdigest()


def token_digest(user):
    data = list(Token.objects.filter(user=user).values())
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, default=str).encode()
    ).hexdigest()


def session_matches(client, user):
    return client.session[HASH_SESSION_KEY] == user.get_session_auth_hash()


@pytest.fixture
def ready_user():
    user = User.objects.create_user(username="voluntary-synthetic", password=OLD)
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.password_changed_at = timezone.now()
    profile.initial_password_expires_at = timezone.now()
    profile.password_reset_requested_at = timezone.now()
    profile.temporary_password_plaintext = "synthetic-private-placeholder"
    profile.save()
    Token.objects.create(user=user)
    return user


def authenticated(user):
    client = APIClient(enforce_csrf_checks=True, REMOTE_ADDR=PUBLIC_IP)
    client.force_login(user)
    client.get(PATH)
    return client


def submit(client, data=None, path=PATH, csrf=True):
    payload = data or dict(old_password=OLD, new_password1=NEW, new_password2=NEW)
    headers = {"HTTP_X_CSRFTOKEN": client.cookies["csrftoken"].value} if csrf else {}
    return client.post(
        path,
        urlencode(payload),
        content_type="application/x-www-form-urlencoded",
        **headers,
    )


@pytest.mark.parametrize("method", ["get", "head", "post"])
def test_anonymous_api_is_not_a_login_redirect(method):
    client = APIClient(enforce_csrf_checks=True, REMOTE_ADDR=PUBLIC_IP)
    client.get("/login/")
    response = submit(client) if method == "post" else getattr(client, method)(PATH)
    assert response.status_code == 401
    assert "Location" not in response
    assert "private" in response["Cache-Control"]


def test_metadata_is_real_password_change_form_without_private_context(ready_user):
    client = authenticated(ready_user)
    before = digest(ready_user)
    response = client.get(PATH)
    assert response.status_code == 200
    data = response.json()
    assert [field["name"] for field in data["fields"]] == list(FIELDS)
    assert data["fields"][0]["attrs"]["autocomplete"] == "current-password"
    assert all(
        field["attrs"]["id"] == "id_" + field["name"] for field in data["fields"]
    )
    assert all(field["required"] for field in data["fields"])
    assert data["title"] == "Cambio de contraseña"
    assert data["done_text"] == "Su contraseña ha sido cambiada."
    assert (
        not {"user", "navigation", "capabilities", "profile", "initial", "token"}
        & data.keys()
    )
    assert "no-store" in response["Cache-Control"]
    assert "Cookie" in response["Vary"]
    assert digest(ready_user) == before


@pytest.mark.parametrize(
    "flag,state,destination",
    [
        ("acceso_web", "web_access_denied", None),
        ("must_change_password", "password_change_required", "/password/first-change/"),
        (
            "needs_profile_confirmation",
            "profile_confirmation_required",
            "/mi-cuenta/confirmar/",
        ),
    ],
)
def test_existing_prerequisites_deny_without_changing_data(
    ready_user, flag, state, destination
):
    client = authenticated(ready_user)
    profile = ready_user.profile
    setattr(profile, flag, flag != "acceso_web")
    profile.save(update_fields=[flag])
    before = digest(ready_user)
    for response in [client.get(PATH), submit(client)]:
        assert response.status_code == 403
        assert response.json()["state"] == state
        assert response.json()["required_action_url"] == destination
    assert digest(ready_user) == before


def test_mandatory_survey_is_not_bypassed(ready_user, monkeypatch):
    client = authenticated(ready_user)
    monkeypatch.setattr(
        "usuarios.web_session.get_rondas_pendientes_para_request",
        lambda _request: [
            SimpleNamespace(encuesta=SimpleNamespace(es_obligatoria=True))
        ],
    )
    before = digest(ready_user)
    response = submit(client)
    assert response.status_code == 403
    assert response.json()["state"] == "mandatory_survey_required"
    assert response.json()["required_action_url"] == "/inicio/"
    assert digest(ready_user) == before


@pytest.mark.parametrize(
    "changes,error_field",
    [
        ({"old_password": "wrong"}, "old_password"),
        ({"new_password2": "mismatch"}, "new_password2"),
        ({"new_password1": "123", "new_password2": "123"}, "new_password2"),
        ({"old_password": ""}, "old_password"),
    ],
)
def test_real_form_rejections_preserve_every_stored_value(
    ready_user, changes, error_field
):
    client = authenticated(ready_user)
    before = digest(ready_user)
    payload = dict(old_password=OLD, new_password1=NEW, new_password2=NEW)
    payload.update(changes)
    response = submit(client, payload)
    assert response.status_code == 400
    assert error_field in response.json()["errors"]
    assert response.json()["errors"][error_field][0]["message"]
    assert "initial" not in response.json()
    assert digest(ready_user) == before


def test_success_uses_framework_session_effects_without_required_password_effects(
    ready_user,
):
    client = authenticated(ready_user)
    profile = ready_user.profile
    profile_before = profile_digest(ready_user)
    token_before = token_digest(ready_user)
    old_session_key = client.session.session_key
    response = submit(client)
    assert response.status_code == 200
    assert response.json() == {"ok": True, "redirect": reverse("password_change_done")}
    ready_user.refresh_from_db()
    new_matches = ready_user.check_password(NEW)
    assert new_matches
    old_matches = ready_user.check_password(OLD)
    assert not old_matches
    assert profile_digest(ready_user) == profile_before
    assert token_digest(ready_user) == token_before
    assert client.session[SESSION_KEY] == str(ready_user.pk)
    assert session_matches(client, ready_user)
    session_rotated = client.session.session_key != old_session_key
    assert session_rotated
    assert client.get(PATH).status_code == 200


def test_csrf_rejection_and_transport_methods_do_not_mutate(ready_user):
    client = authenticated(ready_user)
    before = digest(ready_user)
    assert submit(client, csrf=False).status_code == 403
    token = client.cookies["csrftoken"].value
    assert (
        client.post(PATH, {}, format="json", HTTP_X_CSRFTOKEN=token).status_code == 415
    )
    for method in ["put", "patch", "delete"]:
        assert getattr(client, method)(PATH, HTTP_X_CSRFTOKEN=token).status_code == 405
    assert digest(ready_user) == before


def test_post_cannot_select_another_user_or_change_flags(ready_user):
    other = User.objects.create_user(username="voluntary-other", password=OLD)
    client = authenticated(ready_user)
    before_other = digest(other)
    profile = ready_user.profile
    before_profile = profile_digest(ready_user)
    response = submit(
        client,
        dict(
            old_password=OLD,
            new_password1=NEW,
            new_password2=NEW,
            user_id=str(other.pk),
            must_change_password="true",
            acceso_web="false",
        ),
    )
    assert response.status_code == 200
    assert digest(other) == before_other
    assert profile_digest(ready_user) == before_profile


@pytest.mark.parametrize("address", ["127.0.0.1", PUBLIC_IP])
@pytest.mark.parametrize(
    "actor,expected", [("anonymous", 401), ("ready", 200), ("restricted", 403)]
)
def test_password_head_enforces_access_for_all_addresses(
    ready_user, address, actor, expected, settings
):
    settings.INTERNAL_IPS = ["127.0.0.1"]
    client = APIClient(enforce_csrf_checks=True, REMOTE_ADDR=address)
    if actor == "restricted":
        profile = ready_user.profile
        profile.acceso_web = False
        profile.save(update_fields=["acceso_web"])
    if actor != "anonymous":
        client.force_login(ready_user)
    before = digest(ready_user)
    response = client.head(PATH)
    assert response.status_code == expected
    assert response.content == b""
    assert response["Content-Type"].startswith("application/json")
    assert "X-View" not in response
    assert "private" in response["Cache-Control"]
    assert "no-store" in response["Cache-Control"]
    assert "Cookie" in response["Vary"]
    if actor == "anonymous":
        assert response["WWW-Authenticate"] == "Session"
        assert "sessionid" not in client.cookies
    if actor == "ready":
        assert "csrftoken" in client.cookies
        assert session_matches(client, ready_user)
    assert digest(ready_user) == before


def test_legacy_invalid_form_matches_api_and_done_remains_publicly_guarded(ready_user):
    client = authenticated(ready_user)
    payload = dict(old_password="wrong", new_password1=NEW, new_password2=NEW)
    before = digest(ready_user)
    legacy = submit(client, payload, path="/password_change/")
    api = submit(client, payload)
    assert legacy.status_code == 200
    assert api.status_code == 400
    assert legacy.context["form"].errors.get_json_data() == api.json()["errors"]
    assert client.get("/password_change/done/").status_code == 200
    assert digest(ready_user) == before


def test_legacy_success_still_preserves_profile_and_tokens(ready_user):
    client = authenticated(ready_user)
    profile = ready_user.profile
    before_profile = profile_digest(ready_user)
    before_tokens = token_digest(ready_user)
    response = submit(client, path="/password_change/")
    assert response.status_code == 302
    assert response["Location"] == reverse("password_change_done")
    ready_user.refresh_from_db()
    new_matches = ready_user.check_password(NEW)
    assert new_matches
    assert session_matches(client, ready_user)
    assert profile_digest(ready_user) == before_profile
    assert token_digest(ready_user) == before_tokens
