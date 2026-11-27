"""Contrato del rol para el futuro administrador de tableros."""

import pytest
from django.contrib.auth.models import AnonymousUser, Group, Permission, User
from django.core.management import call_command

from dashboard.services.equipo_datos import puede_administrar_tableros

pytestmark = pytest.mark.django_db


def test_rol_equipo_datos_no_confiere_administracion_general():
    call_command("create_groups", verbosity=0)
    grupo = Group.objects.get(name="Equipo de Datos")
    assert set(grupo.permissions.values_list("name", flat=True)) == {"Equipo de Datos"}
    assert not grupo.user_set.exists()


def test_guard_admite_rol_explicito_o_superusuario_activo():
    call_command("create_groups", verbosity=0)
    grupo = Group.objects.get(name="Equipo de Datos")
    rol = Permission.objects.get(group=grupo, name="Equipo de Datos")
    usuario = User.objects.create_user(username="datos")
    superusuario = User.objects.create_superuser(username="super", password="synthetic")
    assert not puede_administrar_tableros(AnonymousUser())
    assert not puede_administrar_tableros(usuario)
    assert puede_administrar_tableros(superusuario)
    usuario.groups.add(grupo)
    assert puede_administrar_tableros(usuario)
    usuario.groups.remove(grupo)
    assert not puede_administrar_tableros(usuario)
    usuario.user_permissions.add(rol)
    assert puede_administrar_tableros(usuario)
    usuario.user_permissions.remove(rol)
    otro_grupo = Group.objects.create(name="Otro equipo")
    otro_grupo.permissions.add(rol)
    usuario.groups.add(otro_grupo)
    assert puede_administrar_tableros(usuario)
    otro_grupo.permissions.remove(rol)
    assert not puede_administrar_tableros(usuario)
    superusuario.groups.add(grupo)
    assert puede_administrar_tableros(superusuario)
    usuario.user_permissions.add(rol)
    usuario.is_active = False
    usuario.save(update_fields=["is_active"])
    assert not puede_administrar_tableros(usuario)


def test_rechaza_permiso_homonimo_y_detecta_desactivacion_en_base():
    call_command("create_groups", verbosity=0)
    grupo = Group.objects.get(name="Equipo de Datos")
    rol = Permission.objects.get(group=grupo, codename="role_equipo_de_datos")
    falso = Permission.objects.create(
        content_type=rol.content_type, codename="role_no_es_datos", name=rol.name
    )
    grupo.permissions.add(falso)
    usuario = User.objects.create_user(username="otro")
    usuario.user_permissions.add(falso)
    assert not puede_administrar_tableros(usuario)
    usuario.user_permissions.add(rol)
    grupo.permissions.remove(rol)
    assert puede_administrar_tableros(usuario)
    User.objects.filter(pk=usuario.pk).update(is_active=False)
    assert not puede_administrar_tableros(usuario)


def test_colision_de_rol_no_concede_un_permiso_ajeno():
    from django.contrib.contenttypes.models import ContentType

    content_type = ContentType.objects.get_for_model(Group)
    Permission.objects.filter(
        content_type=content_type, codename="role_equipo_de_datos"
    ).delete()
    ajeno = Permission.objects.create(
        content_type=content_type, codename="role_equipo_de_datos", name="Otro rol"
    )
    call_command("create_groups", verbosity=0)
    grupo = Group.objects.get(name="Equipo de Datos")
    usuario = User.objects.create_user(username="colision")
    usuario.groups.add(grupo)
    assert not grupo.permissions.filter(pk=ajeno.pk).exists()
    assert not puede_administrar_tableros(usuario)


@pytest.mark.parametrize(
    ("codigo", "nombre"),
    [
        ("ROLE_EQUIPO_DE_DATOS", "Equipo de Datos"),
        ("role_equipo_de_datos", "equipo de datos"),
    ],
)
def test_no_acepta_variantes_de_mayusculas_del_rol(codigo, nombre):
    from django.contrib.contenttypes.models import ContentType

    permiso = Permission.objects.create(
        content_type=ContentType.objects.get_for_model(Group),
        codename=codigo,
        name=nombre,
    )
    usuario = User.objects.create_user(username="mayusculas")
    usuario.user_permissions.add(permiso)
    assert not puede_administrar_tableros(usuario)
