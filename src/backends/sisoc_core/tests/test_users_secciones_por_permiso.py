"""Secciones del ABM de usuarios habilitadas por permiso."""

import importlib

import pytest
from django.apps import apps as django_apps
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from core.constants import UserGroups
from core.models import Provincia
from usuarios.forms import CustomUserChangeForm, UserCreationForm
from users.secciones_usuario import (
    SECCION_ADMINISTRACION,
    SECCION_DATACALLE,
    SECCIONES_COMEDORES,
    SECCIONES_USUARIO,
    TODAS_LAS_SECCIONES,
    permiso_de_seccion,
    secciones_habilitadas,
)

TARJETAS_COMEDORES = (
    b'id="mobile-access-card"',
    b'id="territorial-comedor-card"',
    b'id="backoffice-equipos-card"',
)
TARJETA_DATACALLE = b'id="relevador-calle-card"'
TARJETA_ADMINISTRACION = b'id="backoffice-admin-card"'
TARJETAS_GENERALES = (
    b'id="backoffice-permisos-card"',
    b'id="backoffice-config-card"',
)


def _permiso(codigo):
    app_label, codename = codigo.split(".", 1)
    permiso, _ = Permission.objects.get_or_create(
        content_type=ContentType.objects.get_for_model(Group),
        codename=codename,
        defaults={"name": codename},
    )
    assert app_label == "auth"
    return permiso


def _permiso_abm(codename):
    return Permission.objects.get(content_type__app_label="auth", codename=codename)


def _actor(username, *secciones):
    actor = User.objects.create_user(username=username, password="secret")
    actor.user_permissions.add(
        _permiso_abm("add_user"),
        _permiso_abm("change_user"),
        *(_permiso(permiso_de_seccion(clave)) for clave in secciones),
    )
    return User.objects.get(pk=actor.pk)


@pytest.mark.django_db
def test_superusuario_y_sin_actor_ven_todas_las_secciones():
    superusuario = User.objects.create_superuser(username="super_secc", password="x")

    assert secciones_habilitadas(superusuario) == TODAS_LAS_SECCIONES
    assert secciones_habilitadas(None) == TODAS_LAS_SECCIONES


@pytest.mark.django_db
def test_sin_permisos_de_seccion_solo_quedan_las_generales(client):
    actor = _actor("sin_secciones")

    assert secciones_habilitadas(actor) == frozenset()
    client.force_login(actor)
    contenido = client.get(reverse("usuario_crear")).content

    for tarjeta in TARJETAS_GENERALES:
        assert tarjeta in contenido
    for tarjeta in (*TARJETAS_COMEDORES, TARJETA_DATACALLE, TARJETA_ADMINISTRACION):
        assert tarjeta not in contenido


@pytest.mark.django_db
def test_gestor_comedores_no_ve_datacalle_ni_administracion(client):
    actor = _actor("gestor_comedores", *SECCIONES_COMEDORES)
    client.force_login(actor)

    contenido = client.get(reverse("usuario_crear")).content

    for tarjeta in TARJETAS_COMEDORES:
        assert tarjeta in contenido
    assert TARJETA_DATACALLE not in contenido
    assert TARJETA_ADMINISTRACION not in contenido


@pytest.mark.django_db
def test_gestor_datacalle_no_ve_las_secciones_de_comedores(client):
    actor = _actor("gestor_datacalle", SECCION_DATACALLE)
    client.force_login(actor)

    contenido = client.get(reverse("usuario_crear")).content

    assert TARJETA_DATACALLE in contenido
    for tarjeta in (*TARJETAS_COMEDORES, TARJETA_ADMINISTRACION):
        assert tarjeta not in contenido


@pytest.mark.django_db
def test_un_post_armado_no_habilita_secciones_ajenas():
    provincia = Provincia.objects.create(nombre="Provincia Secciones")
    actor = _actor("gestor_datacalle_post", SECCION_DATACALLE)
    extra = _permiso_abm("delete_user")

    form = UserCreationForm(
        actor=actor,
        data={
            "username": "creado_por_datacalle",
            "password": "Sisoc12345!",
            "tipo_usuario": "interno",
            "es_territorial_comedor": "on",
            "provincias_territorial": [provincia.pk],
            "es_coordinador": "on",
            "user_permissions": [extra.pk],
        },
    )

    assert form.is_valid(), form.errors
    creado = form.save()
    creado.profile.refresh_from_db()
    assert creado.profile.es_territorial_comedor is False
    assert creado.profile.es_coordinador is False
    assert not creado.user_permissions.filter(pk=extra.pk).exists()


@pytest.mark.django_db
def test_editar_sin_la_seccion_datacalle_conserva_el_relevador():
    cordoba = Provincia.objects.create(nombre="Córdoba Secciones")
    salta = Provincia.objects.create(nombre="Salta Secciones")
    relevador = User.objects.create_user(username="relevador_secc", password="x")
    relevador.profile.es_relevador_calle = True
    relevador.profile.datacalle_rol = "entrevistador"
    relevador.profile.save()
    relevador.profile.relevador_calle_provincias.create(provincia=cordoba)

    # Gestor de Comedores con alcance provincial de una sola provincia: sin la
    # sección DataCalle, su provincia no puede pisar la del relevador.
    actor = _actor("gestor_comedores_edita", *SECCIONES_COMEDORES)
    actor.profile.es_usuario_provincial = True
    actor.profile.save()
    actor.profile.territorial_scopes.create(provincia=salta)

    form = CustomUserChangeForm(
        instance=relevador,
        actor=actor,
        data={
            "username": relevador.username,
            "first_name": "Editado",
            "tipo_usuario": "interno",
            "email": "",
            "password": "",
            "es_relevador_calle": "",
            "datacalle_rol": "",
        },
    )

    assert form.is_valid(), form.errors
    form.save()
    relevador.profile.refresh_from_db()
    assert relevador.first_name == "Editado"
    assert relevador.profile.es_relevador_calle is True
    assert relevador.profile.datacalle_rol == "entrevistador"
    assert list(
        relevador.profile.relevador_calle_provincias.values_list(
            "provincia_id", flat=True
        )
    ) == [cordoba.pk]


@pytest.mark.django_db
def test_administracion_habilita_permisos_directos_y_delegacion():
    actor = _actor("gestor_admin", SECCION_ADMINISTRACION)

    form = UserCreationForm(actor=actor)

    assert form.can_manage_direct_permissions is True
    assert form.can_manage_delegation is True
    assert form.fields["user_permissions"].disabled is False
    assert form.fields["es_relevador_calle"].disabled is True
    assert form.fields["es_representante_pwa"].disabled is True


@pytest.mark.django_db
def test_seed_de_roles_por_seccion():
    def secciones_del_grupo(nombre):
        grupo = Group.objects.get(name=nombre)
        codigos = set(grupo.permissions.values_list("codename", flat=True))
        return {
            seccion.clave
            for seccion in SECCIONES_USUARIO
            if seccion.permiso.split(".", 1)[1] in codigos
        }

    from django.core.management import call_command

    call_command("create_groups", verbosity=0)

    assert secciones_del_grupo(UserGroups.ADMIN) == TODAS_LAS_SECCIONES
    assert secciones_del_grupo(UserGroups.USUARIOS_GESTOR_COMEDORES) == set(
        SECCIONES_COMEDORES
    )
    assert secciones_del_grupo("Coordinador DataCalle") == {SECCION_DATACALLE}
    assert secciones_del_grupo("Administrador DataCalle") == {SECCION_DATACALLE}


@pytest.mark.django_db
def test_migracion_conserva_lo_que_cada_perfil_ya_veia():
    migracion = importlib.import_module(
        "users.migrations.0055_usuarios_secciones_por_permiso"
    )
    add_user = _permiso_abm("add_user")

    generico, _ = Group.objects.get_or_create(name="Grupo ABM genérico")
    cdi, _ = Group.objects.get_or_create(name=UserGroups.CDI_REFERENTE_CENTRO)
    datacalle, _ = Group.objects.get_or_create(name="Administrador DataCalle")
    sin_abm, _ = Group.objects.get_or_create(name="Grupo sin ABM")
    for grupo in (generico, cdi, datacalle, sin_abm):
        grupo.permissions.remove(
            *Permission.objects.filter(codename__startswith="role_usuarios_seccion_")
        )
    for grupo in (generico, cdi, datacalle):
        grupo.permissions.add(add_user)
    directo = User.objects.create_user(username="abm_directo", password="x")
    directo.user_permissions.add(add_user)

    migracion.asignar(django_apps, None)

    def secciones(grupo_o_usuario, relacion):
        codigos = set(
            getattr(grupo_o_usuario, relacion).values_list("codename", flat=True)
        )
        return {
            seccion.clave
            for seccion in SECCIONES_USUARIO
            if seccion.permiso.split(".", 1)[1] in codigos
        }

    assert secciones(generico, "permissions") == TODAS_LAS_SECCIONES
    assert secciones(cdi, "permissions") == set()
    assert secciones(datacalle, "permissions") == {SECCION_DATACALLE}
    assert secciones(sin_abm, "permissions") == set()
    assert secciones(directo, "user_permissions") == TODAS_LAS_SECCIONES
