"""Public session API parity for the source password-recovery circuit."""

import hashlib
import json
from urllib.parse import urlencode, urlsplit

import pytest
from django.contrib.auth import SESSION_KEY, get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.views import INTERNAL_RESET_SESSION_TOKEN
from django.contrib.sessions.models import Session
from django.core import mail
from django.test import Client
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.authtoken.models import Token

User = get_user_model()
REQUEST = "/api/web/password/reset/"
PUBLIC_IP = "203.0.113.42"
OLD = "Synthetic-Old-Password-739!"
NEW = "Synthetic-Reset-Password-482!"
pytestmark = pytest.mark.django_db


def client(address=PUBLIC_IP):
    return Client(enforce_csrf_checks=True, REMOTE_ADDR=address)


def confirm_path(user):
    return f"/api/web/password/reset/{uid(user)}/"


def uid(user):
    return urlsafe_base64_encode(force_bytes(user.pk))


def digest():
    profile_model = User.profile.related.related_model
    data = {
        "users": list(User.objects.order_by("pk").values()),
        "profiles": list(profile_model.objects.order_by("pk").values()),
        "tokens": list(Token.objects.order_by("pk").values()),
    }
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, default=str).encode()
    ).hexdigest()


def post(c, path, data, csrf=True, **extra):
    headers = {"HTTP_X_CSRFTOKEN": c.cookies["csrftoken"].value} if csrf else {}
    return c.post(
        path,
        urlencode(data),
        content_type="application/x-www-form-urlencoded",
        **headers,
        **extra,
    )


@pytest.fixture
def account():
    user = User.objects.create_user(
        username="reset-synthetic", email="Reset.Synthetic@example.invalid"
    )
    user.set_password(OLD)
    user.save()
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = True
    profile.password_changed_at = None
    profile.initial_password_expires_at = timezone.now()
    profile.password_reset_requested_at = timezone.now()
    profile.temporary_password_plaintext = "synthetic-private-placeholder"
    profile.save()
    Token.objects.create(user=user)
    return user


def exchanged(user, prefix="/reset/"):
    """Use the unchanged source GET to trade the URL token for the session."""
    c = client()
    token = default_token_generator.make_token(user)
    response = c.get(f"{prefix}{uid(user)}/{token}/")
    assert response.status_code == 302
    assert response["Location"] == f"{prefix}{uid(user)}/set-password/"
    assert token not in response["Location"]
    c.get(confirm_path(user))
    return c


@pytest.mark.parametrize("method", ["get", "head"])
def test_request_metadata_is_real_form_without_private_values(account, method):
    c = client()
    before = digest()
    response = getattr(c, method)(REQUEST)
    assert response.status_code == 200
    assert response["Content-Type"].startswith("application/json")
    assert "private" in response["Cache-Control"]
    assert "no-store" in response["Cache-Control"]
    assert "Cookie" in response["Vary"]
    assert "csrftoken" in c.cookies
    assert "sessionid" not in c.cookies
    if method == "head":
        assert response.content == b""
    else:
        data = response.json()
        assert set(data) == {"fields", "footer_version_label"}
        assert isinstance(data["footer_version_label"], str)
        assert data["fields"] == [
            {
                "name": "username",
                "label": "Usuario",
                "type": "text",
                "required": True,
                "attrs": {"id": "id_username", "maxlength": "150"},
            },
            {
                "name": "email",
                "label": "Email",
                "type": "email",
                "required": True,
                "attrs": {
                    "id": "id_email",
                    "autocomplete": "email",
                    "maxlength": "254",
                },
            },
        ]
    assert not mail.outbox
    assert not Session.objects.exists()
    assert digest() == before


@pytest.mark.parametrize(
    "case,matches",
    [
        ("match", True),
        ("casefold-email", True),
        ("unknown-user", False),
        ("other-email", False),
        ("inactive", False),
    ],
)
def test_request_has_one_done_whether_or_not_the_account_matches(
    account, case, matches
):
    data = {"username": account.username, "email": account.email}
    if case == "casefold-email":
        data["email"] = account.email.upper()
    elif case == "unknown-user":
        data["username"] = "reset-nobody"
    elif case == "other-email":
        data["email"] = "someone-else@example.invalid"
    elif case == "inactive":
        account.is_active = False
        account.save(update_fields=["is_active"])
    c = client()
    c.get(REQUEST)
    before = digest()
    response = post(c, REQUEST, data)
    assert response.status_code == 200
    assert response.json() == {"ok": True, "redirect": "/password_reset/done/"}
    assert "private" in response["Cache-Control"]
    assert "no-store" in response["Cache-Control"]
    assert "sessionid" not in response.cookies
    assert digest() == before
    assert len(mail.outbox) == (1 if matches else 0)
    legacy = client()
    legacy.get("/password_reset/")
    source = post(legacy, "/password_reset/", data)
    assert source.status_code == 302
    assert source["Location"] == response.json()["redirect"]
    assert len(mail.outbox) == (2 if matches else 0)
    if matches:
        message = mail.outbox[0]
        assert message.to == [account.email]
        assert message.subject == "SISOC - Restablecer contraseña"
        link = next(
            line for line in message.body.splitlines() if "/reset/" in line
        ).strip()
        parts = urlsplit(link).path.strip("/").split("/")
        assert parts[:2] == ["reset", uid(account)]
        assert default_token_generator.check_token(account, parts[2])
        assert mail.outbox[1].body.count("/reset/") == 1


def test_request_response_shape_is_identical_for_match_and_no_match(account):
    shapes = []
    for username in (account.username, "reset-nobody"):
        c = client()
        c.get(REQUEST)
        response = post(c, REQUEST, {"username": username, "email": account.email})
        shapes.append(
            (
                response.status_code,
                response.content,
                sorted(response.headers),
                sorted(response.cookies),
            )
        )
    assert shapes[0] == shapes[1]


@pytest.mark.parametrize(
    "data",
    [
        {"username": "", "email": "x"},
        {"username": "a" * 151, "email": ""},
        {"username": "reset-synthetic"},
    ],
)
def test_request_form_errors_match_source_and_send_nothing(account, data):
    c = client()
    c.get(REQUEST)
    before = digest()
    response = post(c, REQUEST, data)
    assert response.status_code == 400
    legacy = client()
    legacy.get("/password_reset/")
    source = post(legacy, "/password_reset/", data)
    assert source.status_code == 200
    assert response.json() == {"errors": source.context["form"].errors.get_json_data()}
    assert not mail.outbox
    assert digest() == before


def test_request_requires_csrf_urlencoded_and_known_methods(account):
    c = client()
    c.get(REQUEST)
    data = {"username": account.username, "email": account.email}
    before = digest()
    assert post(c, REQUEST, data, csrf=False).status_code == 403
    token = c.cookies["csrftoken"].value
    assert (
        c.post(
            REQUEST, json.dumps(data), "application/json", HTTP_X_CSRFTOKEN=token
        ).status_code
        == 415
    )
    for method in ("put", "patch", "delete"):
        assert getattr(c, method)(REQUEST, HTTP_X_CSRFTOKEN=token).status_code == 405
    assert not mail.outbox
    assert digest() == before


@pytest.mark.parametrize("prefix", ["/reset/", "/password/reset/confirm/"])
def test_confirm_reads_only_the_session_exchange_of_the_source_view(account, prefix):
    before = digest()
    c = exchanged(account, prefix)
    response = c.get(confirm_path(account))
    assert response.status_code == 200
    assert "private" in response["Cache-Control"]
    assert "no-store" in response["Cache-Control"]
    data = response.json()
    assert set(data) == {"validlink", "fields"}
    assert data["validlink"] is True
    assert [field["name"] for field in data["fields"]] == [
        "new_password1",
        "new_password2",
    ]
    assert [field["label"] for field in data["fields"]] == [
        "Contraseña nueva",
        "Confirmación de contraseña nueva",
    ]
    assert data["fields"][0]["attrs"] == {
        "id": "id_new_password1",
        "autocomplete": "new-password",
        "aria-describedby": "id_new_password1_helptext",
    }
    assert "<ul><li>" in data["fields"][0]["help_text"]
    session_token = c.session[INTERNAL_RESET_SESSION_TOKEN]
    assert session_token not in response.content.decode()
    assert SESSION_KEY not in c.session
    fresh = client()
    assert fresh.get(confirm_path(account)).json() == {"validlink": False}
    assert digest() == before


def test_confirm_api_never_accepts_a_url_token(account):
    c = client()
    token = default_token_generator.make_token(account)
    before = digest()
    response = c.get(f"{confirm_path(account)}{token}/")
    assert response.status_code == 404
    assert INTERNAL_RESET_SESSION_TOKEN not in c.session
    c.get(REQUEST)
    response = post(
        c,
        confirm_path(account),
        {"token": token, "new_password1": NEW, "new_password2": NEW},
    )
    assert response.status_code == 200
    assert response.json() == {"validlink": False}
    assert digest() == before


def test_confirm_success_keeps_source_effects_without_login(account):
    c = exchanged(account)
    response = post(
        c, confirm_path(account), {"new_password1": NEW, "new_password2": NEW}
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True, "redirect": "/reset/done/"}
    account.refresh_from_db()
    assert account.check_password(NEW)
    assert not account.check_password(OLD)
    assert not Token.objects.filter(user=account).exists()
    profile = account.profile
    profile.refresh_from_db()
    assert profile.must_change_password is False
    assert profile.password_changed_at is not None
    assert profile.initial_password_expires_at is None
    assert profile.password_reset_requested_at is None
    assert profile.temporary_password_plaintext is None
    assert SESSION_KEY not in c.session
    assert INTERNAL_RESET_SESSION_TOKEN not in c.session
    before = digest()
    assert c.get(confirm_path(account)).json() == {"validlink": False}
    again = post(c, confirm_path(account), {"new_password1": OLD, "new_password2": OLD})
    assert again.json() == {"validlink": False}
    assert digest() == before


@pytest.mark.parametrize(
    "data",
    [
        {"new_password1": NEW, "new_password2": "mismatch"},
        {"new_password1": "12345678", "new_password2": "12345678"},
        {"new_password1": "", "new_password2": ""},
    ],
)
def test_confirm_form_errors_match_source_and_write_nothing(account, data):
    c = exchanged(account)
    before = digest()
    response = post(c, confirm_path(account), data)
    assert response.status_code == 400
    legacy = exchanged(account)
    source = post(legacy, f"/reset/{uid(account)}/set-password/", data)
    assert source.status_code == 200
    assert response.json() == {
        "validlink": True,
        "errors": source.context["form"].errors.get_json_data(),
    }
    assert digest() == before
    assert INTERNAL_RESET_SESSION_TOKEN in c.session
    assert c.get(confirm_path(account)).json()["validlink"] is True


def test_confirm_revalidates_on_submit_after_concurrent_password_change(account):
    c = exchanged(account)
    assert c.get(confirm_path(account)).json()["validlink"] is True
    account.set_password("Synthetic-Concurrent-Password-1!")
    account.save()
    before = digest()
    response = post(
        c, confirm_path(account), {"new_password1": NEW, "new_password2": NEW}
    )
    assert response.status_code == 200
    assert response.json() == {"validlink": False}
    assert digest() == before
    account.refresh_from_db()
    assert account.check_password("Synthetic-Concurrent-Password-1!")


def test_confirm_expired_or_foreign_links_are_invalid_without_writes(account, settings):
    other = User.objects.create_user(username="reset-other", email="o@example.invalid")
    c = exchanged(account)
    before = digest()
    foreign = post(
        c,
        f"/api/web/password/reset/{uid(other)}/",
        {"new_password1": NEW, "new_password2": NEW},
    )
    assert foreign.json() == {"validlink": False}
    garbage = c.get("/api/web/password/reset/not-a-uid/")
    assert garbage.status_code == 200
    assert garbage.json() == {"validlink": False}
    settings.PASSWORD_RESET_TIMEOUT = -1
    assert c.get(confirm_path(account)).json() == {"validlink": False}
    expired = post(
        c, confirm_path(account), {"new_password1": NEW, "new_password2": NEW}
    )
    assert expired.status_code == 200
    assert expired.json() == {"validlink": False}
    assert digest() == before


def test_confirm_requires_csrf_urlencoded_and_known_methods(account):
    c = exchanged(account)
    path = confirm_path(account)
    data = {"new_password1": NEW, "new_password2": NEW}
    before = digest()
    assert post(c, path, data, csrf=False).status_code == 403
    token = c.cookies["csrftoken"].value
    assert (
        c.post(
            path, json.dumps(data), "application/json", HTTP_X_CSRFTOKEN=token
        ).status_code
        == 415
    )
    for method in ("put", "patch", "delete"):
        assert getattr(c, method)(path, HTTP_X_CSRFTOKEN=token).status_code == 405
    assert digest() == before
    assert INTERNAL_RESET_SESSION_TOKEN in c.session


@pytest.mark.parametrize("address", ["127.0.0.1", PUBLIC_IP])
def test_reset_head_is_the_api_response_for_all_addresses(account, address, settings):
    settings.INTERNAL_IPS = ["127.0.0.1"]
    for path in (REQUEST, confirm_path(account)):
        c = client(address)
        before = digest()
        response = c.head(path)
        assert response.status_code == 200
        assert response.content == b""
        assert response["Content-Type"].startswith("application/json")
        assert "X-View" not in response
        assert "private" in response["Cache-Control"]
        assert "no-store" in response["Cache-Control"]
        assert "Cookie" in response["Vary"]
        assert "csrftoken" in c.cookies
        assert digest() == before
