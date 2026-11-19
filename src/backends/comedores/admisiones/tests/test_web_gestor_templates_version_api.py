"""Web API (G1 v1) of the template version editor (AD01.02): ``.../<pk>/versiones/<version_pk>/``."""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client

from admisiones.models.admisiones import (
    TipoConvenio,
    VariableTemplateInformeTecnico,
)
from admisiones.services.templates_informe_tecnico_service import (
    PlantillaInformeTecnicoService,
)
from core import web_gate

ROOT = "/api/web/comedores/admisiones/plantillas-informe/"
NATIVO = "/comedores/configuracion/templates/"
CODE = "gestionar_templates_informe_tecnico"
SUCIO = '<p style="color: red; position: fixed">Hola {{ informe.expediente }}</p><script>alert(1)</script>'
LIMPIO = '<p style="color: red">Hola {{ informe.expediente }}</p>'

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
    usuario = _ready(get_user_model().objects.create_user("gestor_templates_version"))
    usuario.user_permissions.add(
        Permission.objects.get(content_type__app_label="admisiones", codename=CODE)
    )
    return usuario


@pytest.fixture(name="web")
def web_fixture(gestor):
    client = Client()
    client.force_login(gestor)
    return client


@pytest.fixture(name="borrador")
def borrador_fixture():
    convenio = TipoConvenio.objects.create(nombre="Organización Base")
    plantilla, version = PlantillaInformeTecnicoService.crear_plantilla(
        {
            "nombre": "Incorporación",
            "descripcion": "",
            "tipo_admision": "incorporacion",
            "tipo_convenio": convenio,
            "es_ex_pnud": "no",
            "estado_convenio_pnud": None,
            "tipo_renovacion": None,
            "estado_financiamiento": None,
        },
        None,
    )
    version.observaciones = "Primera revisión"
    version.contenido_html = "<p>Inicial</p>"
    version.save()
    return plantilla, version


def _url(plantilla, version):
    return f"{ROOT}{plantilla.pk}/versiones/{version.pk}/"


def _variable(codigo, categoria, nombre, orden, activo=True):
    return VariableTemplateInformeTecnico.objects.get_or_create(
        codigo=codigo,
        defaults={
            "categoria": categoria,
            "nombre": nombre,
            "orden": orden,
            "activo": activo,
        },
    )[0]


def test_get_projects_the_native_editor(web, borrador):
    plantilla, version = borrador
    _variable("informe.fecha", "Informe", "Fecha", 2)
    _variable("informe.expediente", "Informe", "Expediente", 1)
    _variable("comedor.nombre", "Comedor", "Nombre del comedor", 1)
    _variable("oculta.codigo", "Informe", "Inactiva", 3, activo=False)

    respuesta = web.get(_url(plantilla, version))

    assert respuesta.status_code == 200
    assert respuesta["Cache-Control"] == "private, no-store"
    data = respuesta.json()
    assert data["version"] == {"id": version.pk, "numero": 1}
    assert data["plantilla"] == {
        "id": plantilla.pk,
        "codigo": plantilla.codigo,
        "nombre": "Incorporación",
    }
    assert data["contenido_html"]["label"] == "Contenido del template"
    assert data["contenido_html"]["value"] == "<p>Inicial</p>"
    assert data["contenido_html"]["placeholder"] == (
        "Escribí el contenido HTML o insertá una variable desde el catálogo."
    )
    assert data["observaciones"]["label"] == "Observaciones de la versión"
    assert data["observaciones"]["value"] == "Primera revisión"
    assert [(v["categoria"], v["codigo"], v["token"]) for v in data["variables"]] == [
        ("Comedor", "comedor.nombre", "{{ comedor.nombre }}"),
        ("Informe", "informe.expediente", "{{ informe.expediente }}"),
        ("Informe", "informe.fecha", "{{ informe.fecha }}"),
    ]
    assert data["urls"]["detalle"] == f"{NATIVO}{plantilla.pk}/"
    assert data["urls"]["previsualizar"] == (
        f"{NATIVO}{plantilla.pk}/versiones/{version.pk}/previsualizar/"
    )


def test_only_a_draft_of_that_template_is_editable(web, borrador, gestor):
    plantilla, version = borrador
    otra = PlantillaInformeTecnicoService.crear_plantilla(
        {
            "nombre": "Otra",
            "descripcion": "",
            "tipo_admision": "renovacion",
            "tipo_convenio": plantilla.tipo_convenio,
            "es_ex_pnud": None,
            "estado_convenio_pnud": None,
            "tipo_renovacion": "primera",
            "estado_financiamiento": "finalizado",
            "informe_complementario_modifica_prestaciones": "no",
        },
        None,
    )
    version.contenido_html = "<p>Listo</p>"
    version.save()
    assert PlantillaInformeTecnicoService.publicar_version(version, gestor)[0]

    assert web.get(_url(plantilla, version)).status_code == 404
    assert (
        web.post(_url(plantilla, version), {"contenido_html": "<p>X</p>"}).status_code
        == 404
    )
    version.refresh_from_db()
    assert version.contenido_html == "<p>Listo</p>"
    assert web.get(f"{ROOT}{plantilla.pk}/versiones/{otra[1].pk}/").status_code == 404
    assert web.get(f"{ROOT}{plantilla.pk}/versiones/999999999/").status_code == 404


def test_post_saves_the_sanitised_content_and_the_next_page_shows_the_message(
    web, borrador, gestor
):
    plantilla, version = borrador

    respuesta = web.post(
        _url(plantilla, version),
        {"contenido_html": SUCIO, "observaciones": "Revisada"},
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {"ok": True, "redirect": f"{NATIVO}{plantilla.pk}/"}
    version.refresh_from_db()
    plantilla.refresh_from_db()
    assert (version.contenido_html, version.observaciones) == (LIMPIO, "Revisada")
    assert plantilla.modificado_por == gestor
    assert web.get(f"{ROOT}{plantilla.pk}/").json()["messages"] == [
        {
            "message": "Versión en preparación guardada correctamente.",
            "level": "success",
        }
    ]


def test_post_saves_exactly_what_the_native_view_saves(web, borrador, gestor):
    plantilla, version = borrador
    nativo = Client()
    nativo.force_login(gestor)
    datos = {"contenido_html": SUCIO, "observaciones": "Igual"}

    respuesta = nativo.post(
        f"{NATIVO}{plantilla.pk}/versiones/{version.pk}/editar/", datos
    )
    assert respuesta.status_code == 302
    version.refresh_from_db()
    esperado = (version.contenido_html, version.observaciones)
    version.contenido_html = ""
    version.observaciones = ""
    version.save()

    assert web.post(_url(plantilla, version), datos).status_code == 200
    version.refresh_from_db()
    assert (version.contenido_html, version.observaciones) == esperado


def test_a_refused_save_is_400_with_the_bound_form(web, borrador, monkeypatch):
    plantilla, version = borrador
    monkeypatch.setattr(
        PlantillaInformeTecnicoService,
        "guardar_borrador",
        staticmethod(
            lambda *args: (False, "Solo se pueden editar versiones en borrador.")
        ),
    )

    respuesta = web.post(
        _url(plantilla, version),
        {"contenido_html": "<p>Nuevo</p>", "observaciones": "Nota"},
    )

    assert respuesta.status_code == 400
    data = respuesta.json()
    assert data["non_field_errors"] == ["Solo se pueden editar versiones en borrador."]
    assert data["contenido_html"]["value"] == "<p>Nuevo</p>"
    assert data["observaciones"]["value"] == "Nota"
    version.refresh_from_db()
    assert version.contenido_html == "<p>Inicial</p>"


def test_an_unsupported_body_is_415(web, borrador):
    plantilla, version = borrador

    respuesta = web.post(
        _url(plantilla, version),
        {"contenido_html": "x"},
        content_type="application/json",
    )

    assert respuesta.status_code == 415
    version.refresh_from_db()
    assert version.contenido_html == "<p>Inicial</p>"


def test_anonymous_without_permission_and_without_csrf(client, borrador, gestor):
    plantilla, version = borrador
    url = _url(plantilla, version)
    assert client.get(url).status_code == 401
    assert client.get(url).json() == {"detail": web_gate.DETAIL_UNAUTHENTICATED}
    assert client.post(url, {"contenido_html": "x"}).status_code == 401

    client.force_login(
        _ready(get_user_model().objects.create_user("sin_permiso_templates_version"))
    )
    assert client.get(url).status_code == 403
    assert client.post(url, {"contenido_html": "x"}).status_code == 403

    sin_csrf = Client(enforce_csrf_checks=True)
    sin_csrf.force_login(gestor)
    assert sin_csrf.post(url, {"contenido_html": "x"}).status_code == 403
    version.refresh_from_db()
    assert version.contenido_html == "<p>Inicial</p>"


def test_put_and_delete_are_405(web, borrador):
    plantilla, version = borrador
    for metodo in ("put", "delete"):
        assert getattr(web, metodo)(_url(plantilla, version)).status_code == 405
