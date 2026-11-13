"""Regresión del guardado del grupo Coordinador DataCalle (#2908)."""

from importlib import import_module

import pytest
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType

from core.models import Provincia


@pytest.fixture(params=["users.admin_forms", "pwa.user_forms"])
def form_module(request):
    return import_module(request.param)


@pytest.mark.django_db
@pytest.mark.parametrize("creating", [False, True])
def test_coordinator_group_saves_role_and_province(form_module, creating):
    actor = User.objects.create_superuser("admin2908", "admin@example.com", "test")
    group, _ = Group.objects.get_or_create(name="Coordinador DataCalle")
    province = Provincia.objects.create(nombre="Córdoba")
    data = {
        "username": "coordinator2908",
        "tipo_usuario": "interno",
        "password": "Test2908Password!",
        "groups": [group.pk],
        "provincias_datacalle": [province.pk],
    }
    kwargs = {}
    form_class = form_module.UserCreationForm
    if not creating:
        kwargs["instance"] = User.objects.create_user("coordinator2908")
        form_class = form_module.CustomUserChangeForm
    form = form_class(data=data, actor=actor, **kwargs)
    assert form.is_valid(), form.errors
    user = form.save()
    user.refresh_from_db()
    assert set(user.groups.values_list("pk", flat=True)) == {group.pk}
    assert user.profile.datacalle_rol == "coordinador"
    assert user.profile.es_relevador_calle is True
    assert user.profile.es_usuario_provincial is True
    assert list(
        user.profile.territorial_scopes.values_list(
            "provincia_id", "municipio_id", "localidad_id"
        )
    ) == [(province.pk, None, None)]
    assert not user.profile.relevador_calle_provincias.exists()


@pytest.mark.django_db
@pytest.mark.parametrize("province_count", [0, 2])
def test_coordinator_group_requires_exactly_one_province(form_module, province_count):
    actor = User.objects.create_superuser("admin2908", "admin@example.com", "test")
    user = User.objects.create_user("target2908", first_name="Sin cambios")
    group, _ = Group.objects.get_or_create(name="Coordinador DataCalle")
    provinces = [
        Provincia.objects.create(nombre=str(i)).pk for i in range(province_count)
    ]
    form = form_module.CustomUserChangeForm(
        actor=actor,
        instance=user,
        data={
            "username": user.username,
            "tipo_usuario": "interno",
            "first_name": "No guardar",
            "groups": [group.pk],
            "provincias_datacalle": provinces,
        },
    )
    assert not form.is_valid()
    assert "provincias_datacalle" in form.errors
    assert "groups" in form.errors  # Visible aunque Mobile esté oculto.
    user.refresh_from_db()
    assert user.first_name == "Sin cambios"
    assert not user.groups.filter(pk=group.pk).exists()
    assert user.profile.datacalle_rol == ""


@pytest.mark.django_db
@pytest.mark.parametrize("with_section", [False, True])
def test_coordinator_group_cannot_bypass_role_authority(form_module, with_section):
    # A delegated group is not authority to assign a DataCalle coordinator role.
    group, _ = Group.objects.get_or_create(name="Coordinador DataCalle")
    actor = User.objects.create_user("delegated2908")
    actor.profile.grupos_asignables.add(group)
    if with_section:
        permission, _ = Permission.objects.get_or_create(
            content_type=ContentType.objects.get_for_model(User),
            codename="role_usuarios_seccion_datacalle",
            defaults={"name": "DataCalle section"},
        )
        actor.user_permissions.add(permission)
    province = Provincia.objects.create(nombre="Córdoba")
    user = User.objects.create_user("target2908")
    form = form_module.CustomUserChangeForm(
        actor=actor,
        instance=user,
        data={
            "username": user.username,
            "tipo_usuario": "interno",
            "groups": [group.pk],
            "provincias_datacalle": [province.pk],
        },
    )
    assert not form.is_valid()
    assert "groups" in form.errors or "datacalle_rol" in form.errors
    assert not user.groups.filter(pk=group.pk).exists()


@pytest.mark.django_db
def test_coordinator_group_does_not_replace_existing_scope(form_module):
    actor = User.objects.create_superuser("admin2908", "admin@example.com", "test")
    user = User.objects.create_user("target2908")
    group, _ = Group.objects.get_or_create(name="Coordinador DataCalle")
    province = Provincia.objects.create(nombre="Córdoba")
    original = Provincia.objects.create(nombre="Salta")
    user.profile.es_usuario_provincial = True
    user.profile.save()
    user.profile.territorial_scopes.create(provincia=original)
    form = form_module.CustomUserChangeForm(
        actor=actor,
        instance=user,
        data={
            "username": user.username,
            "tipo_usuario": "interno",
            "groups": [group.pk],
            "provincias_datacalle": [province.pk],
        },
    )
    assert not form.is_valid()
    user.refresh_from_db()
    assert list(
        user.profile.territorial_scopes.values_list("provincia_id", flat=True)
    ) == [original.pk]
    assert not user.groups.filter(pk=group.pk).exists()


@pytest.mark.django_db
@pytest.mark.parametrize("role", ["", "entrevistador"])
def test_explicit_revoke_or_demotion_wins_over_resubmitted_group(role):
    from pwa.user_forms import CustomUserChangeForm

    actor = User.objects.create_superuser("admin2908", "admin@example.com", "test")
    user = User.objects.create_user("target2908")
    group, _ = Group.objects.get_or_create(name="Coordinador DataCalle")
    other = Group.objects.create(name="Otro grupo 2908")
    user.groups.add(group, other)
    province = Provincia.objects.create(nombre="Córdoba")
    profile = user.profile
    profile.datacalle_rol = "coordinador"
    profile.es_relevador_calle = True
    profile.es_usuario_provincial = True
    profile.save()
    profile.territorial_scopes.create(provincia=province)
    form = CustomUserChangeForm(
        actor=actor,
        instance=user,
        data={
            "username": user.username,
            "tipo_usuario": "interno",
            "groups": [group.pk, other.pk],
            "es_relevador_calle": bool(role),
            "datacalle_rol": role,
            "provincias_datacalle": [province.pk],
        },
    )
    assert form.is_valid(), form.errors
    form.save()
    user.refresh_from_db()
    assert user.profile.datacalle_rol == role
    assert set(user.groups.values_list("pk", flat=True)) == {other.pk}
