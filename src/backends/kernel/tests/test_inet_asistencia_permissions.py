"""El grupo docente se crea sin privilegios administrativos."""

from importlib import import_module
from types import SimpleNamespace

import pytest
from django.apps import apps
from django.contrib.auth.models import Group, User
from django.core.management import call_command

from iam.roles_vat import es_usuario_solo_vat, is_inet_asistencia


@pytest.mark.django_db
def test_grupo_asistencia_migracion_y_bootstrap_idempotentes():
    migration = import_module("users.migrations.0062_inet_asistencia")
    schema = SimpleNamespace(connection=SimpleNamespace(alias="default"))
    migration.crear_grupo_asistencia(apps, schema)
    migration.crear_grupo_asistencia(apps, schema)
    call_command("create_groups", verbosity=0)
    group = Group.objects.get(name="INET Asistencia")
    user = User.objects.create_user(username="docente")
    user.groups.add(group)
    assert is_inet_asistencia(user)
    assert es_usuario_solo_vat(user)
    assert user.has_perm("VAT.view_centro")
    assert user.has_perm("VAT.view_comisioncurso")
    assert not user.has_perm("VAT.change_inscripcion")
    assert not user.has_perm("VAT.change_comisioncurso")
    assert not user.has_perm("auth.role_referentecentrovat")
    assert not group.permissions.filter(codename__startswith="delete_").exists()
