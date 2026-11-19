"""Local React preview entries of the template manager (``admisiones.web_preview_templates``)."""

import types

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, override_settings

from admisiones.models.admisiones import (
    IncidenciaTemplateInformeTecnico,
    PlantillaInformeTecnico,
    TipoConvenio,
)
from admisiones.web_preview_templates import templates_preview_patterns
from config.urls_all import urlpatterns as monolith_patterns

INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)
BASE = "/comedores/configuracion/templates/"
PAGINAS = (
    BASE,
    f"{BASE}{{plantilla}}/",
    f"{BASE}variables/",
    f"{BASE}incidencias/",
    f"{BASE}incidencias/{{incidencia}}/",
)

pytestmark = pytest.mark.django_db


@pytest.fixture(name="build")
def build_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    (tmp_path / "assets" / "app-1.js").write_text("console.log(1);", encoding="utf-8")
    return tmp_path


@pytest.fixture(name="preview")
def preview_fixture(build):
    module = types.ModuleType("gestor_templates_preview_test_urls")
    module.urlpatterns = templates_preview_patterns(build) + list(monolith_patterns)
    with override_settings(ROOT_URLCONF=module):
        yield


@pytest.fixture(name="gestor")
def gestor_fixture():
    usuario = get_user_model().objects.create_user("gestor_preview_templates")
    usuario.user_permissions.add(
        Permission.objects.get(codename="gestionar_templates_informe_tecnico")
    )
    client = Client()
    client.force_login(usuario)
    return client


@pytest.fixture(name="objetos")
def objetos_fixture():
    plantilla = PlantillaInformeTecnico.objects.create(
        nombre="Plantilla",
        tipo_admision="renovacion",
        tipo_convenio=TipoConvenio.objects.create(nombre="Organización Base"),
        tipo_renovacion="primera",
        estado_financiamiento="finalizado",
    )
    incidencia = IncidenciaTemplateInformeTecnico.objects.create(
        clave_condiciones="clave", condiciones={}
    )
    return {"plantilla": plantilla.pk, "incidencia": incidencia.pk}


@pytest.mark.usefixtures("preview")
def test_every_query_page_gets_the_frozen_index(gestor, objetos):
    for url in PAGINAS:
        respuesta = gestor.get(url.format(**objetos))
        assert respuesta.status_code == 200, url
        body = respuesta.content.decode()
        assert '/comedores/react/assets/app-1.js"' in body
        assert "/v2/sisoc/assets/" not in body
        assert "no-store" in respuesta["Cache-Control"]
        assert "Cookie" in respuesta["Vary"]
        assert "csrftoken" in respuesta.cookies
    assert gestor.get("/comedores/react/assets/app-1.js").content == b"console.log(1);"


@pytest.mark.usefixtures("preview")
def test_native_guards_and_lookups_still_decide_before_the_index(gestor, objetos):
    anonimo = Client()
    sin_permiso = Client()
    sin_permiso.force_login(get_user_model().objects.create_user("sin_permiso"))
    for url in PAGINAS:
        assert anonimo.get(url.format(**objetos)).status_code == 403, url
        assert sin_permiso.get(url.format(**objetos)).status_code == 403, url

    for url in (BASE, f"{BASE}incidencias/"):
        assert gestor.get(url, {"page": "9"}).status_code == 404, url
    for url in (f"{BASE}999999/", f"{BASE}incidencias/999999/"):
        assert gestor.get(url).status_code == 404, url


@pytest.mark.usefixtures("preview")
def test_the_incident_post_and_the_other_routes_stay_native(gestor, objetos):
    respuesta = gestor.post(
        f"{BASE}incidencias/{objetos['incidencia']}/",
        {"estado": "en_analisis", "plantilla": "", "observaciones": "Revisando"},
    )
    assert respuesta.status_code == 302
    incidencia = IncidenciaTemplateInformeTecnico.objects.get()
    assert (incidencia.estado, incidencia.observaciones) == ("en_analisis", "Revisando")

    version = PlantillaInformeTecnico.objects.get().versiones.create(numero=1)
    editor = gestor.post(
        f"{BASE}{objetos['plantilla']}/versiones/{version.pk}/editar/",
        {"contenido_html": "<p>Nuevo</p>", "observaciones": ""},
    )
    assert editor.status_code == 302
    version.refresh_from_db()
    assert version.contenido_html == "<p>Nuevo</p>"
    previa = gestor.get(
        f"{BASE}{objetos['plantilla']}/versiones/{version.pk}/previsualizar/"
    )
    assert previa.status_code == 302
    assert previa["Location"] == (
        f"{BASE}{objetos['plantilla']}/versiones/{version.pk}/editar/"
    )


@pytest.mark.usefixtures("preview")
def test_create_form_gets_the_frozen_index_and_keeps_the_native_post(gestor, objetos):
    anonimo = Client()
    sin_permiso = Client()
    sin_permiso.force_login(get_user_model().objects.create_user("sin_permiso_crear"))

    respuesta = gestor.get(f"{BASE}crear/")

    assert respuesta.status_code == 200
    assert '/comedores/react/assets/app-1.js"' in respuesta.content.decode()
    assert "csrftoken" in respuesta.cookies
    assert anonimo.get(f"{BASE}crear/").status_code == 403
    assert sin_permiso.get(f"{BASE}crear/").status_code == 403
    invalido = gestor.post(f"{BASE}crear/", {"nombre": ""})
    assert "admisiones/templates_informes_tecnicos/form.html" in [
        t.name for t in invalido.templates
    ]


@pytest.mark.usefixtures("preview")
def test_version_editor_gets_the_frozen_index_only_for_a_draft_of_that_template(
    gestor, objetos
):
    version = PlantillaInformeTecnico.objects.get().versiones.create(numero=1)
    url = f"{BASE}{objetos['plantilla']}/versiones/{version.pk}/editar/"
    anonimo = Client()
    sin_permiso = Client()
    sin_permiso.force_login(get_user_model().objects.create_user("sin_permiso_editor"))

    respuesta = gestor.get(url)

    assert respuesta.status_code == 200
    assert '/comedores/react/assets/app-1.js"' in respuesta.content.decode()
    assert "csrftoken" in respuesta.cookies
    assert anonimo.get(url).status_code == 403
    assert sin_permiso.get(url).status_code == 403
    assert gestor.get(f"{BASE}{objetos['plantilla']}/versiones/999999/editar/").status_code == 404
    version.estado = "publicada"
    version.save()
    assert gestor.get(url).status_code == 404


def test_build_without_index_is_refused(tmp_path):
    with pytest.raises(ValueError):
        templates_preview_patterns(tmp_path)


def test_production_urlconf_keeps_the_native_pages(gestor):
    respuesta = gestor.get(BASE)

    assert respuesta.status_code == 200
    assert "admisiones/templates_informes_tecnicos/list.html" in [
        t.name for t in respuesta.templates
    ]
