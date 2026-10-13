"""SIMEPI - Administrador ve y edita solo a los usuarios de CDI.

Antes veía a todos los usuarios del sistema pero solo podía editar a los de
SIMEPI - Equipo Nacional, así que al abrir cualquier otro recibía un 404.
"""

import pytest
from django.contrib.auth.models import Group, Permission, User
from django.test import RequestFactory
from django.urls import reverse

from core.constants import UserGroups
from users.services import UsuariosService
from users.services_delegation import effective_delegatable_group_ids


GRUPOS_CDI_ADMINISTRABLES = (
    UserGroups.SIMEPI_EQUIPO_NACIONAL,
    UserGroups.SIMEPI_EGP,
    UserGroups.SIMEPI_ANALISTA_DATOS,
    UserGroups.SIMEPI_AUDITORIA,
    UserGroups.CDI_REFERENTE_CENTRO,
    UserGroups.CDI_TRABAJADOR,
)


def _grupo(nombre):
    return Group.objects.get_or_create(name=nombre)[0]


def _usuario(username, *grupos):
    user = User.objects.create_user(username=username, password="test1234")
    user.groups.add(*(_grupo(nombre) for nombre in grupos))
    return user


@pytest.fixture
def admin_simepi(db):
    for nombre in GRUPOS_CDI_ADMINISTRABLES:
        _grupo(nombre)
    actor = _usuario("simepi-admin", UserGroups.SIMEPI_ADMINISTRADOR)
    actor.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="auth",
            codename__in=("view_user", "change_user"),
        )
    )
    return User.objects.get(pk=actor.pk)


@pytest.fixture
def usuarios(db):
    cdi = {
        nombre: _usuario(f"cdi-{indice}", nombre)
        for indice, nombre in enumerate(GRUPOS_CDI_ADMINISTRABLES)
    }
    fuera = {
        "otro_programa": _usuario("comedores", "Grupo de otro programa"),
        "mixto": _usuario(
            "mixto", UserGroups.CDI_REFERENTE_CENTRO, "Grupo de otro programa"
        ),
        "sin_grupos": _usuario("sin-grupos"),
        "otro_admin": _usuario("otro-admin", UserGroups.SIMEPI_ADMINISTRADOR),
        "superusuario": User.objects.create_superuser(
            username="super", password="test1234", email="super@example.com"
        ),
    }
    return cdi, fuera


def _listado(actor):
    request = RequestFactory().get("/usuarios/")
    request.user = actor
    return set(
        UsuariosService.get_filtered_usuarios(request).values_list(
            "username", flat=True
        )
    )


@pytest.mark.django_db
def test_admin_delega_todos_los_grupos_cdi_salvo_administrador(admin_simepi):
    delegables = set(
        Group.objects.filter(
            pk__in=effective_delegatable_group_ids(admin_simepi)
        ).values_list("name", flat=True)
    )

    assert delegables == set(GRUPOS_CDI_ADMINISTRABLES)


@pytest.mark.django_db
def test_admin_lista_solo_usuarios_de_cdi(admin_simepi, usuarios):
    cdi, fuera = usuarios

    visibles = _listado(admin_simepi)

    assert {user.username for user in cdi.values()} <= visibles
    assert visibles.isdisjoint(user.username for user in fuera.values())


@pytest.mark.django_db
def test_admin_puede_editar_todo_lo_que_ve(client, admin_simepi, usuarios):
    cdi, _ = usuarios
    client.force_login(admin_simepi)

    for user in cdi.values():
        respuesta = client.get(reverse("usuario_editar", kwargs={"pk": user.pk}))
        assert respuesta.status_code == 200, user.username


@pytest.mark.django_db
@pytest.mark.parametrize(
    "caso", ["otro_programa", "mixto", "sin_grupos", "otro_admin", "superusuario"]
)
def test_admin_no_edita_usuarios_fuera_de_cdi(client, admin_simepi, usuarios, caso):
    _, fuera = usuarios
    client.force_login(admin_simepi)

    respuesta = client.get(reverse("usuario_editar", kwargs={"pk": fuera[caso].pk}))

    assert respuesta.status_code == 404
