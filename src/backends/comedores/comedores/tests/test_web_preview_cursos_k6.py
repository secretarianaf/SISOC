"""Local React preview entries of the course catalog (``comedores.web_preview_cursos``)."""

import types

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.test import Client, override_settings

from comedores.models import CursoAppMobile
from comedores.web_preview_cursos import cursos_preview_patterns
from config.urls_all import urlpatterns as monolith_patterns

INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)
BASE = "/comedores/configuracion/cursos-app-mobile/"

pytestmark = pytest.mark.django_db


@pytest.fixture(name="preview")
def preview_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    (tmp_path / "assets" / "app-1.js").write_text("console.log(1);", encoding="utf-8")
    module = types.ModuleType("cursos_preview_test_urls")
    module.urlpatterns = cursos_preview_patterns(tmp_path) + list(monolith_patterns)
    with override_settings(ROOT_URLCONF=module):
        yield


def _cliente(nombre, *codes, **extra):
    usuario = get_user_model().objects.create_user(nombre, **extra)
    for code in codes:
        app, codename = code.split(".")
        # Role codes live on the ``Group`` content type, not on a model.
        usuario.user_permissions.add(
            Permission.objects.filter(
                content_type__app_label=app, codename=codename
            ).first()
            or Permission.objects.create(
                content_type=ContentType.objects.get_for_model(Group),
                codename=codename,
                name=codename,
            )
        )
    client = Client()
    client.force_login(usuario)
    return client


@pytest.fixture(name="curso")
def curso_fixture():
    return CursoAppMobile.objects.create(
        nombre="Curso preview",
        link="https://cursos.example/p",
        programa_objetivo="pnud",
    )


def _entradas(curso):
    return [
        BASE,
        f"{BASE}crear/",
        f"{BASE}{curso.pk}/editar/",
        f"{BASE}{curso.pk}/eliminar/",
    ]


@pytest.mark.usefixtures("preview")
def test_every_entry_serves_the_frozen_index_with_its_native_permission(curso):
    for indice, url in enumerate(_entradas(curso)):
        respuesta = _cliente(f"u{indice}_cur_k6", "auth.role_admin").get(url)
        assert respuesta.status_code == 200, url
        assert '/comedores/react/assets/app-1.js"' in respuesta.content.decode()
        assert "no-store" in respuesta["Cache-Control"]
        assert "csrftoken" in respuesta.cookies
    asset = Client().get("/comedores/react/assets/app-1.js")
    assert asset.content == b"console.log(1);"


@pytest.mark.usefixtures("preview")
def test_native_guards_paging_and_missing_objects_decide_first(curso):
    sin_permiso = _cliente("sin_permiso_cur_k6")

    for url in _entradas(curso):
        assert Client().get(url).status_code == 403, url
        assert sin_permiso.get(url).status_code == 403, url
    admin = _cliente("admin_cur_k6", "auth.role_admin")
    assert admin.get(f"{BASE}?page=9").status_code == 404
    for sufijo in ("editar", "eliminar"):
        assert admin.get(f"{BASE}999999/{sufijo}/").status_code == 404
    curso.delete()
    assert admin.get(f"{BASE}{curso.pk}/editar/").status_code == 404
