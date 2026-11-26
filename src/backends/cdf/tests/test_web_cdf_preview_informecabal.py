"""Local React preview entries of the CDF Informe Cabal screens (``centrodefamilia.web_preview_informecabal``)."""

import types

import pytest
from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.test import Client, override_settings

from centrodefamilia.models import CabalArchivo, Centro
from centrodefamilia.web_preview_informecabal import cdf_informecabal_preview_patterns
from config.urls_all import urlpatterns as monolith_patterns

INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)

pytestmark = pytest.mark.django_db


def _client(*, view=True):
    user = User.objects.create_user("preview_cabal")
    if view:
        user.user_permissions.add(
            Permission.objects.get(
                content_type=ContentType.objects.get_for_model(Centro),
                codename="view_centro",
            )
        )
    client = Client()
    client.force_login(user)
    return client, user


@pytest.fixture(name="datos")
def datos_fixture():
    usuario = User.objects.create_user("subio_cabal")
    archivo = CabalArchivo(nombre_original="a.xlsx", usuario=usuario)
    archivo.archivo.save("a.xlsx", ContentFile(b"x"), save=False)
    archivo.save()
    centro = Centro.objects.create(
        nombre="Centro Preview Cabal",
        tipo="faro",
        codigo="PREV-C",
        domicilio_actividad="Domicilio",
        telefono="1",
        celular="2",
        correo="c@example.com",
        nombre_referente="R",
        apellido_referente="E",
        telefono_referente="3",
        correo_referente="r@example.com",
    )
    return archivo, centro


@pytest.fixture(name="preview_urls")
def preview_urls_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    (tmp_path / "assets" / "app-1.js").write_text("console.log(1);", encoding="utf-8")
    module = types.ModuleType("cdf_informecabal_preview_test_urls")
    module.urlpatterns = cdf_informecabal_preview_patterns(tmp_path) + list(
        monolith_patterns
    )
    return module


def _get(client, urlconf, url, method="get"):
    with override_settings(ROOT_URLCONF=urlconf):
        return getattr(client, method)(url)


def _urls(datos):
    archivo, centro = datos
    return (
        "/centrodefamilia/informecabal/",
        f"/centrodefamilia/informecabal/{archivo.pk}/",
        f"/centrodefamilia/informecabal/registro/{archivo.pk}/",
        f"/centrodefamilia/centros/{centro.pk}/informecabal/{archivo.pk}/",
    )


def test_entries_serve_the_frozen_index_with_rewritten_assets(datos, preview_urls):
    client, _ = _client()
    for url in _urls(datos):
        respuesta = _get(client, preview_urls, url)
        head = _get(client, preview_urls, url, "head")

        assert respuesta.status_code == 200, url
        assert '/centrodefamilia/react/assets/app-1.js"' in respuesta.content.decode()
        assert "no-store" in respuesta["Cache-Control"]
        assert head.content == b""
    assert "csrftoken" in _get(client, preview_urls, _urls(datos)[0]).cookies


def test_native_guards_and_object_rule_decide_exactly_as_the_native_pages(
    datos, preview_urls
):
    archivo, centro = datos
    urls = _urls(datos)

    anonimo_nativo = Client().get(urls[0]).status_code
    for url in urls:
        assert _get(Client(), preview_urls, url).status_code == anonimo_nativo, url
    sin_permiso, usuario = _client(view=False)
    for url in urls:
        assert _get(sin_permiso, preview_urls, url).status_code == 403, url
    usuario.delete()
    cliente, _ = _client()
    assert (
        _get(cliente, preview_urls, "/centrodefamilia/informecabal/999999/").status_code
        == 404
    )
    assert (
        _get(
            cliente, preview_urls, "/centrodefamilia/informecabal/registro/999999/"
        ).status_code
        == 404
    )
    assert _get(cliente, preview_urls, f"{urls[2]}?registro=999999").status_code == 404
    assert (
        _get(
            cliente,
            preview_urls,
            f"/centrodefamilia/centros/999999/informecabal/{archivo.pk}/",
        ).status_code
        == 404
    )
    assert (
        _get(
            cliente,
            preview_urls,
            f"/centrodefamilia/centros/{centro.pk}/informecabal/999999/",
        ).status_code
        == 404
    )


def test_assets_are_frozen_and_the_native_ajax_endpoints_stay_native(preview_urls):
    client, _ = _client()

    assert (
        _get(client, preview_urls, "/centrodefamilia/react/assets/app-1.js").status_code
        == 200
    )
    assert (
        _get(client, preview_urls, "/centrodefamilia/react/assets/x.js").status_code
        == 404
    )
    # preview/process are POST-only native views: a GET is still a 405, not the index.
    for ajax in ("preview", "process"):
        assert (
            _get(
                client, preview_urls, f"/centrodefamilia/informecabal/{ajax}/"
            ).status_code
            == 405
        )
