"""Issue #2444: carga de Profile.rol territorial PNUD por data migration."""

import importlib
from types import SimpleNamespace

import pytest
from django.apps import apps as global_apps
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import DEFAULT_DB_ALIAS, migrations

from users.models import Profile

pytestmark = pytest.mark.django_db
User = get_user_model()

_migration = importlib.import_module(
    "users.migrations.0056_issue_2444_roles_territoriales_pnud"
)

ROLES_VALIDOS = {"TERRITORIAL PNUD", "RESPONSABLE TERRITORIAL PNUD"}


def _schema_editor():
    return SimpleNamespace(connection=SimpleNamespace(alias=DEFAULT_DB_ALIAS))


def _ejecutar():
    _migration.cargar_roles_territoriales(global_apps, _schema_editor())


def _roles(**roles):
    """Reemplaza la lista de la migración por una acotada al test."""
    return tuple(roles.items())


def test_listado_tiene_los_100_usuarios_del_csv_sin_duplicados():
    usernames = [username for username, _rol in _migration.ROLES_POR_USERNAME]

    assert len(usernames) == 100
    assert len(set(usernames)) == 100
    assert {rol for _u, rol in _migration.ROLES_POR_USERNAME} == ROLES_VALIDOS
    assert dict(_migration.ROLES_POR_USERNAME)["vmverbauwede-2"] == (
        "RESPONSABLE TERRITORIAL PNUD"
    )
    assert dict(_migration.ROLES_POR_USERNAME)["rodalaya"] == "TERRITORIAL PNUD"


def test_actualiza_solo_el_rol_de_los_usuarios_listados(monkeypatch):
    monkeypatch.setattr(
        _migration,
        "ROLES_POR_USERNAME",
        _roles(tuno="TERRITORIAL PNUD", rdos="RESPONSABLE TERRITORIAL PNUD"),
    )
    grupo = Group.objects.create(name="Grupo existente")
    tuno = User.objects.create_user(
        username="tuno", email="t@x.com", first_name="Ana", last_name="Uno"
    )
    tuno.groups.add(grupo)
    tuno.profile.rol = "TECNICO"
    tuno.profile.save(update_fields=["rol"])
    rdos = User.objects.create_user(username="rdos")
    ajeno = User.objects.create_user(username="ajeno")
    ajeno.profile.rol = "OTRO"
    ajeno.profile.save(update_fields=["rol"])

    _ejecutar()

    tuno.refresh_from_db()
    assert tuno.profile.rol == "TERRITORIAL PNUD"
    assert (tuno.email, tuno.first_name, tuno.last_name) == ("t@x.com", "Ana", "Uno")
    assert list(tuno.groups.all()) == [grupo]
    assert Profile.objects.get(user=rdos).rol == "RESPONSABLE TERRITORIAL PNUD"
    assert Profile.objects.get(user=ajeno).rol == "OTRO"


def test_usuarios_inexistentes_se_informan_y_no_se_crean(monkeypatch, capsys):
    monkeypatch.setattr(
        _migration,
        "ROLES_POR_USERNAME",
        _roles(existe="TERRITORIAL PNUD", fantasma="TERRITORIAL PNUD"),
    )
    User.objects.create_user(username="existe")

    _ejecutar()

    salida = capsys.readouterr().out
    assert not User.objects.filter(username="fantasma").exists()
    assert "No encontrados (1): fantasma" in salida
    assert "Actualizados: 1" in salida


def test_username_con_otra_capitalizacion_se_actualiza(monkeypatch, capsys):
    monkeypatch.setattr(
        _migration, "ROLES_POR_USERNAME", _roles(rodalaya="TERRITORIAL PNUD")
    )
    user = User.objects.create_user(username="RodAlaya")

    _ejecutar()

    assert Profile.objects.get(user=user).rol == "TERRITORIAL PNUD"
    assert "No encontrados (0):" in capsys.readouterr().out


def test_crea_el_perfil_si_el_usuario_no_lo_tiene(monkeypatch):
    monkeypatch.setattr(
        _migration, "ROLES_POR_USERNAME", _roles(sinperfil="TERRITORIAL PNUD")
    )
    user = User.objects.create_user(username="sinperfil")
    Profile.objects.filter(user=user).delete()

    _ejecutar()

    assert Profile.objects.get(user=user).rol == "TERRITORIAL PNUD"


def test_informa_el_valor_anterior_de_cada_usuario(monkeypatch, capsys):
    monkeypatch.setattr(
        _migration, "ROLES_POR_USERNAME", _roles(tuno="TERRITORIAL PNUD")
    )
    user = User.objects.create_user(username="tuno")
    user.profile.rol = "TECNICO"
    user.profile.save(update_fields=["rol"])

    _ejecutar()

    assert "tuno: 'TECNICO' -> 'TERRITORIAL PNUD'" in capsys.readouterr().out


def test_es_idempotente(monkeypatch, capsys):
    monkeypatch.setattr(
        _migration, "ROLES_POR_USERNAME", _roles(tuno="TERRITORIAL PNUD")
    )
    User.objects.create_user(username="tuno")

    _ejecutar()
    capsys.readouterr()
    _ejecutar()

    salida = capsys.readouterr().out
    assert "Actualizados: 0" in salida
    assert "Sin cambios: 1" in salida


def test_reversa_no_modifica_datos():
    operacion = _migration.Migration.operations[0]

    assert isinstance(operacion, migrations.RunPython)
    assert operacion.reverse_code is migrations.RunPython.noop
