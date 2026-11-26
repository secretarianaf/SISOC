"""Native preinscription before and after the ``procesar_preinscripcion`` extraction.

These tests pass unchanged on the base and on the candidate: the native view
keeps its JSON for XHR, its redirect and message for a plain POST, its form
re-render on errors and its 500 text. RENAPER is always simulated.
"""

from datetime import date

import pytest
from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.contrib.messages import get_messages
from django.test import Client

from centrodefamilia.models import (
    Beneficiario,
    BeneficiarioResponsable,
    Centro,
    Responsable,
)
from core.models import Provincia

URL = "/centrodefamilia/beneficiarios/nuevo/"
IMPL = "centrodefamilia.services.beneficiarios_service"
XHR = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}

pytestmark = pytest.mark.django_db


@pytest.fixture(name="client")
def client_fixture(monkeypatch):
    monkeypatch.setattr(
        f"{IMPL}.consultar_datos_renaper", lambda dni, sexo: {"success": False}
    )
    user = User.objects.create_user("nativa_pre")
    user.user_permissions.add(
        Permission.objects.get(
            content_type=ContentType.objects.get_for_model(Centro),
            codename="view_centro",
        )
    )
    client = Client()
    client.force_login(user)
    return client


def _datos(provincia, **over):
    datos = {
        "beneficiario_nombre": "Sofía",
        "beneficiario_apellido": "Pérez",
        "beneficiario_dni": "45111222",
        "beneficiario_cuil": "20451112223",
        "beneficiario_genero": "F",
        "beneficiario_fecha_nacimiento": "2012-03-04",
        "beneficiario_domicilio": "Siempreviva 742",
        "beneficiario_provincia": str(provincia.pk),
        "beneficiario_calle": "Siempreviva",
        "beneficiario_maximo_nivel_educativo": "Primario incompleto",
        "beneficiario_actividad_preferida": ["Deportiva"],
        "responsable_nombre": "Ana",
        "responsable_apellido": "Resp",
        "responsable_dni": "30111222",
        "responsable_cuil": "27301112224",
        "responsable_genero": "F",
        "responsable_fecha_nacimiento": "1985-01-02",
        "responsable_vinculo_parental": "Padre/Madre",
        "responsable_calle": "Siempreviva",
        "responsable_provincia": str(provincia.pk),
    }
    datos.update(over)
    return {k: v for k, v in datos.items() if v is not None}


@pytest.fixture(name="provincia")
def provincia_fixture():
    return Provincia.objects.create(nombre="Provincia Nativa")


def test_xhr_success_json_message_and_rows(client, provincia):
    respuesta = client.post(URL, _datos(provincia), **XHR)

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "status": "success",
        "message": "Preinscripción confirmada exitosamente",
    }
    beneficiario = Beneficiario.objects.get(dni=45111222)
    assert BeneficiarioResponsable.objects.filter(
        beneficiario=beneficiario, vinculo_parental="Padre/Madre"
    ).exists()
    assert [str(m) for m in get_messages(respuesta.wsgi_request)] == [
        "Datos cargados con éxito"
    ]


def test_plain_post_redirects_to_the_form(client, provincia):
    respuesta = client.post(URL, _datos(provincia))

    assert (respuesta.status_code, respuesta["Location"]) == (302, URL)


def test_xhr_errors_and_plain_rerender(client, provincia):
    sin_vinculo = client.post(
        URL, _datos(provincia, responsable_vinculo_parental=None), **XHR
    )
    assert (sin_vinculo.status_code, sin_vinculo.json()) == (
        400,
        {"status": "error", "errors": {}},
    )
    invalido = client.post(
        URL, _datos(provincia, beneficiario_maximo_nivel_educativo=None), **XHR
    )
    assert invalido.status_code == 400
    assert invalido.json()["errors"] == {
        "beneficiario": {"maximo_nivel_educativo": ["Este campo es requerido."]}
    }
    html = client.post(URL, _datos(provincia, beneficiario_maximo_nivel_educativo=None))
    assert html.status_code == 200
    assert "beneficiario-form" in html.content.decode()
    assert not Beneficiario.objects.exists()


def test_existing_responsable_is_updated(client, provincia):
    existente = Responsable.objects.create(
        cuil=27301112224,
        dni=30111222,
        apellido="Resp",
        nombre="Ana",
        genero="F",
        fecha_nacimiento=date(1985, 1, 2),
        vinculo_parental="Padre/Madre",
        calle="Vieja",
    )

    client.post(URL, _datos(provincia, responsable_calle="Nueva"), **XHR)

    existente.refresh_from_db()
    assert existente.calle == "Nueva"
    assert Responsable.objects.count() == 1


def test_unexpected_error_answers_500(client, provincia, monkeypatch):
    def rompe(*_args):
        raise RuntimeError("boom")

    monkeypatch.setattr(f"{IMPL}.procesar_formularios", rompe)

    respuesta = client.post(URL, _datos(provincia), **XHR)

    assert (respuesta.status_code, respuesta.json()) == (
        500,
        {"status": "error", "message": "Error al guardar: boom"},
    )
