"""Synthetic public-interface preflight; no credential/session values are emitted."""

import hashlib, secrets
from datetime import timedelta
import pytest
from django.contrib.auth import SESSION_KEY
from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from users.models import Profile
from rest_framework.authtoken.models import Token
from encuestas.models import Encuesta, SegmentacionEncuesta, RondaEncuesta

pytestmark = pytest.mark.django_db


def need(value, label):
    if not bool(value):
        raise AssertionError(label)


def account(role="ready"):
    secret = " " + secrets.token_urlsafe(24) + " "
    user = User.objects.create_user(
        username="ida_" + role, password=secret, is_active=role != "inactive"
    )
    profile = user.profile
    profile.acceso_web = role != "web_disabled"
    profile.must_change_password = role in {
        "password_pending",
        "expired",
        "all_pending",
    }
    profile.needs_profile_confirmation = role in {"profile_pending", "all_pending"}
    if role == "expired":
        profile.initial_password_expires_at = timezone.now() - timedelta(seconds=1)
    profile.save()
    if role in {"survey_pending", "all_pending"}:
        survey = Encuesta.objects.create(
            titulo="Synthetic mandatory",
            duracion_ronda_dias=7,
            usuario_creador=user,
            es_obligatoria=True,
            estado="publicada",
        )
        segment, _ = SegmentacionEncuesta.objects.get_or_create(
            encuesta=survey, defaults={"tipo": "todos_los_usuarios"}
        )
        segment.tipo = "todos_los_usuarios"
        segment.save()
        RondaEncuesta.objects.get_or_create(
            encuesta=survey,
            numero_ronda=1,
            defaults={
                "fecha_apertura": timezone.now() - timedelta(hours=1),
                "fecha_cierre_programada": timezone.now() + timedelta(days=7),
                "estado": "abierta",
            },
        )
    return user, secret


def client():
    return Client(enforce_csrf_checks=True, REMOTE_ADDR="203.0.113.42")


def csrf(c, path="/login/"):
    r = c.get(path)
    need(r.status_code == 200, "BOOTSTRAP_STATUS")
    need("csrftoken" in c.cookies, "CSRF_COOKIE_SET")
    return c.cookies["csrftoken"].value


def state():
    rows = [
        list(m.objects.order_by("pk").values()) for m in [User, Profile, Token, Session]
    ]
    return hashlib.sha256(repr(rows).encode()).digest()


def login(c, user, secret, path="/login/", next_url=None):
    token = csrf(c, path)
    body = {"username": user.username, "password": secret}
    if next_url is not None:
        body["next"] = next_url
    return c.post(path, body, HTTP_X_CSRFTOKEN=token)


@pytest.mark.parametrize("path", ["/", "/login/"])
def test_legacy_anonymous_bootstrap_and_missing_csrf(path):
    c = client()
    r = c.get(path)
    need(r.status_code == 200, "PUBLIC_LOGIN_GET")
    need("csrftoken" in c.cookies, "PUBLIC_CSRF_BOOTSTRAP")
    need(
        r.context["form"].__class__.__name__ == "BackofficeAuthenticationForm",
        "REAL_AUTH_FORM",
    )
    before = state()
    r = c.post(path, {"username": "", "password": ""})
    need(r.status_code == 403, "ANONYMOUS_POST_REQUIRES_CSRF")
    need(state() == before, "REJECTED_LOGIN_NO_STATE_CHANGE")
    need(SESSION_KEY not in c.session, "REJECTED_LOGIN_NO_AUTH")


@pytest.mark.parametrize(
    "role,code",
    [
        ("inactive", "invalid_login"),
        ("web_disabled", "web_access_disabled"),
        ("expired", "initial_password_expired"),
    ],
)
def test_real_form_denials_preserve_auth_state(role, code):
    u, p = account(role)
    c = client()
    token = csrf(c)
    before = state()
    r = c.post(
        "/login/", {"username": u.username, "password": p}, HTTP_X_CSRFTOKEN=token
    )
    need(r.status_code == 200, "LEGACY_INVALID_STATUS")
    form = r.context["form"]
    need(
        any(e.code == code for e in form.non_field_errors().as_data()),
        "SOURCE_DENIAL_CODE",
    )
    need(form.data.get("password") == "", "FAILED_PASSWORD_CLEARED")
    need(SESSION_KEY not in r.wsgi_request.session, "NO_DENIED_AUTH")
    need(state() == before, "DENIAL_NO_AUTH_STATE_CHANGE")


@pytest.mark.parametrize("kind", ["empty", "spaces", "incorrect", "password_trimmed"])
def test_errors_normalization_and_password_not_trimmed(kind):
    u, p = account()
    c = client()
    token = csrf(c)
    before = state()
    data = {
        "username": "  " + u.username + "  ",
        "password": (
            p.strip() if kind == "password_trimmed" else secrets.token_urlsafe(24)
        ),
    }
    if kind == "empty":
        data = {"username": "", "password": ""}
    if kind == "spaces":
        data = {"username": "  ", "password": "  "}
    r = c.post("/login/", data, HTTP_X_CSRFTOKEN=token)
    need(r.status_code == 200, "INVALID_LOGIN_STATUS")
    f = r.context["form"]
    need(f.data.get("password") == "", "INVALID_PASSWORD_NOT_ECHOED")
    need(state() == before, "INVALID_LOGIN_AUTH_STATE_UNCHANGED")
    if kind in {"empty", "spaces"}:
        need(set(f.errors) == {"username", "password"}, "REQUIRED_FIELD_KEYS")
        need(
            all(
                str(e) == "Este campo es obligatorio."
                for k in f.errors
                for e in f.errors[k]
            ),
            "EXACT_REQUIRED_MESSAGES",
        )
    else:
        need(f.data.get("username") == u.username, "USERNAME_NORMALIZED")
        need(
            str(f.non_field_errors()[0]) == "Usuario o contraseña inválidos.",
            "EXACT_GENERAL_ERROR",
        )


@pytest.mark.parametrize("path", ["/", "/login/"])
@pytest.mark.parametrize(
    "destination",
    [
        "/insumos/?busqueda=sintetico",
        "https://external.invalid/",
        "//external.invalid/",
    ],
)
def test_actual_login_rotates_session_csrf_and_uses_framework_safe_next(
    path, destination
):
    u, p = account()
    c = client()
    session = c.session
    session["synthetic_marker"] = True
    session.save()
    token = csrf(c, path)
    old_key = c.session.session_key
    old_csrf = c.cookies["csrftoken"].value
    r = c.post(
        path,
        {"username": " " + u.username + " ", "password": p, "next": destination},
        HTTP_X_CSRFTOKEN=token,
    )
    need(r.status_code == 302, "SUCCESS_REDIRECT")
    need(
        r["Location"]
        == (destination if destination.startswith("/insumos/") else reverse("inicio")),
        "SOURCE_SAFE_DESTINATION",
    )
    need(SESSION_KEY in c.session, "REAL_SESSION_CREATED")
    need(c.session.session_key != old_key, "SESSION_ROTATED")
    need(c.cookies["csrftoken"].value != old_csrf, "CSRF_ROTATED")
    need(
        not Session.objects.filter(session_key=old_key).exists(), "OLD_SESSION_REMOVED"
    )


@pytest.mark.parametrize(
    "role,destination",
    [
        ("password_pending", "/password/first-change/"),
        ("profile_pending", "/mi-cuenta/confirmar/"),
        ("survey_pending", "/inicio/"),
        ("all_pending", "/password/first-change/"),
    ],
)
def test_login_followup_preserves_prerequisite_destination(role, destination):
    u, p = account(role)
    c = client()
    r = login(c, u, p, next_url="/insumos/")
    need(r.status_code == 302 and r["Location"] == "/insumos/", "SAFE_NEXT_PRESERVED")
    after = c.get(r["Location"])
    need(
        after.status_code == 302 and after["Location"] == destination,
        "REAL_PREREQUISITE_REDIRECT",
    )
    ctx = c.get("/api/web/session/").json()
    need(ctx["navigation"] == [], "PENDING_NAVIGATION_STAYS_EMPTY")


@pytest.mark.parametrize("path", ["/logout", "/logout/"])
@pytest.mark.parametrize(
    "role",
    [
        "ready",
        "password_pending",
        "profile_pending",
        "survey_pending",
        "all_pending",
        "web_disabled",
    ],
)
def test_logout_aliases_csrf_get_and_pending_sessions(path, role):
    u, p = account(role)
    c = client()
    # Establish all sessions via real login; web access changes only after successful login.
    if role == "web_disabled":
        u.profile.acceso_web = True
        u.profile.save()
    r = login(c, u, p)
    need(r.status_code == 302, "LOGOUT_FIXTURE_REAL_LOGIN")
    if role == "web_disabled":
        profile = Profile.objects.get(user=u)
        profile.acceso_web = False
        profile.save()
    before = state()
    r = c.get(path)
    need(r.status_code == 405, "LOGOUT_GET_405")
    need(state() == before, "GET_LOGOUT_NO_STATE_CHANGE")
    need(SESSION_KEY in c.session, "GET_LOGOUT_PRESERVES_SESSION")
    r = c.post(path)
    need(r.status_code == 403, "LOGOUT_REQUIRES_CSRF")
    need(state() == before, "CSRF_LOGOUT_NO_STATE_CHANGE")
    key = c.session.session_key
    r = c.post(path, HTTP_X_CSRFTOKEN=c.cookies["csrftoken"].value)
    need(r.status_code == 302, "LOGOUT_POST_REDIRECT")
    need(r["Location"] == reverse("login"), "LOGOUT_SOURCE_TARGET")
    need(SESSION_KEY not in c.session, "LOGOUT_FLUSHED_AUTH")
    need(
        not Session.objects.filter(session_key=key).exists(), "OLD_LOGOUT_SESSION_GONE"
    )


def test_authenticated_redirect_and_restricted_cookie_are_source_preserved():
    u, p = account()
    c = client()
    login(c, u, p)
    r = c.get("/login/")
    need(
        r.status_code == 302 and r["Location"] == reverse("inicio"),
        "AUTHENTICATED_LOGIN_REDIRECT",
    )
    profile = Profile.objects.get(user=u)
    profile.acceso_web = False
    profile.save()
    before = state()
    for path in ["/", "/login/"]:
        r = c.get(path)
        need(r.status_code == 403, "RESTRICTED_COOKIE_STILL_DENIED")
    need(state() == before, "RESTRICTED_COOKIE_NO_REPAIR")


def api_post(c, data, token=None):
    from urllib.parse import urlencode

    kwargs = {} if token is None else {"HTTP_X_CSRFTOKEN": token}
    return c.post(
        "/api/web/login/",
        urlencode(data),
        content_type="application/x-www-form-urlencoded",
        **kwargs,
    )


@pytest.mark.parametrize("method", ["get", "head"])
def test_public_api_bootstrap_has_actual_form_metadata_no_private_values(method):
    c = client()
    response = getattr(c, method)("/api/web/login/")
    need(response.status_code == 200, "API_BOOTSTRAP_STATUS")
    need("csrftoken" in c.cookies, "API_CSRF_COOKIE")
    need(
        "private" in response["Cache-Control"]
        and "no-store" in response["Cache-Control"],
        "API_PRIVATE_NOSTORE",
    )
    need("Cookie" in response["Vary"], "API_VARY_COOKIE")
    if method == "head":
        need(response.content == b"", "API_HEAD_EMPTY")
    else:
        data = response.json()
        need(
            set(data) == {"fields", "initial", "errors", "footer_version_label"},
            "API_BOOTSTRAP_KEYS",
        )
        need(set(data["initial"]) == {"username"}, "API_NO_PASSWORD_INITIAL")
        need(
            {f["name"] for f in data["fields"]} == {"username", "password"},
            "API_SOURCE_FIELDS",
        )
        need(isinstance(data["footer_version_label"], str), "API_PUBLIC_FOOTER")


def test_api_real_login_rejects_csrf_and_rotates_both_session_and_csrf():
    u, p = account()
    c = client()
    response = c.get("/api/web/login/")
    need(response.status_code == 200, "API_BOOTSTRAP")
    before = state()
    response = api_post(c, {"username": u.username, "password": p})
    need(response.status_code == 403, "API_ANONYMOUS_CSRF_REQUIRED")
    need(state() == before, "API_CSRF_NO_STATE_CHANGE")
    token = c.cookies["csrftoken"].value
    old_csrf = token
    before_key = c.session.session_key
    response = api_post(
        c,
        {
            "username": " " + u.username + " ",
            "password": p,
            "next": "https://external.invalid/",
        },
        token,
    )
    need(
        response.status_code == 200
        and response.json() == {"ok": True, "redirect": reverse("inicio")},
        "API_REAL_LOGIN_SAFE_REDIRECT",
    )
    need(SESSION_KEY in c.session, "API_AUTH_SESSION")
    need(c.session.session_key != before_key, "API_ROTATED_SESSION")
    need(c.cookies["csrftoken"].value != old_csrf, "API_ROTATED_CSRF")


@pytest.mark.parametrize(
    "role,code",
    [
        ("ready", "invalid_login"),
        ("inactive", "invalid_login"),
        ("web_disabled", "web_access_disabled"),
        ("expired", "initial_password_expired"),
    ],
)
def test_api_form_error_codes_clear_password_and_leave_state_unchanged(role, code):
    u, p = account(role)
    c = client()
    response = c.get("/api/web/login/")
    need(response.status_code == 200, "API_BOOTSTRAP")
    before = state()
    response = api_post(
        c,
        {
            "username": " " + u.username + " ",
            "password": secrets.token_urlsafe(24) if role == "ready" else p,
        },
        c.cookies["csrftoken"].value,
    )
    need(response.status_code == 400, "API_INVALID_STATUS")
    data = response.json()
    need(
        set(data) == {"errors", "initial"}
        and data["initial"] == {"username": u.username},
        "API_ERROR_NO_PASSWORD_ECHO",
    )
    need(
        any(e["code"] == code for e in data["errors"]["__all__"]),
        "API_SOURCE_ERROR_CODE",
    )
    need(state() == before, "API_FORM_REJECTION_NO_STATE_CHANGE")


@pytest.mark.parametrize("authenticated", [False, True])
def test_api_urlencoded_only_and_unsupported_methods_do_not_authenticate(authenticated):
    u, p = account()
    c = client()
    if authenticated:
        need(login(c, u, p).status_code == 302, "REAL_AUTHENTICATED_FIXTURE")
    need(c.get("/api/web/login/").status_code == 200, "API_BOOTSTRAP")
    token = c.cookies["csrftoken"].value
    before = state()
    for method in ["put", "patch", "delete"]:
        response = getattr(c, method)("/api/web/login/", HTTP_X_CSRFTOKEN=token)
        need(response.status_code == 405, "API_METHOD_405")
        need(state() == before, "API_METHOD_NO_STATE_CHANGE")
    response = c.post(
        "/api/web/login/",
        {"username": u.username, "password": p},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=token,
    )
    need(response.status_code == 415, "API_JSON_NOT_SUPPORTED")
    need(state() == before, "API_MEDIA_NO_STATE_CHANGE")


@pytest.mark.parametrize(
    "role", ["ready", "password_pending", "profile_pending", "all_pending"]
)
def test_api_authenticated_bootstrap_retains_framework_redirect_and_no_business_menu(
    role,
):
    u, p = account(role)
    c = client()
    need(login(c, u, p).status_code == 302, "REAL_LOGIN_FIXTURE")
    response = c.get("/api/web/login/")
    need(
        response.status_code == 200
        and response.json() == {"ok": True, "redirect": reverse("inicio")},
        "API_AUTHENTICATED_REDIRECT",
    )
    profile = Profile.objects.get(user=u)
    profile.acceso_web = False
    profile.save()
    before = state()
    response = c.get("/api/web/login/")
    need(response.status_code == 403, "API_RESTRICTED_COOKIE_403")
    need(state() == before, "API_RESTRICTED_COOKIE_NO_REPAIR")


@pytest.mark.parametrize("address", ["127.0.0.1", "203.0.113.42"])
def test_login_head_bootstrap_preserves_csrf_for_all_addresses(address, settings):
    settings.INTERNAL_IPS = ["127.0.0.1"]
    c = Client(enforce_csrf_checks=True, REMOTE_ADDR=address)
    before = state()
    response = c.head("/api/web/login/")
    assert response.status_code == 200
    assert response["Content-Type"].startswith("application/json")
    assert response.content == b""
    assert "csrftoken" in c.cookies
    assert "private" in response["Cache-Control"]
    assert "no-store" in response["Cache-Control"]
    assert "Cookie" in response["Vary"]
    assert "X-View" not in response
    assert "sessionid" not in c.cookies
    assert state() == before
