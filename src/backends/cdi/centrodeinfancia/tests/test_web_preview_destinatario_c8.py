"""Local React preview entries of the CDI destinatario screens (``web_preview_destinatario``)."""

import types

import pytest
from django.contrib.auth.models import Permission, User
from django.test import Client, override_settings
from django.urls import reverse

from centrodeinfancia.models import CentroDeInfancia, NominaCentroInfancia
from centrodeinfancia.web_preview_destinatario import destinatario_preview_patterns
from ciudadanos.models import Ciudadano
from config.urls_all import urlpatterns as monolith_patterns

INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)

pytestmark = pytest.mark.django_db


@pytest.fixture(name="preview")
def preview_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    (tmp_path / "assets" / "app-1.js").write_text("console.log(1);", encoding="utf-8")
    module = types.ModuleType("cdi_preview_destinatario_test_urls")
    module.urlpatterns = destinatario_preview_patterns(tmp_path) + list(
        monolith_patterns
    )
    with override_settings(ROOT_URLCONF=module):
        yield


def _cliente(user):
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture(name="centro")
def centro_fixture():
    return CentroDeInfancia.objects.create(nombre="CDI Vista previa")


def _nomina(centro):
    ciudadano = Ciudadano.objects.create(
        apellido="Ramirez", nombre="Sofia", documento=44555666
    )
    return NominaCentroInfancia.objects.create(
        centro=centro,
        ciudadano=ciudadano,
        dni=ciudadano.documento,
        apellido="Ramirez",
        nombre="Sofia",
    )


@pytest.mark.usefixtures("preview")
def test_entries_serve_the_index_after_the_native_guards(centro):
    admin = User.objects.create_superuser("c8-preview-admin", "", "test1234")
    nomina = _nomina(centro)

    for url in (
        reverse("centrodeinfancia_nomina_crear", args=[centro.pk]),
        reverse("centrodeinfancia_nomina_editar", args=[centro.pk, nomina.pk]),
    ):
        respuesta = _cliente(admin).get(url)
        assert respuesta.status_code == 200
        assert b"/centrodeinfancia/react/assets/app-1.js" in respuesta.content
        assert respuesta["Cache-Control"] == "private, no-store"


@pytest.mark.usefixtures("preview")
def test_entries_keep_the_native_rejections(centro):
    nomina = _nomina(centro)
    urls = (
        reverse("centrodeinfancia_nomina_crear", args=[centro.pk]),
        reverse("centrodeinfancia_nomina_editar", args=[centro.pk, nomina.pk]),
    )
    solo_alta = User.objects.create_user("c8-preview-alta")
    solo_alta.user_permissions.add(
        Permission.objects.get(codename="add_nominacentroinfancia")
    )

    assert _cliente(solo_alta).get(urls[0]).status_code == 200
    assert _cliente(solo_alta).get(urls[1]).status_code == 403
    assert Client().get(urls[0]).status_code in (302, 401, 403)


@pytest.mark.usefixtures("preview")
def test_unknown_centre_and_ficha_are_404(centro):
    admin = User.objects.create_superuser("c8-preview-admin2", "", "test1234")

    assert (
        _cliente(admin)
        .get(reverse("centrodeinfancia_nomina_crear", args=[987654]))
        .status_code
        == 404
    )
    assert (
        _cliente(admin)
        .get(reverse("centrodeinfancia_nomina_editar", args=[centro.pk, 987654]))
        .status_code
        == 404
    )
