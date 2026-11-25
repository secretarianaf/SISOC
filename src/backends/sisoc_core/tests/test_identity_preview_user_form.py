"""Local preview entries of the user form keep native guards, scope and POST."""

import hashlib
from types import ModuleType

import pytest
from django.contrib.auth.models import Group, Permission, User
from django.test import override_settings


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
    name = f"form-{hashlib.sha256(b'x').hexdigest()[:12]}.js"
    (assets / name).write_bytes(b"x")
    (tmp_path / "index.html").write_text(
        f'<html><script type="module" src="/v2/sisoc/assets/{name}"></script></html>'
    )
    module = ModuleType("user_form_preview_test_urls")
    module.urlpatterns = identity_preview_patterns(tmp_path) + urlpatterns
    with override_settings(ROOT_URLCONF=module):
        yield name


@pytest.mark.django_db
def test_form_entries_keep_guards_scope_and_native_post(client, preview):
    group = Group.objects.create(name="CDI - Trabajador")
    target = User.objects.create_user(username="form_target")
    target.groups.add(group)
    outsider = User.objects.create_user(username="form_outsider")
    outsider.groups.add(Group.objects.create(name="CDF - Referente centro"))
    paths = ["/usuarios/crear/", f"/usuarios/editar/{target.pk}/"]
    for path in paths:
        assert client.get(path).status_code == 403
    actor = _actor("form-preview", ["add_user", "change_user"], group)
    client.force_login(actor)
    for path in paths:
        response = client.get(path)
        assert response.status_code == 200
        assert preview.encode() in response.content
        assert "no-store" in response["Cache-Control"]
    assert client.get(f"/usuarios/editar/{outsider.pk}/").status_code == 404
    before = User.objects.count()
    response = client.post("/usuarios/crear/", {"username": ""})
    assert response.status_code == 200
    assert User.objects.count() == before
    actor.user_permissions.clear()
    for path in paths:
        assert client.get(path).status_code == 403
