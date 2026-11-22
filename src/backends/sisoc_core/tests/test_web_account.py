"""Real session/public-route contracts for own-account editing and confirmation."""

import hashlib
import secrets
from unittest.mock import patch

import pytest
from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.test import Client
from users.models import Profile

pytestmark = pytest.mark.django_db
PATHS = ["/api/web/account/", "/api/web/account/confirm/"]
FIELDS = ["first_name", "last_name", "email", "dni", "cuil", "correo_institucional"]


def payload(**overrides):
    data = dict(
        first_name="Ana",
        last_name="Pérez",
        email="ana@example.invalid",
        dni="12.345.678",
        cuil="20-12345678-6",
        correo_institucional="",
    )
    return {**data, **overrides}


def digest():
    return hashlib.sha256(
        repr(
            [list(m.objects.order_by("pk").values()) for m in (User, Profile, Session)]
        ).encode()
    ).hexdigest()


@pytest.fixture
def actor():
    secret = secrets.token_urlsafe(24)
    user = User.objects.create_user(
        username="account_synthetic",
        password=secret,
        first_name="Original",
        last_name="Persona",
        email="original@example.invalid",
    )
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.dni = "12345678"
    profile.cuil = "20123456786"
    profile.save()
    c = Client(enforce_csrf_checks=True, REMOTE_ADDR="203.0.113.42")
    assert c.get("/api/web/login/").status_code == 200
    from urllib.parse import urlencode

    response = c.post(
        "/api/web/login/",
        urlencode({"username": user.username, "password": secret}),
        content_type="application/x-www-form-urlencoded",
        HTTP_X_CSRFTOKEN=c.cookies["csrftoken"].value,
    )
    assert response.status_code == 200
    return user, c


def post(c, path, data, **kwargs):
    from urllib.parse import urlencode

    return c.post(
        path,
        urlencode(data),
        content_type="application/x-www-form-urlencoded",
        HTTP_X_CSRFTOKEN=c.cookies["csrftoken"].value,
        **kwargs,
    )


def pending(user):
    profile = user.profile
    profile.needs_profile_confirmation = True
    profile.save(update_fields=["needs_profile_confirmation"])


@pytest.mark.parametrize("path", PATHS)
def test_anonymous_401(path):
    c = Client(REMOTE_ADDR="203.0.113.42")
    before = digest()
    assert c.get(path).status_code == 401
    assert digest() == before


@pytest.mark.parametrize("path", PATHS)
def test_metadata_has_only_authorized_fields(actor, path):
    user, c = actor
    if path.endswith("confirm/"):
        pending(user)
    before = digest()
    response = c.get(path)
    assert response.status_code == 200
    data = response.json()
    assert set(data) == {"fields", "initial", "errors", "presentation", "messages"}
    assert [f["name"] for f in data["fields"]] == FIELDS
    assert set(data["initial"]) == set(FIELDS)
    assert [f["name"] for f in data["fields"] if not f["required"]] == [
        "correo_institucional"
    ]
    assert data["initial"]["dni"] == "12345678"
    assert set(data["presentation"]) == {
        "user",
        "footer_version_label",
        "legacy_frame_navigation",
    }
    assert set(data["presentation"]["user"]) == {
        "username",
        "display_name",
        "avatar_initial",
        "role_label",
    }
    assert data["errors"] == {}
    assert "no-store" in response["Cache-Control"] and "Cookie" in response["Vary"]
    head = c.head(path)
    assert head.status_code == 200 and head.content == b""
    assert digest() == before
    if path.endswith("confirm/"):
        assert c.get("/api/web/session/").json()["navigation"] == []
        assert c.get("/insumos/").status_code == 302


@pytest.mark.parametrize("path", PATHS)
@pytest.mark.parametrize(
    "change,field",
    [
        ({"first_name": ""}, "first_name"),
        ({"dni": "123"}, "dni"),
        ({"cuil": "20-12345678-9"}, "cuil"),
        ({"email": "bad"}, "email"),
    ],
)
def test_form_errors_preserve_data(actor, path, change, field):
    user, c = actor
    if path.endswith("confirm/"):
        pending(user)
    before = digest()
    response = post(c, path, payload(**change))
    assert response.status_code == 400
    assert field in response.json()["errors"]
    assert set(response.json()["initial"]) == set(FIELDS)
    assert digest() == before


@pytest.mark.parametrize(
    "path,redirect", [(PATHS[0], "/mi-cuenta/"), (PATHS[1], "/inicio/")]
)
def test_atomic_current_user_save_and_ignored_private_fields(actor, path, redirect):
    user, c = actor
    other = User.objects.create_user(username="unrelated", email="ana@example.invalid")
    if path.endswith("confirm/"):
        pending(user)
    response = post(
        c,
        path,
        payload(
            pk=other.pk,
            is_staff="true",
            is_superuser="true",
            rol="injected",
            acceso_web="false",
            groups="1",
        ),
    )
    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "message": "Datos personales actualizados correctamente.",
        "redirect": redirect,
    }
    user.refresh_from_db()
    other.refresh_from_db()
    profile = Profile.objects.get(user=user)
    assert (user.first_name, user.last_name, user.email) == (
        "Ana",
        "Pérez",
        "ana@example.invalid",
    )
    assert profile.dni == "12345678" and profile.cuil == "20123456786"
    assert (
        not profile.needs_profile_confirmation
        and profile.datos_confirmados_at is not None
    )
    assert profile.correo_institucional == "" and profile.acceso_web
    assert not user.is_staff and not user.is_superuser and user.groups.count() == 0
    assert other.first_name == "" and c.get("/api/web/session/").status_code == 200
    assert c.get(redirect).status_code == 200


@pytest.mark.parametrize("path", PATHS)
def test_csrf_methods_media_reject_without_mutation(actor, path):
    user, c = actor
    if path.endswith("confirm/"):
        pending(user)
    before = digest()
    assert c.post(path, payload()).status_code == 403
    assert (
        c.put(
            path,
            "",
            content_type="application/json",
            HTTP_X_CSRFTOKEN=c.cookies["csrftoken"].value,
        ).status_code
        == 405
    )
    assert (
        c.post(
            path,
            "{}",
            content_type="application/json",
            HTTP_X_CSRFTOKEN=c.cookies["csrftoken"].value,
        ).status_code
        == 415
    )
    assert digest() == before


@pytest.mark.parametrize("path", PATHS)
@pytest.mark.parametrize(
    "flag,state",
    [
        ("acceso_web", "web_access_denied"),
        ("must_change_password", "password_change_required"),
    ],
)
def test_higher_priority_guards(actor, path, flag, state):
    user, c = actor
    pending(user)
    profile = Profile.objects.get(user=user)
    setattr(profile, flag, flag != "acceso_web")
    profile.save()
    before = digest()
    for response in [c.get(path), post(c, path, payload())]:
        assert response.status_code == 403 and response.json()["state"] == state
    assert digest() == before


def test_account_does_not_bypass_profile_confirmation(actor):
    user, c = actor
    pending(user)
    before = digest()
    assert c.get(PATHS[0]).status_code == 403
    assert post(c, PATHS[0], payload()).status_code == 403
    assert digest() == before


def test_already_confirmed_is_source_noop_even_on_post(actor):
    _, c = actor
    before = digest()
    for response in [c.get(PATHS[1]), post(c, PATHS[1], payload())]:
        assert response.status_code == 200 and response.json() == {
            "ok": True,
            "redirect": "/inicio/",
        }
    assert digest() == before
    assert c.get("/mi-cuenta/confirmar/").status_code == 302


def test_existing_form_rolls_back_user_when_profile_save_fails(actor):
    user, c = actor
    before = digest()
    with patch.object(
        Profile, "save", side_effect=RuntimeError("synthetic save failure")
    ):
        with pytest.raises(RuntimeError, match="synthetic save failure"):
            post(c, PATHS[0], payload())
    user.refresh_from_db()
    assert digest() == before


@pytest.mark.parametrize("path", ["/mi-cuenta/", "/mi-cuenta/confirmar/"])
def test_native_form_and_return_remain(actor, path):
    user, c = actor
    if path.endswith("confirmar/"):
        pending(user)
    assert c.get(path).status_code == 200
    response = c.post(path, payload(), HTTP_X_CSRFTOKEN=c.cookies["csrftoken"].value)
    assert response.status_code == 302
    assert response["Location"] == (
        "/inicio/" if path.endswith("confirmar/") else "/mi-cuenta/"
    )
    assert Profile.objects.get(user=user).dni == "12345678"


def test_account_get_consumes_success_queue_once(actor):
    _, c = actor
    response = post(c, PATHS[0], payload())
    assert response.status_code == 200
    first = c.get(PATHS[0])
    assert first.json()["messages"] == [
        {"message": "Datos personales actualizados correctamente.", "level": "success"}
    ]
    assert c.get(PATHS[0]).json()["messages"] == []


def test_account_get_preserves_other_source_notice_levels(actor):
    from django.contrib import messages
    from usuarios.auth_views import MiCuentaView

    _, c = actor
    original = MiCuentaView.form_valid

    def with_existing_notice(view, form):
        response = original(view, form)
        messages.warning(view.request, "Aviso sintético anterior.")
        return response

    with patch.object(MiCuentaView, "form_valid", with_existing_notice):
        assert post(c, PATHS[0], payload()).status_code == 200
    notices = c.get(PATHS[0]).json()["messages"]
    assert notices == [
        {"message": "Datos personales actualizados correctamente.", "level": "success"},
        {"message": "Aviso sintético anterior.", "level": "warning"},
    ]
    assert c.get(PATHS[0]).json()["messages"] == []


def test_profile_confirmation_precedes_survey_but_does_not_authorize_business(actor):
    from datetime import timedelta
    from django.utils import timezone
    from encuestas.models import Encuesta, SegmentacionEncuesta, RondaEncuesta

    user, c = actor
    pending(user)
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
    assert c.get(PATHS[1]).status_code == 200
    assert (
        c.get("/api/web/session/").json()["access"]["state"]
        == "profile_confirmation_required"
    )
    assert post(c, PATHS[1], payload()).json()["redirect"] == "/inicio/"
    assert (
        c.get("/api/web/session/").json()["access"]["state"]
        == "mandatory_survey_required"
    )
    assert c.get(PATHS[0]).status_code == 403
    before = digest()
    assert c.get(PATHS[1]).json() == {"ok": True, "redirect": "/inicio/"}
    assert digest() == before


@pytest.mark.parametrize(
    "request_case",
    [
        (path, address, kind)
        for path in PATHS
        for address in ("127.0.0.1", "203.0.113.42")
        for kind in (
            "anonymous",
            "ready",
            "restricted",
            "profile_pending",
            "password_pending",
        )
    ],
)
def test_account_head_enforces_access_for_all_addresses(actor, request_case, settings):
    user, _ = actor
    path, address, kind = request_case
    settings.INTERNAL_IPS = ["127.0.0.1"]
    profile = user.profile
    if kind == "restricted":
        profile.acceso_web = False
    elif kind == "profile_pending":
        profile.needs_profile_confirmation = True
    elif kind == "password_pending":
        profile.must_change_password = True
    profile.save()
    client = Client(enforce_csrf_checks=True, REMOTE_ADDR=address)
    if kind != "anonymous":
        client.force_login(user)
    expected = 401 if kind == "anonymous" else 200
    if kind in {"restricted", "password_pending"} or (
        kind == "profile_pending" and path == PATHS[0]
    ):
        expected = 403
    before = digest()
    response = client.head(path)
    assert response.status_code == expected
    assert response.content == b""
    assert response["Content-Type"].startswith("application/json")
    assert "X-View" not in response
    assert "private" in response["Cache-Control"]
    assert "no-store" in response["Cache-Control"]
    assert "Cookie" in response["Vary"]
    assert "csrftoken" in client.cookies
    if kind == "anonymous":
        assert "sessionid" not in client.cookies
    assert digest() == before
