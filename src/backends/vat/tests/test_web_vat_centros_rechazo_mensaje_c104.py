"""V06.01: un POST rechazado de los modales del centro trae el ``message`` que la vista nativa envía a su script. Datos sintéticos."""

import itertools

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from rest_framework.test import APIClient

from core.models import Localidad, Municipio, Provincia
from VAT.models import Centro

pytestmark = pytest.mark.django_db

_COUNTER = itertools.count()


def _editor(*codes):
    user = get_user_model().objects.create_user(f"rm{next(_COUNTER)}")
    user.user_permissions.add(
        *Permission.objects.filter(content_type__app_label="VAT", codename__in=codes)
    )
    permiso, _ = Permission.objects.get_or_create(
        content_type=ContentType.objects.get_for_model(Group),
        codename="role_vat_sse",
        defaults={"name": "role_vat_sse"},
    )
    user.user_permissions.add(permiso)
    client = APIClient()
    client.force_login(user)
    return client


@pytest.fixture(name="centro")
def centro_fixture():
    provincia = Provincia.objects.create(nombre="Buenos Aires")
    municipio = Municipio.objects.create(nombre="La Plata", provincia=provincia)
    localidad = Localidad.objects.create(nombre="Tolosa", municipio=municipio)
    return Centro.objects.create(
        nombre="CFP 401",
        codigo="060144900",
        provincia=provincia,
        municipio=municipio,
        localidad=localidad,
    )


def test_a_rejected_contact_carries_the_native_message(centro):
    respuesta = _editor("view_centro", "add_institucioncontacto").post(
        f"/api/web/vat/institucion/contactos/nuevo/?centro={centro.pk}",
        {"nombre_contacto": "Ana", "telefono_contacto": "abc"},
    )
    assert respuesta.status_code == 400
    assert respuesta.json()["message"] == (
        "No se pudo guardar el contacto. Revisá los datos e intentá nuevamente."
    )
    assert respuesta.json()["fields"]


def test_a_rejected_location_carries_the_native_message(centro):
    respuesta = _editor("view_centro", "add_institucionubicacion").post(
        f"/api/web/vat/institucion/ubicaciones/nuevo/?centro={centro.pk}", {}
    )
    assert respuesta.status_code == 400
    assert respuesta.json()["message"] == (
        "No se pudo guardar la ubicación. Revisá los datos e intentá nuevamente."
    )


def test_a_rejected_course_carries_the_native_message(centro):
    respuesta = _editor("view_centro", "add_curso").post(
        f"/api/web/vat/centros-acciones/cursos/nuevo/?centro={centro.pk}",
        {"nombre": "Curso", "estado": "activo", "plan_estudio": ""},
    )
    assert respuesta.status_code == 400
    assert respuesta.json()["message"] == (
        "No se pudo guardar el curso. Revisa los datos e intenta nuevamente."
    )


def test_a_form_whose_native_view_sends_no_message_adds_none(centro):
    respuesta = _editor("view_centro", "add_modalidadcursada").post(
        "/api/web/vat/catalogos/modalidades-cursado/nueva/", {}
    )
    assert respuesta.status_code == 400
    assert "message" not in respuesta.json()
