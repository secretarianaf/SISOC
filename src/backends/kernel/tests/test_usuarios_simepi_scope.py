"""Alcance SIMEPI del ABM de usuarios, también sin el backend CDI instalado."""

import pytest
from django.contrib.auth.models import Group, Permission, User
from django.test import RequestFactory
from django.urls import reverse

from core.constants import UserGroups
from users.services import UsuariosService


@pytest.fixture
def admin_simepi(db):
    actor = User.objects.create_user(username="admin-simepi-core", password="test")
    actor.groups.add(
        Group.objects.get_or_create(name=UserGroups.SIMEPI_ADMINISTRADOR)[0]
    )
    actor.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="auth",
            codename__in=("view_user", "change_user", "delete_user"),
        )
    )
    Group.objects.get_or_create(name=UserGroups.CDI_TRABAJADOR)
    return User.objects.get(pk=actor.pk)


@pytest.fixture
def usuarios(db):
    cdi = User.objects.create_user(username="trabajador-cdi-core", password="test")
    cdi.groups.add(Group.objects.get_or_create(name=UserGroups.CDI_TRABAJADOR)[0])
    sin_grupos = User.objects.create_user(username="sin-grupos-core", password="test")
    return cdi, sin_grupos


@pytest.mark.django_db
def test_admin_no_lista_ni_administra_cuentas_sin_grupos(admin_simepi, usuarios):
    cdi, sin_grupos = usuarios
    request = RequestFactory().get("/usuarios/")
    request.user = admin_simepi

    for queryset in (
        UsuariosService.get_filtered_usuarios(request),
        UsuariosService.get_usuarios_en_alcance(request),
    ):
        visibles = set(queryset.values_list("pk", flat=True))
        assert cdi.pk in visibles
        assert admin_simepi.pk in visibles
        assert sin_grupos.pk not in visibles


@pytest.mark.django_db
@pytest.mark.parametrize("ruta", ["usuario_editar", "usuario_borrar"])
@pytest.mark.parametrize("metodo", ["get", "post"])
def test_admin_no_edita_ni_da_de_baja_cuenta_sin_grupos(
    client, admin_simepi, usuarios, ruta, metodo
):
    _, sin_grupos = usuarios
    password_original = sin_grupos.password
    client.force_login(admin_simepi)

    respuesta = getattr(client, metodo)(reverse(ruta, kwargs={"pk": sin_grupos.pk}))

    assert respuesta.status_code == 404
    sin_grupos.refresh_from_db()
    assert sin_grupos.is_active
    assert sin_grupos.password == password_original


@pytest.mark.django_db
@pytest.mark.parametrize("ruta", ["usuario_editar", "usuario_borrar"])
def test_admin_conserva_acceso_a_cuentas_cdi(client, admin_simepi, usuarios, ruta):
    cdi, _ = usuarios
    client.force_login(admin_simepi)

    respuesta = client.get(reverse(ruta, kwargs={"pk": cdi.pk}))

    assert respuesta.status_code == 200


@pytest.mark.django_db
def test_superusuario_conserva_acceso_a_cuentas_sin_grupos(usuarios):
    _, sin_grupos = usuarios
    actor = User.objects.create_superuser(
        username="super-core", email="super@example.com", password="test"
    )
    request = RequestFactory().get("/usuarios/")
    request.user = actor

    assert (
        UsuariosService.get_usuarios_en_alcance(request)
        .filter(pk=sin_grupos.pk)
        .exists()
    )


@pytest.mark.django_db
def test_otro_gestor_conserva_delegacion_de_cuentas_sin_grupos(usuarios):
    _, sin_grupos = usuarios
    actor = User.objects.create_user(username="gestor-core", password="test")
    actor.profile.grupos_asignables.add(
        Group.objects.get_or_create(name="Grupo de otro programa")[0]
    )
    request = RequestFactory().get("/usuarios/")
    request.user = actor

    assert (
        UsuariosService.get_usuarios_en_alcance(request)
        .filter(pk=sin_grupos.pk)
        .exists()
    )
