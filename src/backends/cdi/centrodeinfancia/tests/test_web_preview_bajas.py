"""React entries of the CDI soft-delete confirmations (``centrodeinfancia.web_preview_bajas``).

GET returns the frozen index only after the native URL permission and the
native scoped lookup; POST still reaches the native delete view; without the
entries (React off) the native confirmation template answers.
"""

import types

import pytest
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.test import Client, override_settings

from centrodeinfancia.models import AccesoCDI, CentroDeInfancia, NominaCentroInfancia
from centrodeinfancia.web_preview import cdi_preview_patterns
from centrodeinfancia.web_preview_bajas import cdi_bajas_preview_patterns
from ciudadanos.models import Ciudadano
from config.urls_all import urlpatterns as monolith_patterns
from core.models import Sexo

INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)
ASSET = "/centrodeinfancia/react/assets/app-1.js"
BAJA_CENTRO = "delete_centrodeinfancia"
BAJA_NOMINA = "delete_nominacentroinfancia"

pytestmark = pytest.mark.django_db


@pytest.fixture(name="build")
def build_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    (tmp_path / "assets" / "app-1.js").write_text("console.log(1);", encoding="utf-8")
    return tmp_path


@pytest.fixture(name="preview")
def preview_fixture(build):
    module = types.ModuleType("cdi_bajas_preview_test_urls")
    module.urlpatterns = (
        cdi_bajas_preview_patterns(build)
        + cdi_preview_patterns(build)
        + list(monolith_patterns)
    )
    with override_settings(ROOT_URLCONF=module):
        yield


def _usuario(username, *codenames):
    user = User.objects.create_user(username)
    for codename in codenames:
        permiso = Permission.objects.filter(
            content_type__app_label="centrodeinfancia", codename=codename
        ).first() or Permission.objects.create(
            content_type=ContentType.objects.get_for_model(Group),
            codename=codename,
            name=codename,
        )
        user.user_permissions.add(permiso)
    return user


def _cliente(user):
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture(name="datos")
def datos_fixture():
    centro = CentroDeInfancia.objects.create(nombre="CDI Preview")
    ajeno = CentroDeInfancia.objects.create(nombre="CDI Ajeno")
    ciudadano = Ciudadano.objects.create(
        apellido="Paz",
        nombre="Ana",
        documento=30111222,
        sexo=Sexo.objects.get_or_create(sexo="Femenino")[0],
    )
    nomina = NominaCentroInfancia.objects.create(centro=centro, ciudadano=ciudadano)
    return centro, ajeno, nomina


def _centro_url(pk):
    return f"/centrodeinfancia/eliminar/{pk}"


def _nomina_url(pk, pk2):
    return f"/centrodeinfancia/{pk}/nomina/{pk2}/eliminar/"


def _vivos():
    return (
        set(CentroDeInfancia.objects.values_list("pk", flat=True)),
        set(NominaCentroInfancia.objects.values_list("pk", flat=True)),
    )


@pytest.mark.usefixtures("preview")
def test_entries_return_the_frozen_index_for_authorized_scoped_objects(datos):
    centro, _, nomina = datos
    client = _cliente(_usuario("prev-baja", BAJA_CENTRO, BAJA_NOMINA))

    for url in (_centro_url(centro.pk), _nomina_url(centro.pk, nomina.pk)):
        respuesta = client.get(url)
        assert respuesta.status_code == 200
        assert ASSET in respuesta.content.decode()
        assert "no-store" in respuesta["Cache-Control"]
        assert "csrftoken" in respuesta.cookies
    assert client.head(_centro_url(centro.pk)).content == b""


@pytest.mark.usefixtures("preview")
def test_entries_keep_the_native_guards_and_leak_nothing(datos):
    centro, ajeno, nomina = datos
    urls = (_centro_url(centro.pk), _nomina_url(centro.pk, nomina.pk))
    for url in urls:
        anonimo = Client().get(url)
        with override_settings(ROOT_URLCONF="config.urls_all"):
            esperado = Client().get(url)
        assert anonimo.status_code == esperado.status_code
        assert anonimo.get("Location") == esperado.get("Location")
        sin_permiso = _cliente(_usuario(f"prev-baja-sin-{url.count('/')}"))
        negado = sin_permiso.get(url)
        assert negado.status_code == 403
        assert ASSET not in negado.content.decode()

    referente = _usuario("prev-baja-ref", BAJA_CENTRO, BAJA_NOMINA)
    AccesoCDI.objects.create(user=referente, centro=ajeno)
    fuera = _cliente(referente)
    for url in urls:
        negado = fuera.get(url)
        assert negado.status_code == 404
        assert ASSET not in negado.content.decode()
    otro = _cliente(_usuario("prev-baja-cruzada", BAJA_NOMINA))
    assert otro.get(_nomina_url(ajeno.pk, nomina.pk)).status_code == 404


@pytest.mark.usefixtures("preview")
def test_post_still_reaches_the_native_soft_delete(datos):
    centro, _, nomina = datos
    client = _cliente(_usuario("prev-baja-post", BAJA_CENTRO, BAJA_NOMINA))

    respuesta = client.post(_nomina_url(centro.pk, nomina.pk))

    assert respuesta.status_code == 302
    assert respuesta["Location"] == f"/centrodeinfancia/{centro.pk}/nomina/"
    assert not NominaCentroInfancia.objects.filter(pk=nomina.pk).exists()
    respuesta = client.post(_centro_url(centro.pk))
    assert respuesta.status_code == 302
    assert respuesta["Location"] == "/centrodeinfancia/listar"
    assert not CentroDeInfancia.objects.filter(pk=centro.pk).exists()


@pytest.mark.usefixtures("preview")
def test_post_without_permission_is_denied_as_native_without_effects(datos):
    centro, _, nomina = datos
    antes = _vivos()
    client = _cliente(_usuario("prev-baja-post-sin"))

    assert client.post(_centro_url(centro.pk)).status_code == 403
    assert client.post(_nomina_url(centro.pk, nomina.pk)).status_code == 403
    assert _vivos() == antes


def test_production_urlconf_keeps_the_native_confirmations(datos):
    centro, _, nomina = datos
    client = _cliente(_usuario("prev-baja-nativo", BAJA_CENTRO, BAJA_NOMINA))

    centro_page = client.get(_centro_url(centro.pk))
    nomina_page = client.get(_nomina_url(centro.pk, nomina.pk))

    assert "centrodeinfancia/centrodeinfancia_confirm_delete.html" in [
        t.name for t in centro_page.templates
    ]
    assert "centrodeinfancia/nomina_confirm_delete.html" in [
        t.name for t in nomina_page.templates
    ]


def test_build_without_index_is_refused(tmp_path):
    with pytest.raises(ValueError):
        cdi_bajas_preview_patterns(tmp_path)
