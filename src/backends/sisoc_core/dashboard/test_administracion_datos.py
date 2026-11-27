"""Acceso y gestión operativa del catálogo para el equipo de Datos."""

import pytest
from unittest.mock import patch
from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.test import Client
from django.urls import resolve, reverse
from auditlog.models import LogEntry
from django.contrib.contenttypes.models import ContentType

from dashboard.models import Tablero
from dashboard.forms_datos import TableroOperativoForm

pytestmark = pytest.mark.django_db


def test_catalogo_requiere_rol_o_superusuario_y_no_administra_usuarios():
    call_command("create_groups", verbosity=0)
    url = reverse("dashboard_administracion_datos")
    usuario = User.objects.create_user(username="sin_rol")
    client = Client()
    client.force_login(usuario)
    assert client.get(url).status_code == 403
    assert client.post(url, {"tablero": "1"}).status_code == 403
    usuario.is_superuser = True
    usuario.save(update_fields=["is_superuser"])
    assert client.get(url).status_code == 200
    usuario.is_superuser = False
    usuario.save(update_fields=["is_superuser"])
    usuario.groups.add(Group.objects.get(name="Equipo de Datos"))
    assert client.get(url).status_code == 200
    assert not usuario.has_perm("auth.add_user")


def test_catalogo_edita_solo_campos_operativos():
    call_command("create_groups", verbosity=0)
    usuario = User.objects.create_user(username="datos")
    usuario.groups.add(Group.objects.get(name="Equipo de Datos"))
    tablero = Tablero.objects.create(nombre="Original", slug="seguro", activo=True)
    client = Client(enforce_csrf_checks=True)
    client.force_login(usuario)
    url = reverse("dashboard_administracion_datos")
    assert client.post(url, {"tablero": tablero.pk}).status_code == 403
    client.get(url)
    token = client.cookies["csrftoken"].value
    response = client.post(
        url,
        {
            "tablero": tablero.pk,
            "nombre": "Nuevo",
            "visible_menu": "on",
            "slug": "otro",
        },
        HTTP_X_CSRFTOKEN=token,
    )
    assert response.status_code == 302
    tablero.refresh_from_db()
    assert (tablero.nombre, tablero.activo, tablero.visible_menu, tablero.slug) == (
        "Nuevo",
        False,
        True,
        "seguro",
    )
    assert LogEntry.objects.filter(
        content_type=ContentType.objects.get_for_model(Tablero),
        object_pk=str(tablero.pk),
        actor=usuario,
        action=LogEntry.Action.UPDATE,
    ).exists()


def test_editar_abre_el_modal_individual_del_tablero():
    usuario = User.objects.create_user(username="editor", is_superuser=True)
    primero = Tablero.objects.create(nombre="Primero", slug="primero")
    segundo = Tablero.objects.create(nombre="Segundo", slug="segundo")
    client = Client()
    client.force_login(usuario)

    response = client.get(reverse("dashboard_administracion_datos"))

    assert response.status_code == 200
    html = response.content.decode()
    for tablero in (primero, segundo):
        modal_id = f"editar-tablero-{tablero.pk}"
        assert f'data-bs-target="#{modal_id}"' in html
        assert f'id="{modal_id}"' in html
        assert f'aria-labelledby="{modal_id}-titulo"' in html
    assert 'data-reabrir-modal="' not in html


def test_edicion_invalida_reabre_solo_el_modal_enviado_con_los_errores():
    usuario = User.objects.create_user(username="editor", is_superuser=True)
    primero = Tablero.objects.create(nombre="Primero", slug="primero")
    segundo = Tablero.objects.create(
        nombre="Segundo", slug="segundo", activo=True, visible_menu=False
    )
    client = Client()
    client.force_login(usuario)

    response = client.post(
        reverse("dashboard_administracion_datos"),
        {"tablero": segundo.pk, "nombre": "", "visible_menu": "on"},
    )

    assert response.status_code == 400
    html = response.content.decode()
    assert f'data-reabrir-modal="editar-tablero-{segundo.pk}"' in html
    assert f'data-reabrir-modal="editar-tablero-{primero.pk}"' not in html
    assert f'id="error_1_id_{segundo.pk}_nombre"' in html
    assert f'id="error_1_id_{primero.pk}_nombre"' not in html
    segundo.refresh_from_db()
    assert (segundo.nombre, segundo.activo, segundo.visible_menu) == (
        "Segundo",
        True,
        False,
    )


def test_preserva_cambios_tecnicos_concurrentes():
    call_command("create_groups", verbosity=0)
    usuario = User.objects.create_user(username="concurrente")
    usuario.groups.add(Group.objects.get(name="Equipo de Datos"))
    tablero = Tablero.objects.create(nombre="Original", slug="antes")
    client = Client()
    client.force_login(usuario)
    validar = TableroOperativoForm.is_valid

    def cambio_concurrente(form):
        resultado = validar(form)
        Tablero.objects.filter(pk=tablero.pk).update(slug="despues")
        return resultado

    with patch.object(TableroOperativoForm, "is_valid", cambio_concurrente):
        response = client.post(
            reverse("dashboard_administracion_datos"),
            {"tablero": tablero.pk, "nombre": "Nuevo", "activo": "on"},
        )
    tablero.refresh_from_db()
    assert response.status_code == 302
    assert tablero.slug == "despues"


def test_slug_administracion_datos_sigue_siendo_tablero():
    tablero = Tablero.objects.create(nombre="Existente", slug="administracion-datos")
    assert tablero.get_absolute_url() == "/dashboard/administracion-datos/"
    assert resolve(tablero.get_absolute_url()).url_name == "dashboard_tablero"


def test_acciones_de_usuarios_respetan_permiso_de_alta():
    from django.contrib.auth.models import Permission

    call_command("create_groups", verbosity=0)
    usuario = User.objects.create_user(username="datos")
    usuario.groups.add(Group.objects.get(name="Equipo de Datos"))
    client = Client()
    client.force_login(usuario)
    url = reverse("dashboard_administracion_datos")
    acciones = [reverse("usuario_crear"), reverse("usuarios_importar")]

    def enlaces():
        response = client.get(url)
        assert response.status_code == 200
        return response.content.decode()

    sin_permiso = enlaces()
    for accion in acciones:
        assert client.get(accion).status_code == 403
        assert f'href="{accion}"' not in sin_permiso

    usuario.user_permissions.add(
        Permission.objects.get(content_type__app_label="auth", codename="add_user")
    )
    con_permiso = enlaces()
    for accion in acciones:
        assert client.get(accion).status_code == 200
        assert f'href="{accion}"' in con_permiso
