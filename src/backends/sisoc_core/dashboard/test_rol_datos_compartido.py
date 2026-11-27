"""El rol de Datos debe ser idéntico en todos los runtimes."""

import pytest
from django.contrib.auth.models import Group, User
from django.core.management import call_command

from dashboard.services.equipo_datos import puede_administrar_tableros as en_dashboard
from iam.roles_datos import puede_administrar_tableros as en_kernel


@pytest.mark.django_db
def test_mismo_rol_explicito_en_kernel_y_dashboard():
    call_command("create_groups", verbosity=0)
    usuario = User.objects.create_user(username="datos")
    assert not en_kernel(usuario) and not en_dashboard(usuario)
    usuario.groups.add(Group.objects.get(name="Equipo de Datos"))
    assert en_kernel(usuario) and en_dashboard(usuario)
    usuario.groups.clear()
    assert not en_kernel(usuario) and not en_dashboard(usuario)


@pytest.mark.django_db
def test_superusuario_activo_puede_administrar_sin_grupo_y_revocacion_es_inmediata():
    usuario = User.objects.create_superuser(username="supervisor", password="x")
    assert en_kernel(usuario) and en_dashboard(usuario)
    User.objects.filter(pk=usuario.pk).update(is_active=False)
    assert not en_kernel(usuario) and not en_dashboard(usuario)
