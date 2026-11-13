"""Local React preview entries of the comedor collaborators (``comedores.web_preview_colaboradores``)."""

import types
from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, override_settings

from ciudadanos.models import Ciudadano, Sexo
from comedores.models import ColaboradorEspacio, Comedor, Programas
from comedores.web_preview_colaboradores import colaboradores_preview_patterns
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
    module = types.ModuleType("colaboradores_preview_test_urls")
    module.urlpatterns = colaboradores_preview_patterns(tmp_path) + list(
        monolith_patterns
    )
    with override_settings(ROOT_URLCONF=module):
        yield


def _cliente(nombre, *codes, **extra):
    usuario = get_user_model().objects.create_user(nombre, **extra)
    for code in codes:
        app, codename = code.split(".")
        usuario.user_permissions.add(
            Permission.objects.get(content_type__app_label=app, codename=codename)
        )
    client = Client()
    client.force_login(usuario)
    return client


@pytest.fixture(name="datos")
def datos_fixture():
    comedor = Comedor.objects.create(nombre="Comedor preview")
    sexo, _ = Sexo.objects.get_or_create(sexo="Femenino")
    persona = Ciudadano.objects.create(
        nombre="Ana",
        apellido="Gómez",
        documento="30999111",
        sexo=sexo,
        fecha_nacimiento=date(2000, 1, 1),
    )
    colaborador = ColaboradorEspacio.objects.create(
        comedor=comedor, ciudadano=persona, fecha_alta=date(2026, 9, 1)
    )
    return comedor, colaborador


def _entradas(comedor, colaborador):
    return {
        f"/comedores/{comedor.pk}/colaboradores/crear/": (
            "comedores.add_colaboradorespacio"
        ),
        f"/comedores/{comedor.pk}/colaboradores/{colaborador.pk}/editar/": (
            "comedores.change_colaboradorespacio"
        ),
    }


@pytest.mark.usefixtures("preview")
def test_every_entry_serves_the_frozen_index_with_its_native_permission(datos):
    for indice, (url, permiso) in enumerate(_entradas(*datos).items()):
        respuesta = _cliente(f"u{indice}_col_k6", permiso, is_superuser=True).get(url)
        assert respuesta.status_code == 200, url
        assert '/comedores/react/assets/app-1.js"' in respuesta.content.decode()
        assert "no-store" in respuesta["Cache-Control"]
        assert "csrftoken" in respuesta.cookies
    asset = Client().get("/comedores/react/assets/app-1.js")
    assert asset.content == b"console.log(1);"


@pytest.mark.usefixtures("preview")
def test_native_guards_scope_veto_and_missing_objects_decide_first(datos):
    comedor, colaborador = datos
    sin_permiso = _cliente("sin_permiso_col_k6")

    for url in _entradas(comedor, colaborador):
        assert Client().get(url).status_code == 403, url
        assert sin_permiso.get(url).status_code == 403, url
    root = _cliente("root_col_k6", is_superuser=True)
    assert root.get("/comedores/999999/colaboradores/crear/").status_code == 404
    assert (
        root.get(f"/comedores/{comedor.pk}/colaboradores/999999/editar/").status_code
        == 404
    )
    comedor.programa = Programas.objects.create(
        nombre="Abordaje Comunitario - Línea Secos"
    )
    comedor.save()
    assert root.get(f"/comedores/{comedor.pk}/colaboradores/crear/").status_code == 404
    colaborador.fecha_baja = date(2026, 9, 30)
    colaborador.save()
    assert (
        root.get(
            f"/comedores/{comedor.pk}/colaboradores/{colaborador.pk}/editar/"
        ).status_code
        == 404
    )
