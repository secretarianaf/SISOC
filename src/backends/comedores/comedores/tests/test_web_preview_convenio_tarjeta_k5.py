"""Local React preview entries of the comedor convenio PNUD and card holder pages (``comedores.web_preview_convenio_tarjeta``)."""

import types

import pytest
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.test import Client, override_settings

from comedores.models import Comedor, ComedorDatosConvenioPnud, Programas
from comedores.web_preview_convenio_tarjeta import convenio_tarjeta_preview_patterns
from config.urls_all import urlpatterns as monolith_patterns
from duplas.models import Dupla

INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)

pytestmark = pytest.mark.django_db


@pytest.fixture(name="comedor_fixture", autouse=True)
def sin_dobles_del_conftest():
    """Same name as the folder's autouse double: these tests run the real services."""


@pytest.fixture(name="preview")
def preview_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    (tmp_path / "assets" / "app-1.js").write_text("console.log(1);", encoding="utf-8")
    module = types.ModuleType("convenio_tarjeta_preview_test_urls")
    module.urlpatterns = convenio_tarjeta_preview_patterns(tmp_path) + list(
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


def _comedor(programa):
    return Comedor.objects.create(
        nombre="Comedor preview", programa=Programas.objects.create(nombre=programa)
    )


@pytest.mark.usefixtures("preview")
def test_the_entry_serves_the_frozen_index_without_creating_the_record():
    comedor = _comedor("PNUD")

    respuesta = _cliente("gestor_conv_k5", "comedores.change_comedor").get(
        f"/comedores/{comedor.pk}/convenio-pnud/"
    )

    assert respuesta.status_code == 200
    assert '/convenio-tarjeta/react/assets/app-1.js"' in respuesta.content.decode()
    assert "no-store" in respuesta["Cache-Control"]
    assert "csrftoken" in respuesta.cookies
    assert not ComedorDatosConvenioPnud.objects.exists()
    asset = Client().get("/convenio-tarjeta/react/assets/app-1.js")
    assert asset.content == b"console.log(1);"


@pytest.mark.usefixtures("preview")
def test_native_guards_decide_first():
    comedor = _comedor("PNUD")
    url = f"/comedores/{comedor.pk}/convenio-pnud/"

    assert Client().get(url).status_code == 403
    assert (
        _cliente("lector_conv_k5", "comedores.view_comedor").get(url).status_code == 403
    )
    root = _cliente("root_conv_k5", is_superuser=True)
    assert root.get("/comedores/999999/convenio-pnud/").status_code == 404


@pytest.mark.usefixtures("preview")
def test_a_comedor_outside_the_convenio_gets_the_native_redirect_and_message():
    otro = _comedor("Alimentar Comunidad")

    respuesta = _cliente("otro_conv_k5", "comedores.change_comedor").get(
        f"/comedores/{otro.pk}/convenio-pnud/"
    )

    assert respuesta.status_code == 302
    assert respuesta["Location"] == f"/comedores/{otro.pk}"
    assert [str(m) for m in messages.get_messages(respuesta.wsgi_request)] == [
        "Esta opcion solo aplica para comedores PNUD o Abordaje Comunitario."
    ]


def _tecnico(nombre, grupo=True):
    usuario = get_user_model().objects.create_user(nombre)
    usuario.user_permissions.add(
        Permission.objects.get_or_create(
            codename="role_tecnico_comedor",
            content_type=ContentType.objects.get_for_model(get_user_model()),
            defaults={"name": "role_tecnico_comedor"},
        )[0]
    )
    if grupo:
        usuario.groups.add(Group.objects.get_or_create(name="Tecnico Comedor")[0])
    client = Client()
    client.force_login(usuario)
    return usuario, client


def _comedor_de(usuario, programa="Alimentar Comunidad"):
    dupla = Dupla.objects.create(
        nombre="Dupla preview", estado="Activo", abogado=usuario
    )
    dupla.tecnico.add(usuario)
    return Comedor.objects.create(
        nombre="Comedor tarjeta",
        programa=Programas.objects.create(nombre=programa),
        dupla=dupla,
    )


@pytest.mark.usefixtures("preview")
def test_the_tarjeta_entry_serves_the_frozen_index_after_the_native_guards():
    usuario, tecnico = _tecnico("tecnico_tar_k5")
    comedor = _comedor_de(usuario)

    respuesta = tecnico.get(f"/comedores/{comedor.pk}/responsable-tarjeta/editar")

    assert respuesta.status_code == 200
    assert '/convenio-tarjeta/react/assets/app-1.js"' in respuesta.content.decode()
    assert "csrftoken" in respuesta.cookies


@pytest.mark.usefixtures("preview")
def test_the_tarjeta_entry_keeps_the_native_404s_and_403():
    usuario, tecnico = _tecnico("tecnico2_tar_k5")
    comedor = _comedor_de(usuario)
    otro_programa = _comedor_de(usuario, "Otro")
    _, sin_grupo = _tecnico("singrupo_tar_k5", grupo=False)
    url = f"/comedores/{comedor.pk}/responsable-tarjeta/editar"

    assert Client().get(url).status_code == 403
    assert sin_grupo.get(url).status_code == 404
    assert (
        tecnico.get(
            f"/comedores/{otro_programa.pk}/responsable-tarjeta/editar"
        ).status_code
        == 404
    )
    assert (
        tecnico.get("/comedores/999999/responsable-tarjeta/editar").status_code == 404
    )
