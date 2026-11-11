"""Local React preview entries of the PAS back office (``pas.web_preview_backoffice``)."""

import types

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, override_settings

from config.urls_all import urlpatterns as monolith_patterns
from core.models import Municipio, Provincia
from pas.models import PasEstado, PasPersona
from pas.web_preview_backoffice import backoffice_preview_patterns

INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)
PAGES = (
    "/pas/listar",
    "/pas/panel-control",
    "/pas/panel-control/{pk}",
    "/pas/{pk}",
    "/pas/formacion",
    "/pas/mesa-ayuda",
    "/pas/liquidacion",
)

pytestmark = pytest.mark.django_db


@pytest.fixture(name="build")
def build_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    (tmp_path / "assets" / "app-1.js").write_text("console.log(1);", encoding="utf-8")
    (tmp_path / "assets" / "notes.txt").write_text("not served", encoding="utf-8")
    return tmp_path


@pytest.fixture(name="preview")
def preview_fixture(build):
    module = types.ModuleType("pas_preview_test_urls")
    module.urlpatterns = backoffice_preview_patterns(build) + list(monolith_patterns)
    with override_settings(ROOT_URLCONF=module):
        yield


@pytest.fixture(name="gestor")
def gestor_fixture():
    client = Client()
    client.force_login(get_user_model().objects.create_superuser("super_pas_preview"))
    return client


@pytest.fixture(name="persona")
def persona_fixture():
    provincia = Provincia.objects.create(nombre="Provincia")
    return PasPersona.objects.create(
        id_persona=1,
        apellidos="Apellido",
        nombres="Nombre",
        dni=30000001,
        provincia=provincia,
        municipio=Municipio.objects.create(nombre="Municipio", provincia=provincia),
        estado=PasEstado.objects.get_or_create(nombre="Activo")[0],
    )


@pytest.mark.usefixtures("preview")
def test_every_page_gets_the_frozen_index(gestor, persona):
    for url in PAGES:
        respuesta = gestor.get(url.format(pk=persona.pk))
        assert respuesta.status_code == 200, url
        body = respuesta.content.decode()
        assert '/pas/react/assets/app-1.js"' in body
        assert "/v2/sisoc/assets/" not in body
        assert "no-store" in respuesta["Cache-Control"]
        assert "Cookie" in respuesta["Vary"]
        assert "csrftoken" in respuesta.cookies
    assert gestor.head(PAGES[0]).content == b""


@pytest.mark.usefixtures("preview")
def test_native_guards_still_decide_before_the_index(gestor, persona):
    client = Client()
    for url in PAGES:
        # The decorator runs before LoginRequiredMixin: anonymous is a 403.
        assert client.get(url.format(pk=persona.pk)).status_code == 403, url
    usuario = get_user_model().objects.create_user("sin_ver_pas")
    usuario.user_permissions.add(Permission.objects.get(codename="change_paspersona"))
    client.force_login(usuario)
    for url in PAGES:
        assert client.get(url.format(pk=persona.pk)).status_code == 403, url

    assert gestor.get("/pas/panel-control/999999").status_code == 404
    assert gestor.get("/pas/999999").status_code == 404


@pytest.mark.usefixtures("preview")
def test_empty_padron_panel_still_gets_the_index(gestor):
    assert gestor.get("/pas/panel-control").status_code == 200


@pytest.mark.usefixtures("preview")
def test_other_routes_stay_native(gestor, persona):
    assert gestor.get("/pas/formacion/personas").json()["html"] is not None
    respuesta = gestor.get(f"/pas/{persona.pk}/editar")
    assert "pas/persona_form.html" in [t.name for t in respuesta.templates]


@pytest.mark.usefixtures("preview")
def test_only_frozen_assets_are_served(client):
    asset = client.get("/pas/react/assets/app-1.js")

    assert asset.status_code == 200
    assert asset.content == b"console.log(1);"
    assert asset["Cache-Control"] == "public, max-age=31536000, immutable"
    assert asset["X-Content-Type-Options"] == "nosniff"
    assert client.get("/pas/react/assets/app-1.js?x=1").status_code == 404
    assert client.get("/pas/react/assets/notes.txt").status_code == 404
    assert client.post("/pas/react/assets/app-1.js").status_code == 405


def test_build_without_index_is_refused(tmp_path):
    with pytest.raises(ValueError):
        backoffice_preview_patterns(tmp_path)


def test_production_urlconf_keeps_the_native_pages(gestor, persona):
    respuesta = gestor.get(f"/pas/panel-control/{persona.pk}")

    assert respuesta.status_code == 200
    assert "pas/persona_detail.html" in [t.name for t in respuesta.templates]
