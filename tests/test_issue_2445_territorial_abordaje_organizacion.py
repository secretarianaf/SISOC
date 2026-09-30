"""Issue #2445: Territorial Asignado Abordaje Comunitario en el legajo de Organización."""

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from core.models import Provincia
from organizaciones.forms import OrganizacionForm
from organizaciones.models import Organizacion
from users.services_territoriales import (
    ROL_RESPONSABLE_TERRITORIAL_PNUD,
    ROL_TERRITORIAL_PNUD,
    etiqueta_territorial,
    usuarios_territoriales_pnud,
)

pytestmark = pytest.mark.django_db
User = get_user_model()

CAMPO = "territoriales_abordaje_comunitario"


def _usuario(username, rol=None, *, first_name="", last_name="", is_active=True):
    user = User.objects.create_user(
        username=username,
        password="pwd",
        first_name=first_name,
        last_name=last_name,
        is_active=is_active,
    )
    user.profile.rol = rol
    user.profile.save(update_fields=["rol"])
    return user


@pytest.fixture
def territorial():
    return _usuario("tpnud", ROL_TERRITORIAL_PNUD, first_name="Ana", last_name="Zapata")


@pytest.fixture
def responsable():
    return _usuario(
        "rtpnud",
        ROL_RESPONSABLE_TERRITORIAL_PNUD,
        first_name="Bruno",
        last_name="Alvarez",
    )


@pytest.fixture
def provincia():
    return Provincia.objects.create(nombre="Buenos Aires")


def _payload(nombre, provincia, territoriales=()):
    return {
        "nombre": nombre,
        "cuit": "",
        "telefono": "",
        "email": "",
        "domicilio": "",
        "localidad": "",
        "partido": "",
        "provincia": str(provincia.pk),
        "municipio": "",
        "tipo_entidad": "",
        "subtipo_entidad": "",
        "fecha_vencimiento": "2030-01-01",
        "sigla": "",
        "cuil_duplicado_confirmado": "",
        "cuil_duplicado_confirmado_valor": "",
        CAMPO: [str(user.pk) for user in territoriales],
    }


def test_elegibles_son_solo_usuarios_activos_con_rol_territorial_pnud(
    territorial, responsable
):
    _usuario("otro_rol", "TECNICO")
    _usuario("sin_rol")
    _usuario("inactivo", ROL_TERRITORIAL_PNUD, is_active=False)
    en_minuscula = _usuario(
        "minuscula", ROL_TERRITORIAL_PNUD.lower(), last_name="Medina"
    )

    elegibles = list(usuarios_territoriales_pnud())

    # Ordenados por apellido; el rol se compara sin distinguir mayúsculas.
    assert elegibles == [responsable, en_minuscula, territorial]


def test_etiqueta_muestra_apellido_nombre_y_username(territorial):
    assert etiqueta_territorial(territorial) == "Zapata, Ana (tpnud)"
    assert etiqueta_territorial(_usuario("solo_username")) == "solo_username"


def test_formulario_ofrece_elegibles_y_no_es_obligatorio(territorial, responsable):
    _usuario("otro_rol", "TECNICO")

    field = OrganizacionForm().fields[CAMPO]

    assert field.required is False
    assert list(field.queryset) == [responsable, territorial]
    assert field.label_from_instance(territorial) == "Zapata, Ana (tpnud)"


def test_alta_guarda_territoriales_seleccionados(
    client, admin_user, provincia, territorial, responsable
):
    client.force_login(admin_user)

    response = client.post(
        reverse("organizacion_crear"),
        _payload("Org nueva", provincia, [territorial, responsable]),
    )

    assert response.status_code == 302, response.content[:500]
    organizacion = Organizacion.objects.get(nombre="Org nueva")
    assert set(getattr(organizacion, CAMPO).all()) == {territorial, responsable}


def test_alta_sin_territoriales_es_valida(client, admin_user, provincia):
    client.force_login(admin_user)

    response = client.post(reverse("organizacion_crear"), _payload("Org", provincia))

    assert response.status_code == 302, response.content[:500]
    assert not getattr(Organizacion.objects.get(nombre="Org"), CAMPO).exists()


def test_edicion_conserva_territorial_asignado_que_perdio_el_rol(
    client, admin_user, provincia, territorial
):
    organizacion = Organizacion.objects.create(nombre="Org", provincia=provincia)
    getattr(organizacion, CAMPO).add(territorial)
    territorial.profile.rol = "OTRO ROL"
    territorial.profile.save(update_fields=["rol"])

    form = OrganizacionForm(instance=organizacion)
    assert territorial in form.fields[CAMPO].queryset

    client.force_login(admin_user)
    response = client.post(
        reverse("organizacion_editar", kwargs={"pk": organizacion.pk}),
        _payload("Org", provincia, [territorial]),
    )

    assert response.status_code == 302, response.content[:500]
    assert list(getattr(organizacion, CAMPO).all()) == [territorial]


def test_detalle_muestra_territoriales_en_informacion_de_la_organizacion(
    client, admin_user, provincia, territorial
):
    organizacion = Organizacion.objects.create(nombre="Org", provincia=provincia)
    getattr(organizacion, CAMPO).add(territorial)
    client.force_login(admin_user)

    response = client.get(
        reverse("organizacion_detalle", kwargs={"pk": organizacion.pk})
    )

    assert response.status_code == 200
    html = response.content.decode()
    assert "Territorial Asignado Abordaje Comunitario:" in html
    assert "Zapata, Ana (tpnud)" in html
