"""Local preview entries of the user list and its state steps keep native guards."""

import hashlib
from types import ModuleType

import pytest
from django.contrib.auth.models import Group, Permission, User
from django.test import override_settings

PUBLIC_IP = "203.0.113.42"


def _actor(username, codenames, delegated):
    user = User.objects.create_user(username=username)
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    profile.grupos_asignables.add(delegated)
    user.user_permissions.set(
        Permission.objects.filter(
            content_type__app_label="auth", codename__in=codenames
        )
    )
    return user


@pytest.fixture
def preview(tmp_path):
    from config.urls_all import urlpatterns
    from usuarios.identity_preview import identity_preview_patterns

    assets = tmp_path / "assets"
    assets.mkdir()
    name = f"users-{hashlib.sha256(b'x').hexdigest()[:12]}.js"
    (assets / name).write_bytes(b"x")
    (tmp_path / "index.html").write_text(
        f'<html><script type="module" src="/v2/sisoc/assets/{name}"></script></html>'
    )
    module = ModuleType("users_preview_test_urls")
    module.urlpatterns = identity_preview_patterns(tmp_path) + urlpatterns
    with override_settings(ROOT_URLCONF=module):
        yield name


@pytest.mark.django_db
def test_user_entries_keep_guards_scope_and_native_post(client, preview):
    group = Group.objects.create(name="Preview delegado")
    target = User.objects.create_user(username="preview_target")
    target.groups.add(group)
    outsider = User.objects.create_user(username="preview_outsider")
    outsider.groups.add(Group.objects.create(name="Preview ajeno"))
    paths = [
        "/usuarios/",
        f"/usuarios/borrar/{target.pk}/",
        f"/usuarios/activar/{target.pk}/",
    ]
    for path in paths:
        assert client.get(path).status_code == 403
    actor = _actor("users-preview", ["view_user", "delete_user"], group)
    client.force_login(actor)
    for path in paths:
        response = client.get(path, {"busqueda": "do-not-forward"})
        assert response.status_code == 200
        assert preview.encode() in response.content
        assert b"do-not-forward" not in response.content
        assert "no-store" in response["Cache-Control"]
        head = client.head(path, REMOTE_ADDR=PUBLIC_IP)
        assert head.status_code == 200 and head.content == b""
    assert client.get(f"/usuarios/borrar/{outsider.pk}/").status_code == 404
    assert client.get(f"/usuarios/activar/{outsider.pk}/").status_code == 404
    response = client.post(f"/usuarios/borrar/{target.pk}/")
    assert response.status_code == 302 and response["Location"] == "/usuarios/"
    target.refresh_from_db()
    assert target.is_active is False
    actor.user_permissions.clear()
    for path in paths:
        assert client.get(path).status_code == 403
