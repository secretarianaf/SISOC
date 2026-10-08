"""Permisos por grupo y alcance del alta de sedes adicionales."""

from pathlib import Path

import pytest
from django.contrib.auth.context_processors import PermWrapper
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse
from django.test import override_settings
from django.template import Context, Engine
from django.urls import path, reverse

from core.decorators import permissions_any_required
from core.models import Localidad, Municipio, Provincia
from VAT.models import Centro, InstitucionUbicacion
from VAT.services.access_scope import can_user_edit_centro
from VAT.views.institucion import InstitucionUbicacionCreateView

urlpatterns = [
    path(
        "ubicaciones/nuevo/",
        permissions_any_required(["VAT.add_institucionubicacion"])(
            InstitucionUbicacionCreateView.as_view()
        ),
        name="vat_institucion_ubicacion_create",
    ),
    path(
        "ubicaciones/",
        lambda request: HttpResponse(),
        name="vat_institucion_ubicacion_list",
    ),
]

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def ubicacion_urls():
    with override_settings(ROOT_URLCONF=__name__):
        yield


@pytest.fixture
def sede_data():
    provincia = Provincia.objects.create(nombre="Provincia de prueba")
    municipio = Municipio.objects.create(nombre="Departamento", provincia=provincia)
    localidad = Localidad.objects.create(nombre="Localidad", municipio=municipio)
    user = User.objects.create_user(username="operador-sedes")
    role, _ = Permission.objects.get_or_create(
        content_type=ContentType.objects.get_for_model(Group),
        codename="role_referentecentrovat",
        defaults={"name": "Referente de centro VAT"},
    )
    group = Group.objects.create(name="Operadores sedes prueba")
    group.permissions.add(role)
    user.groups.add(group)
    centro = Centro.objects.create(
        codigo="SEDES-TEST",
        nombre="Centro asignado",
        provincia=provincia,
        municipio=municipio,
        localidad=localidad,
        referente=user,
    )
    return user, group, centro, localidad


def _habilitar_alta(group):
    group.permissions.add(
        Permission.objects.get(
            content_type__app_label="VAT", codename="add_institucionubicacion"
        )
    )


def _crear_sede(client, centro, localidad, *, bloquear_centro=False):
    url = reverse("vat_institucion_ubicacion_create")
    if bloquear_centro:
        url += f"?centro={centro.pk}"
    return client.post(
        url,
        {
            "centro": centro.pk,
            "departamento": localidad.municipio_id,
            "localidad": localidad.pk,
            "rol_ubicacion": "anexo",
            "nombre_ubicacion": "Sede secundaria",
        },
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )


def test_grupo_sin_permiso_no_puede_crear_sede(client, sede_data):
    user, _, centro, localidad = sede_data
    client.force_login(user)
    response = _crear_sede(client, centro, localidad)
    assert response.status_code == 403
    assert not InstitucionUbicacion.objects.exists()


@pytest.mark.parametrize("habilitar", [False, True])
def test_boton_agregar_sede_depende_del_permiso_del_grupo(sede_data, habilitar):
    user, group, centro, _ = sede_data
    if habilitar:
        _habilitar_alta(group)
    template = (
        Path(__file__).resolve().parents[1]
        / "VAT/templates/vat/centros/centro_detail.html"
    ).read_text(encoding="utf-8")
    button_index = template.index('data-bs-target="#modalUbicacion"')
    fragment_start = template.rfind("{% if ", 0, button_index)
    fragment_end = template.index("{% endif %}", button_index) + len("{% endif %}")
    content = (
        Engine()
        .from_string(template[fragment_start:fragment_end])
        .render(
            Context(
                {
                    "can_edit_centro": can_user_edit_centro(user, centro),
                    "perms": PermWrapper(user),
                }
            )
        )
    )
    assert ("Agregar sede" in content) is habilitar


@pytest.mark.parametrize("bloquear_centro", [False, True])
def test_grupo_con_permiso_crea_sede_asignada(client, sede_data, bloquear_centro):
    user, group, centro, localidad = sede_data
    _habilitar_alta(group)
    client.force_login(user)
    response = _crear_sede(client, centro, localidad, bloquear_centro=bloquear_centro)
    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert InstitucionUbicacion.objects.get().centro_id == centro.pk


def test_quitar_permiso_del_grupo_bloquea_nuevas_sedes(client, sede_data):
    user, group, centro, localidad = sede_data
    _habilitar_alta(group)
    client.force_login(user)
    assert _crear_sede(client, centro, localidad).status_code == 200
    group.permissions.remove(
        Permission.objects.get(
            content_type__app_label="VAT", codename="add_institucionubicacion"
        )
    )
    assert _crear_sede(client, centro, localidad).status_code == 403
    assert InstitucionUbicacion.objects.count() == 1


def test_permiso_puede_venir_de_otro_grupo_independiente(client, sede_data):
    user, _, centro, localidad = sede_data
    group = Group.objects.create(name="Habilitar sedes adicionales prueba")
    _habilitar_alta(group)
    user.groups.add(group)
    client.force_login(user)
    assert _crear_sede(client, centro, localidad).status_code == 200


@pytest.mark.parametrize("bloquear_centro", [False, True])
def test_permiso_no_habilita_crear_en_centro_ajeno(client, sede_data, bloquear_centro):
    user, group, centro, localidad = sede_data
    _habilitar_alta(group)
    centro.referente = None
    centro.save(update_fields=["referente"])
    client.force_login(user)
    assert (
        _crear_sede(
            client, centro, localidad, bloquear_centro=bloquear_centro
        ).status_code
        == 403
    )
    assert not InstitucionUbicacion.objects.exists()


def test_formulario_solo_ofrece_centros_gestionables(rf, sede_data):
    user, group, centro, _ = sede_data
    _habilitar_alta(group)
    Centro.objects.create(codigo="SEDES-AJENO", nombre="Centro ajeno")
    request = rf.get(reverse("vat_institucion_ubicacion_create"))
    request.user = user
    view = InstitucionUbicacionCreateView()
    view.setup(request)
    view.object = None
    form = view.get_form()
    assert list(form.fields["centro"].queryset) == [centro]
