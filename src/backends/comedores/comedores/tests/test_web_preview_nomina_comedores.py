"""Local React preview entries of the comedor nómina (``comedores.web_preview_nomina``)."""

import types

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, override_settings

from admisiones.models.admisiones import Admision
from comedores.models import Comedor, Programas
from comedores.web_preview_nomina import nomina_preview_patterns
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
    module = types.ModuleType("comedores_nomina_preview_test_urls")
    module.urlpatterns = nomina_preview_patterns(tmp_path) + list(monolith_patterns)
    with override_settings(ROOT_URLCONF=module):
        yield


@pytest.fixture(name="lector")
def lector_fixture():
    usuario = get_user_model().objects.create_user("lector_preview_nomina")
    usuario.user_permissions.add(Permission.objects.get(codename="view_nomina"))
    client = Client()
    client.force_login(usuario)
    return client


@pytest.mark.usefixtures("preview")
def test_both_entries_get_the_frozen_index(lector):
    directo = Comedor.objects.create(
        nombre="Preview Directo",
        programa=Programas.objects.create(
            nombre="Programa directo", usa_admision_para_nomina=False
        ),
    )
    comedor = Comedor.objects.create(nombre="Preview Nomina")
    admision = Admision.objects.create(comedor=comedor)

    for url in (
        f"/comedores/{directo.pk}/nomina/",
        f"/comedores/{comedor.pk}/admision/{admision.pk}/nomina/",
    ):
        respuesta = lector.get(url)
        assert respuesta.status_code == 200
        assert '/comedores/react/assets/app-1.js"' in respuesta.content.decode()
        assert "no-store" in respuesta["Cache-Control"]
        assert "csrftoken" in respuesta.cookies
    assert lector.get("/comedores/react/assets/app-1.js").content == b"console.log(1);"


@pytest.mark.usefixtures("preview")
def test_native_guards_and_scope_decide_first(lector):
    comedor = Comedor.objects.create(
        nombre="Preview Nomina Guard",
        programa=Programas.objects.create(
            nombre="Programa directo guard", usa_admision_para_nomina=False
        ),
    )
    otro = Comedor.objects.create(nombre="Otro")
    ajena = Admision.objects.create(comedor=otro)
    sin_permiso = Client()
    sin_permiso.force_login(get_user_model().objects.create_user("sin_permiso_pnom"))

    assert Client().get(f"/comedores/{comedor.pk}/nomina/").status_code in (302, 403)
    assert sin_permiso.get(f"/comedores/{comedor.pk}/nomina/").status_code == 403
    assert lector.get("/comedores/999999/nomina/").status_code == 404
    assert (
        lector.get(f"/comedores/{comedor.pk}/admision/{ajena.pk}/nomina/").status_code
        == 404
    )


@pytest.mark.usefixtures("preview")
def test_actions_stay_native(lector):
    comedor = Comedor.objects.create(nombre="Preview Nomina Acciones")

    assert lector.get(f"/comedores/{comedor.pk}/nomina/crear/").status_code == 403


def test_build_without_index_is_refused(tmp_path):
    with pytest.raises(ValueError):
        nomina_preview_patterns(tmp_path)
