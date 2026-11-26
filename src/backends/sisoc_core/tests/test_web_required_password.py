"""Public HTTP contract for the session-only mandatory-password circuit."""

import hashlib
import json
from datetime import timedelta
from urllib.parse import urlencode

import pytest
from django.contrib.auth.models import Permission, User
from django.contrib.messages import get_messages
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from users.models import Profile

PATH = "/api/web/password/first-change/"
PUBLIC_IP = "203.0.113.42"
VALID_PASSWORD = "Synthetic-New-Password-48!"
NOTICE = "Contraseña actualizada correctamente."


@pytest.fixture
def required_user(db):
    user = User.objects.create_user(
        username="required_password_subject",
        password="Synthetic-Old-Password-28!",
        first_name="Usuario",
        last_name="Sintético",
    )
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = True
    profile.needs_profile_confirmation = True
    profile.initial_password_expires_at = timezone.now() + timedelta(days=1)
    profile.password_reset_requested_at = timezone.now()
    profile.temporary_password_plaintext = "synthetic-fixture-only"
    profile.save()
    user.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="insumos", codename="view_insumo"
        )
    )
    Token.objects.create(user=user)
    return user


def authenticated(user, *, csrf=False):
    client = APIClient(enforce_csrf_checks=csrf, REMOTE_ADDR=PUBLIC_IP)
    client.force_login(user)
    return client


def fingerprint():
    payload = {
        "users": list(User.objects.order_by("pk").values()),
        "profiles": list(Profile.objects.order_by("pk").values()),
        "tokens": list(Token.objects.order_by("pk").values()),
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode()
    ).hexdigest()


def submit(client, values=None, **kwargs):
    return client.post(
        PATH,
        urlencode(
            values
            if values is not None
            else {"new_password1": VALID_PASSWORD, "new_password2": VALID_PASSWORD}
        ),
        content_type="application/x-www-form-urlencoded",
        **kwargs,
    )


@pytest.mark.django_db
@pytest.mark.parametrize("method", ["get", "head", "post"])
def test_anonymous_requires_cookie_session_without_redirect(method):
    response = getattr(APIClient(REMOTE_ADDR=PUBLIC_IP), method)(PATH)
    assert response.status_code == 401
    assert "Location" not in response
    assert "private" in response["Cache-Control"]
    assert "no-store" in response["Cache-Control"]
    assert "Cookie" in response["Vary"]


def test_metadata_preserves_pending_session_and_authorized_presentation(required_user):
    client = authenticated(required_user)
    before = fingerprint()
    response = client.get(PATH)
    assert response.status_code == 200
    data = response.json()
    assert data["access"] == {
        "state": "password_change_required",
        "required_action_url": "/password/first-change/",
    }
    assert [field["name"] for field in data["fields"]] == [
        "new_password1",
        "new_password2",
    ]
    assert all(
        set(field) == {"name", "label", "help_text", "required"}
        and field["required"] is True
        for field in data["fields"]
    )
    assert data["presentation"]["user"]["username"] == required_user.username
    assert any(
        node["id"] == "inicio"
        for node in data["presentation"]["legacy_frame_navigation"]
    )
    assert "csrftoken" in client.cookies
    assert client.get("/api/web/session/").json()["navigation"] == []
    assert client.get("/insumos/")["Location"] == "/password/first-change/"
    assert client.get("/api/web/insumos/").status_code == 403
    assert fingerprint() == before
    assert "temporary_password_plaintext" not in response.content.decode()
    assert "password_reset_requested_at" not in response.content.decode()


@pytest.mark.parametrize("method", ["get", "head", "post"])
def test_web_access_denial_precedes_remediation(required_user, method):
    profile = required_user.profile
    profile.acceso_web = False
    profile.save(update_fields=["acceso_web"])
    client = authenticated(required_user)
    before = fingerprint()
    response = getattr(client, method)(PATH)
    assert response.status_code == 403
    if method != "head":
        assert response.json()["state"] == "web_access_denied"
    assert fingerprint() == before


@pytest.mark.parametrize("method", ["get", "post"])
def test_already_completed_returns_fixed_redirect_without_mutation(
    required_user, method
):
    profile = required_user.profile
    profile.must_change_password = False
    profile.save(update_fields=["must_change_password"])
    client = authenticated(required_user)
    before = fingerprint()
    response = client.get(PATH) if method == "get" else submit(client)
    assert response.status_code == 200
    assert response.json() == {"ok": True, "redirect": reverse("inicio")}
    assert fingerprint() == before


def test_invalid_password_pair_returns_form_errors_and_preserves_state(required_user):
    client = authenticated(required_user)
    before = fingerprint()
    response = submit(
        client, {"new_password1": VALID_PASSWORD, "new_password2": "different"}
    )
    assert response.status_code == 400
    assert response.json()["errors"]["new_password2"][0]["code"] == "password_mismatch"
    assert fingerprint() == before
    assert "new_password1" not in response.json()["errors"]


def test_success_preserves_source_flags_session_message_and_tokens(required_user):
    client = authenticated(required_user)
    token_count = Token.objects.filter(user=required_user).count()
    response = submit(client)
    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "message": NOTICE,
        "redirect": reverse("inicio"),
    }
    required_user.refresh_from_db()
    profile = required_user.profile
    assert required_user.check_password(VALID_PASSWORD)
    assert not profile.must_change_password
    assert profile.needs_profile_confirmation
    assert profile.password_changed_at is not None
    assert profile.initial_password_expires_at is None
    assert profile.password_reset_requested_at is None
    assert profile.temporary_password_plaintext is None
    assert Token.objects.filter(user=required_user).count() == token_count
    assert [str(message) for message in get_messages(response.wsgi_request)] == [NOTICE]
    context = client.get("/api/web/session/")
    assert context.status_code == 200
    assert context.json()["access"]["state"] == "profile_confirmation_required"
    assert context.json()["navigation"] == []


def test_csrf_failure_preserves_state_and_valid_token_allows_source_action(
    required_user,
):
    client = authenticated(required_user, csrf=True)
    before = fingerprint()
    assert submit(client).status_code == 403
    assert fingerprint() == before
    assert client.get(PATH).status_code == 200
    response = submit(client, HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value)
    assert response.status_code == 200
    required_user.refresh_from_db()
    assert not required_user.profile.must_change_password


def test_json_and_unsupported_methods_cannot_change_password(required_user):
    client = authenticated(required_user)
    before = fingerprint()
    assert (
        client.post(PATH, {"new_password1": "not-used"}, format="json").status_code
        == 415
    )
    for method in ("put", "patch", "delete"):
        assert getattr(client, method)(PATH).status_code == 405
    assert fingerprint() == before


def test_payload_cannot_select_another_user_or_change_private_flags(required_user):
    other = User.objects.create_user(username="untouched_subject")
    other_before = other.password
    response = submit(
        authenticated(required_user),
        {
            "new_password1": VALID_PASSWORD,
            "new_password2": VALID_PASSWORD,
            "user_id": str(other.pk),
            "acceso_web": "false",
            "rol": "administrator",
        },
    )
    assert response.status_code == 200
    other.refresh_from_db()
    required_user.refresh_from_db()
    assert other.password == other_before
    assert required_user.profile.acceso_web
    assert required_user.profile.rol != "administrator"


@pytest.mark.parametrize("address", ["127.0.0.1", PUBLIC_IP])
@pytest.mark.parametrize(
    "actor,expected",
    [("anonymous", 401), ("required", 200), ("restricted", 403), ("completed", 200)],
)
def test_required_password_head_enforces_access_for_all_addresses(
    required_user, address, actor, expected, settings
):
    settings.INTERNAL_IPS = ["127.0.0.1"]
    client = APIClient(enforce_csrf_checks=True, REMOTE_ADDR=address)
    if actor in {"restricted", "completed"}:
        profile = required_user.profile
        if actor == "restricted":
            profile.acceso_web = False
        else:
            profile.must_change_password = False
        profile.save()
    if actor != "anonymous":
        client.force_login(required_user)
    before = fingerprint()
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
    else:
        assert "csrftoken" in client.cookies
    assert fingerprint() == before


def test_inactive_or_missing_profile_session_cannot_enter(required_user):
    client = authenticated(required_user)
    profile = required_user.profile
    profile.delete()
    before = fingerprint()
    assert client.get(PATH).status_code == 403
    assert fingerprint() == before
    required_user.is_active = False
    required_user.save(update_fields=["is_active"])
    assert client.get(PATH).status_code == 401


def test_legacy_html_keeps_fixed_nonrequired_redirect(required_user):
    profile = required_user.profile
    profile.must_change_password = False
    profile.save(update_fields=["must_change_password"])
    client = authenticated(required_user)
    before = fingerprint()
    response = client.get("/password/first-change/")
    assert response.status_code == 302
    assert response["Location"] == reverse("inicio")
    assert fingerprint() == before


@override_settings(ROOT_URLCONF="config.urls")
def test_actual_core_root_exposes_the_same_private_endpoint(required_user):
    assert authenticated(required_user).get(PATH).status_code == 200
