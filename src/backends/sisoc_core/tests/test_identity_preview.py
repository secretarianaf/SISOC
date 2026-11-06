"""Isolated identity preview entry and immutable public asset boundary."""

import hashlib
from types import ModuleType

import pytest
from django.contrib.auth.models import Group, Permission, User
from django.contrib.sessions.models import Session
from django.test import override_settings

PUBLIC_IP = "203.0.113.42"


def _assert_private_html(response, asset_path):
    assert response["Content-Type"] == "text/html; charset=utf-8"
    assert "private" in response["Cache-Control"]
    assert "no-store" in response["Cache-Control"]
    assert "Cookie" in response["Vary"]
    if asset_path is not None:
        assert asset_path.encode() in response.content
        assert b"/v2/sisoc/assets/" not in response.content
        assert response["Content-Length"] == str(len(response.content))


def _web_user(username, **flags):
    user = User.objects.create_user(username=username)
    profile = user.profile
    profile.acceso_web = flags.get("acceso_web", True)
    profile.must_change_password = flags.get("must_change_password", False)
    profile.needs_profile_confirmation = flags.get("needs_confirmation", False)
    profile.save()
    return user


def _domain_fingerprint():
    return (
        tuple(User.objects.order_by("pk").values_list("pk", "password", "email")),
        tuple(Group.objects.order_by("pk").values_list("pk", "name")),
    )


@pytest.fixture
def identity_preview(tmp_path):
    from config.urls_all import urlpatterns
    from usuarios.identity_preview import identity_preview_patterns

    assets = tmp_path / "assets"
    assets.mkdir()
    script = b"export const identity = true;"
    name = f"identity-{hashlib.sha256(script).hexdigest()[:12]}.js"
    (assets / name).write_bytes(script)
    (assets / "not-public.env").write_text("synthetic-not-an-asset")
    (tmp_path / "index.html").write_text(
        f'<html><script type="module" src="/v2/sisoc/assets/{name}"></script></html>'
    )
    module = ModuleType("identity_preview_test_urls")
    module.urlpatterns = identity_preview_patterns(tmp_path) + urlpatterns
    with override_settings(ROOT_URLCONF=module):
        yield f"/static/sisoc-identity/assets/{name}", script


@pytest.mark.django_db
def test_identity_anonymous_entry_keeps_csrf_and_fixed_assets(client, identity_preview):
    asset_path, _ = identity_preview
    for path in ("/", "/login/"):
        response = client.get(path, {"private": "do-not-forward"})
        assert response.status_code == 200
        _assert_private_html(response, asset_path)
        assert b"do-not-forward" not in response.content
        assert "csrftoken" in response.cookies
        assert "sessionid" not in response.cookies
        head = client.head(path, REMOTE_ADDR=PUBLIC_IP)
        assert head.status_code == 200
        assert head.content == b""
        assert "X-View" not in head
        assert "no-store" in head["Cache-Control"]
    assert not Session.objects.exists()
    response = client.get("/password/first-change/")
    assert response.status_code == 302
    assert response["Location"] == "/inicio/"


@pytest.mark.django_db
def test_identity_assets_are_exact_immutable_and_credential_free(
    client, identity_preview
):
    path, script = identity_preview
    for method in ("get", "head"):
        response = getattr(client, method)(path, REMOTE_ADDR=PUBLIC_IP)
        assert response.status_code == 200
        assert response.content == (script if method == "get" else b"")
        assert response["Content-Length"] == str(len(script))
        assert not response.cookies
        assert "immutable" in response["Cache-Control"]
        assert response["X-Content-Type-Options"] == "nosniff"
        assert hashlib.sha256(script).hexdigest() in response["ETag"]
    for invalid in (
        path + "?private=ignored",
        "/static/sisoc-identity/missing.js",
        "/static/sisoc-identity/assets/not-public.env",
    ):
        assert client.get(invalid).status_code == 404
    assert client.post(path).status_code == 405
    assert not Session.objects.exists()


@pytest.mark.django_db
def test_identity_password_frame_does_not_unlock_business(client, identity_preview):
    asset_path, _ = identity_preview
    user = User.objects.create_user(
        username="identity-preview", password="fixture-only"
    )
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = True
    profile.needs_profile_confirmation = True
    profile.initial_password_expires_at = None
    profile.save()
    response = client.post(
        "/login/", {"username": user.username, "password": "fixture-only"}
    )
    assert response.status_code == 302
    before = _domain_fingerprint()
    entry = client.get("/password/first-change/")
    assert entry.status_code == 200
    _assert_private_html(entry, asset_path)
    assert "csrftoken" in entry.cookies
    head = client.head("/password/first-change/", REMOTE_ADDR=PUBLIC_IP)
    assert head.status_code == 200
    assert head.content == b""
    session = client.get("/api/web/session/")
    assert session.json()["access"]["state"] == "password_change_required"
    assert session.json()["navigation"] == []
    business = client.get("/insumos/")
    assert business.status_code == 302
    assert business["Location"] == "/password/first-change/"
    assert _domain_fingerprint() == before
    user.profile.refresh_from_db()
    assert user.profile.must_change_password
    profile.acceso_web = False
    profile.save()
    assert client.get("/password/first-change/").status_code == 403
    denied_head = client.head("/password/first-change/", REMOTE_ADDR=PUBLIC_IP)
    assert denied_head.status_code == 403
    assert denied_head.content == b""


def test_identity_preview_refuses_missing_fixed_index(tmp_path):
    from usuarios.identity_preview import identity_preview_patterns

    with pytest.raises(ValueError, match="index"):
        identity_preview_patterns(tmp_path)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "path",
    [
        "/mi-cuenta/",
        "/mi-cuenta/confirmar/",
        "/password_change/",
        "/password_change/done/",
        "/inicio/",
    ],
)
def test_account_password_entries_preserve_source_guards(
    client, identity_preview, path
):
    asset_path, _ = identity_preview
    anonymous = client.get(path)
    assert anonymous.status_code == 302
    assert "next=" in anonymous["Location"]
    anonymous_head = client.head(path, REMOTE_ADDR=PUBLIC_IP)
    assert anonymous_head.status_code == 302
    assert anonymous_head.content == b""
    user = _web_user(
        "identity-next-preview",
        needs_confirmation=path == "/mi-cuenta/confirmar/",
    )
    client.force_login(user)
    before = _domain_fingerprint()
    response = client.get(path)
    assert response.status_code == 200
    _assert_private_html(response, asset_path)
    assert "csrftoken" in response.cookies or path == "/password_change/done/"
    head = client.head(path, REMOTE_ADDR=PUBLIC_IP)
    assert head.status_code == 200
    assert head.content == b""
    assert "X-View" not in head
    assert _domain_fingerprint() == before
    if user.profile.needs_profile_confirmation:
        assert client.get("/api/web/session/").json()["navigation"] == []
        assert client.get("/insumos/")["Location"] == "/mi-cuenta/confirmar/"
    profile = user.profile
    profile.must_change_password = True
    profile.save()
    blocked = client.get(path)
    assert blocked.status_code == 302
    assert blocked["Location"] == "/password/first-change/"
    profile.acceso_web = False
    profile.save()
    assert client.get(path).status_code == 403
    assert client.head(path, REMOTE_ADDR=PUBLIC_IP).status_code == 403


@pytest.mark.django_db
def test_confirmation_entry_keeps_source_early_redirect(client, identity_preview):
    client.force_login(_web_user("confirmed-preview"))
    response = client.get("/mi-cuenta/confirmar/")
    assert response.status_code == 302
    assert response["Location"] == "/inicio/"


@pytest.mark.django_db
def test_voluntary_password_post_keeps_django_form_and_session(
    client, identity_preview
):
    user = User.objects.create_user(username="voluntary-preview", password="old-only")
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    client.force_login(user)
    password_before = User.objects.get(pk=user.pk).password
    invalid = client.post(
        "/password_change/",
        {
            "old_password": "wrong-old",
            "new_password1": "Synthetic-Preview-9431",
            "new_password2": "Synthetic-Preview-9431",
        },
    )
    assert invalid.status_code == 200
    assert "old_password" in invalid.context["form"].errors
    assert User.objects.get(pk=user.pk).password == password_before
    valid = client.post(
        "/password_change/",
        {
            "old_password": "old-only",
            "new_password1": "Synthetic-Preview-9431",
            "new_password2": "Synthetic-Preview-9431",
        },
    )
    assert valid.status_code == 302
    assert valid["Location"] == "/password_change/done/"
    user.refresh_from_db()
    assert user.check_password("Synthetic-Preview-9431")
    assert client.get("/password_change/done/").status_code == 200


@pytest.mark.django_db
def test_group_preview_retains_public_guards_objects_and_native_post(
    client, identity_preview
):
    asset_path, _ = identity_preview
    assert client.get("/grupos/").status_code == 403
    assert client.head("/grupos/", REMOTE_ADDR=PUBLIC_IP).status_code == 403
    user = _web_user("groups-preview")
    user.user_permissions.set(
        Permission.objects.filter(
            content_type__app_label="auth",
            codename__in=["view_group", "add_group", "change_group"],
        )
    )
    client.force_login(user)
    group = Group.objects.create(name="Preview group")
    before = _domain_fingerprint()
    for path in ["/grupos/", "/grupos/crear/", f"/grupos/editar/{group.pk}/"]:
        response = client.get(path, {"busqueda": "do-not-forward"})
        assert response.status_code == 200
        _assert_private_html(response, asset_path)
        assert b"do-not-forward" not in response.content
        assert "csrftoken" in response.cookies
        head = client.head(path, REMOTE_ADDR=PUBLIC_IP)
        assert head.status_code == 200
        assert head.content == b""
    assert _domain_fingerprint() == before
    assert client.get("/grupos/editar/999999/").status_code == 404
    response = client.post("/grupos/crear/", {"name": "Native preview POST"})
    assert response.status_code == 302 and response["Location"] == "/grupos/"
    assert Group.objects.filter(name="Native preview POST").exists()
    user.user_permissions.clear()
    assert client.get(f"/grupos/editar/{group.pk}/").status_code == 403
    denied_head = client.head(f"/grupos/editar/{group.pk}/", REMOTE_ADDR=PUBLIC_IP)
    assert denied_head.status_code == 403


@pytest.mark.django_db
def test_home_preview_keeps_source_non_get_render(client, identity_preview):
    asset_path, _ = identity_preview
    client.force_login(_web_user("home-preview"))
    response = client.post("/inicio/")
    assert response.status_code == 200
    assert b"inicio-presentacion--default" in response.content
    assert asset_path.encode() not in response.content


@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/mi-cuenta/", "/grupos/", "/password_change/"])
def test_internal_head_matches_source_baseline(client, settings, tmp_path, path):
    """Preview entries never widen the inherited admindocs HEAD diagnostic."""
    from config.urls_all import urlpatterns
    from usuarios.identity_preview import identity_preview_patterns

    settings.INTERNAL_IPS = ["127.0.0.1"]
    source = client.head(path, REMOTE_ADDR="127.0.0.1")
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<html></html>")
    module = ModuleType("identity_preview_internal_head_urls")
    module.urlpatterns = identity_preview_patterns(tmp_path) + urlpatterns
    with override_settings(ROOT_URLCONF=module):
        preview = client.head(path, REMOTE_ADDR="127.0.0.1")
    assert preview.status_code == source.status_code
    assert preview.content == source.content == b""
    assert ("X-View" in preview) == ("X-View" in source)
    assert not Session.objects.exists()


@pytest.mark.django_db
def test_recovery_entries_keep_source_exchange_without_exposing_token(
    client, identity_preview
):
    from django.contrib.auth.tokens import default_token_generator
    from django.contrib.auth.views import INTERNAL_RESET_SESSION_TOKEN
    from django.utils.encoding import force_bytes
    from django.utils.http import urlsafe_base64_encode

    asset_path, _ = identity_preview
    user = _web_user("recovery-preview")
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    before = _domain_fingerprint()
    for path in ("/password_reset/", "/password_reset/done/", "/reset/done/"):
        response = client.get(path, {"private": "do-not-forward"})
        assert response.status_code == 200
        _assert_private_html(response, asset_path)
        assert b"do-not-forward" not in response.content
        head = client.head(path, REMOTE_ADDR=PUBLIC_IP)
        assert head.status_code == 200
        assert head.content == b""
    assert "csrftoken" in client.get("/password_reset/").cookies
    for prefix in ("/reset/", "/password/reset/confirm/"):
        invalid = client.get(f"{prefix}{uid}/not-a-token/")
        assert invalid.status_code == 200
        _assert_private_html(invalid, asset_path)
        assert b"not-a-token" not in invalid.content
        exchange = client.get(f"{prefix}{uid}/{token}/")
        assert exchange.status_code == 302
        assert exchange["Location"] == f"{prefix}{uid}/set-password/"
        assert client.session[INTERNAL_RESET_SESSION_TOKEN] == token
        entry = client.get(exchange["Location"])
        assert entry.status_code == 200
        _assert_private_html(entry, asset_path)
        assert token.encode() not in entry.content
        assert "csrftoken" in entry.cookies
        head = client.head(exchange["Location"], REMOTE_ADDR=PUBLIC_IP)
        assert head.status_code == 200
        assert head.content == b""
    assert _domain_fingerprint() == before


@pytest.mark.django_db
def test_recovery_entries_keep_source_html_posts(client, identity_preview):
    from django.core import mail

    asset_path, _ = identity_preview
    user = _web_user("recovery-post-preview")
    user.email = "recovery-post@example.invalid"
    user.set_password("Synthetic-Old-7781!")
    user.save()
    invalid = client.post("/password_reset/", {"username": "", "email": "x"})
    assert invalid.status_code == 200
    assert asset_path.encode() not in invalid.content
    assert "username" in invalid.context["form"].errors
    sent = client.post(
        "/password_reset/", {"username": user.username, "email": user.email}
    )
    assert sent.status_code == 302 and sent["Location"] == "/password_reset/done/"
    assert len(mail.outbox) == 1
    link = next(line for line in mail.outbox[0].body.splitlines() if "/reset/" in line)
    exchange = client.get(link.strip().split("testserver", 1)[1])
    assert exchange.status_code == 302
    mismatch = client.post(
        exchange["Location"],
        {"new_password1": "Synthetic-New-4410!", "new_password2": "other"},
    )
    assert mismatch.status_code == 200
    assert asset_path.encode() not in mismatch.content
    user.refresh_from_db()
    assert user.check_password("Synthetic-Old-7781!")
    done = client.post(
        exchange["Location"],
        {
            "new_password1": "Synthetic-New-4410!",
            "new_password2": "Synthetic-New-4410!",
        },
    )
    assert done.status_code == 302 and done["Location"] == "/reset/done/"
    user.refresh_from_db()
    assert user.check_password("Synthetic-New-4410!")
    stale = client.get(exchange["Location"])
    assert stale.status_code == 200
    _assert_private_html(stale, asset_path)
