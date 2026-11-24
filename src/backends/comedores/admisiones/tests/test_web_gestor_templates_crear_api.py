"""Web API (G1 v1) of the template create form (AD01.02): ``.../plantillas-informe/crear/``."""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client

from admisiones.models.admisiones import (
    PlantillaInformeTecnico,
    PlantillaInformeTecnicoVersion,
    TipoConvenio,
)
from core import web_gate

ROOT = "/api/web/comedores/admisiones/plantillas-informe/"
CREAR = f"{ROOT}crear/"
NATIVO = "/comedores/configuracion/templates/crear/"
CODE = "gestionar_templates_informe_tecnico"

pytestmark = pytest.mark.django_db


def _ready(user):
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    return user


@pytest.fixture(name="gestor")
def gestor_fixture():
    usuario = _ready(get_user_model().objects.create_user("gestor_templates_crear"))
    usuario.user_permissions.add(
        Permission.objects.get(content_type__app_label="admisiones", codename=CODE)
    )
    return usuario


@pytest.fixture(name="web")
def web_fixture(gestor):
    client = Client()
    client.force_login(gestor)
    return client


@pytest.fixture(name="convenio")
def convenio_fixture():
    return TipoConvenio.objects.create(nombre="Organización Base")


def _datos(convenio, **extra):
    return {
        "nombre": "Incorporación nueva",
        "descripcion": "Para incorporaciones",
        "tipo_admision": "incorporacion",
        "tipo_convenio": str(convenio.pk),
        "es_ex_pnud": "si",
        "estado_convenio_pnud": "vigente",
        **extra,
    }


def test_get_projects_the_native_form(web, convenio):
    respuesta = web.get(CREAR)

    assert respuesta.status_code == 200
    assert respuesta["Cache-Control"] == "private, no-store"
    data = respuesta.json()
    campos = {campo["name"]: campo for campo in data["fields"]}
    assert list(campos) == [
        "nombre",
        "descripcion",
        "tipo_admision",
        "tipo_convenio",
        "es_ex_pnud",
        "estado_convenio_pnud",
        "tipo_renovacion",
        "estado_financiamiento",
        "informe_complementario_modifica_prestaciones",
    ]
    assert campos["nombre"]["required"] is True
    assert campos["nombre"]["max_length"] == 255
    assert campos["es_ex_pnud"]["required"] is False
    assert campos["tipo_convenio"]["choices"] == [
        {"value": "", "label": "Seleccione un tipo de convenio"},
        {"value": str(convenio.pk), "label": "Asociación de hecho"},
    ]
    assert data["errors"] == {}
    assert data["non_field_errors"] == []
    assert data["urls"]["cancelar"] == "/comedores/configuracion/templates/"
    assert data["messages"] == []


def test_post_creates_the_template_and_the_next_page_shows_the_message(web, convenio):
    respuesta = web.post(CREAR, _datos(convenio))

    plantilla = PlantillaInformeTecnico.objects.get()
    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "ok": True,
        "redirect": f"/comedores/configuracion/templates/{plantilla.pk}/",
    }
    assert (plantilla.estado, plantilla.es_ex_pnud, plantilla.estado_convenio_pnud) == (
        "activa",
        "si",
        "vigente",
    )
    version = PlantillaInformeTecnicoVersion.objects.get()
    assert (version.plantilla_id, version.numero, version.estado) == (
        plantilla.pk,
        1,
        "borrador",
    )
    detalle = web.get(f"{ROOT}{plantilla.pk}/").json()
    assert detalle["messages"] == [
        {
            "message": f"Template {plantilla.codigo} creado con su versión 1 en preparación.",
            "level": "success",
        }
    ]


def test_post_matches_the_native_view_for_a_renewal(web, convenio):
    datos = {
        "nombre": "Renovación",
        "tipo_admision": "renovacion",
        "tipo_convenio": str(convenio.pk),
        "es_ex_pnud": "si",
        "estado_convenio_pnud": "vigente",
        "tipo_renovacion": "primera",
        "estado_financiamiento": "finalizado",
        "informe_complementario_modifica_prestaciones": "no",
    }

    assert web.post(CREAR, datos).status_code == 200

    plantilla = PlantillaInformeTecnico.objects.get()
    assert plantilla.es_ex_pnud is None
    assert plantilla.estado_convenio_pnud is None
    assert plantilla.tipo_renovacion == "primera"


def test_invalid_post_returns_the_native_errors_and_persists_nothing(web, convenio):
    nativo = Client()
    nativo.force_login(get_user_model().objects.get(username="gestor_templates_crear"))
    datos = _datos(convenio, nombre="", es_ex_pnud="", estado_convenio_pnud="")

    respuesta = web.post(CREAR, datos)

    assert respuesta.status_code == 400
    data = respuesta.json()
    assert data["errors"]["nombre"] == ["Este campo es requerido."]
    assert data["errors"]["es_ex_pnud"] == ["Debe indicar si la admisión es Ex PNUD."]
    campos = {campo["name"]: campo for campo in data["fields"]}
    assert campos["descripcion"]["value"] == "Para incorporaciones"
    assert campos["tipo_convenio"]["value"] == str(convenio.pk)
    pagina = nativo.post(NATIVO, datos)
    assert pagina.status_code == 200
    assert {
        nombre: [str(error) for error in errores]
        for nombre, errores in pagina.context["form"].errors.items()
    } == data["errors"]
    assert not PlantillaInformeTecnico.objects.exists()


def test_pnud_state_is_required_when_ex_pnud(web, convenio):
    respuesta = web.post(CREAR, _datos(convenio, estado_convenio_pnud=""))

    assert respuesta.status_code == 400
    assert respuesta.json()["errors"] == {
        "estado_convenio_pnud": ["Debe indicar el estado del convenio PNUD."]
    }


def test_an_unsupported_body_is_415(web, convenio):
    respuesta = web.post(CREAR, {"nombre": "x"}, content_type="application/json")

    assert respuesta.status_code == 415
    assert not PlantillaInformeTecnico.objects.exists()


def test_anonymous_is_401_and_without_permission_403(client, convenio):
    assert client.get(CREAR).status_code == 401
    assert client.get(CREAR).json() == {"detail": web_gate.DETAIL_UNAUTHENTICATED}
    assert client.post(CREAR, _datos(convenio)).status_code == 401

    client.force_login(
        _ready(get_user_model().objects.create_user("sin_permiso_templates_crear"))
    )
    assert client.get(CREAR).status_code == 403
    assert client.post(CREAR, _datos(convenio)).status_code == 403
    assert not PlantillaInformeTecnico.objects.exists()


def test_post_without_the_csrf_token_is_403(gestor, convenio):
    client = Client(enforce_csrf_checks=True)
    client.force_login(gestor)

    assert client.post(CREAR, _datos(convenio)).status_code == 403
    assert not PlantillaInformeTecnico.objects.exists()


def test_put_and_delete_are_405(web):
    for metodo in ("put", "delete"):
        assert getattr(web, metodo)(CREAR).status_code == 405
