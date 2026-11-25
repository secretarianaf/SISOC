"""Local React preview entries of the comunicados (``comunicados.web_preview``)."""

import types

import pytest
from django.contrib.auth.models import Permission, User
from django.test import Client, override_settings
from django.utils import timezone

from comunicados.models import Comunicado, EstadoComunicado, TipoComunicado
from comunicados.web_preview import comunicados_preview_patterns
from config.urls_all import urlpatterns as monolith_patterns

INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
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
    module = types.ModuleType("comunicados_preview_test_urls")
    module.urlpatterns = comunicados_preview_patterns(build) + list(monolith_patterns)
    with override_settings(ROOT_URLCONF=module):
        yield


def _login(nombre, perms=()):
    usuario = User.objects.create_user(nombre)
    for codename in perms:
        usuario.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="comunicados", codename=codename
            )
        )
    client = Client()
    client.force_login(usuario)
    return client


def _comunicado(**campos):
    creador = User.objects.get_or_create(username="creador_prev_cm")[0]
    datos = {
        "titulo": "Aviso",
        "cuerpo": "Texto",
        "estado": EstadoComunicado.PUBLICADO,
        "tipo": TipoComunicado.INTERNO,
        "fecha_publicacion": timezone.now(),
        **campos,
    }
    return Comunicado.objects.create(usuario_creador=creador, **datos)


@pytest.mark.usefixtures("preview")
def test_list_and_reader_detail_get_the_frozen_index():
    comunicado = _comunicado()
    client = _login("lector_prev_cm")

    for url in ("/comunicados/", f"/comunicados/ver/{comunicado.pk}/"):
        respuesta = client.get(url)
        assert respuesta.status_code == 200
        assert '/comunicados/react/assets/app-1.js"' in respuesta.content.decode()
        assert "no-store" in respuesta["Cache-Control"]
        assert "csrftoken" in respuesta.cookies
    asset = client.get("/comunicados/react/assets/app-1.js")
    assert asset.content == b"console.log(1);"


@pytest.mark.usefixtures("preview")
def test_native_guards_decide_first():
    oculto = _comunicado(estado=EstadoComunicado.BORRADOR)
    anonimo = Client().get("/comunicados/")
    assert anonimo.status_code == 302
    assert anonimo["Location"].startswith("/login/")
    lector = _login("lector2_prev_cm")
    assert lector.get("/comunicados/", {"page": "9"}).status_code == 404
    assert lector.get("/comunicados/", {"page": "x"}).status_code == 404
    assert lector.get(f"/comunicados/ver/{oculto.pk}/").status_code == 404


@pytest.mark.usefixtures("preview")
def test_managers_get_the_index_for_gestion_and_detail():
    borrador = _comunicado(estado=EstadoComunicado.BORRADOR)
    gestor = _login("gestor_prev_cm", perms=["change_comunicado"])

    for url in ("/comunicados/gestion/", f"/comunicados/ver/{borrador.pk}/"):
        respuesta = gestor.get(url)
        assert respuesta.status_code == 200
        assert '/comunicados/react/assets/app-1.js"' in respuesta.content.decode()


@pytest.mark.usefixtures("preview")
def test_gestion_keeps_the_native_guards():
    anonimo = Client().get("/comunicados/gestion/")
    assert anonimo.status_code == 403
    assert _login("lector3_prev_cm").get("/comunicados/gestion/").status_code == 403
    gestor = _login("gestor2_prev_cm", perms=["add_comunicado"])
    assert gestor.get("/comunicados/gestion/", {"page": "9"}).status_code == 404


@pytest.mark.usefixtures("preview")
def test_delete_entry_keeps_the_native_order_of_guards():
    borrador = _comunicado(estado=EstadoComunicado.BORRADOR)
    publicado = _comunicado()
    admin = User.objects.create_user("admin_prev_cm", is_superuser=True)
    client = Client()
    client.force_login(admin)

    respuesta = client.get(f"/comunicados/eliminar/{borrador.pk}/")
    assert respuesta.status_code == 200
    assert '/comunicados/react/assets/app-1.js"' in respuesta.content.decode()
    assert client.get(f"/comunicados/eliminar/{publicado.pk}/").status_code == 403
    assert client.get("/comunicados/eliminar/999999/").status_code == 404
    assert Client().get(f"/comunicados/eliminar/{borrador.pk}/").status_code == 403
    assert (
        _login("gestor3_prev_cm", perms=["change_comunicado"])
        .get(f"/comunicados/eliminar/{borrador.pk}/")
        .status_code
        == 403
    )


@pytest.mark.usefixtures("preview")
def test_create_and_edit_entries_keep_the_native_guards():
    borrador = _comunicado(estado=EstadoComunicado.BORRADOR)
    publicado = _comunicado()
    editor = _login("editor_prev_cm", perms=["change_comunicado"])
    creador = _login("creador2_prev_cm", perms=["add_comunicado"])

    for url in ("/comunicados/crear/", f"/comunicados/editar/{borrador.pk}/"):
        client = creador if "crear" in url else editor
        respuesta = client.get(url)
        assert respuesta.status_code == 200
        assert '/comunicados/react/assets/app-1.js"' in respuesta.content.decode()
    assert editor.get(f"/comunicados/editar/{publicado.pk}/").status_code == 403
    assert editor.get("/comunicados/editar/999999/").status_code == 404
    assert editor.get("/comunicados/crear/").status_code == 403
    assert _login("lector4_prev_cm").get("/comunicados/crear/").status_code == 403


def test_build_without_index_is_refused(tmp_path):
    with pytest.raises(ValueError):
        comunicados_preview_patterns(tmp_path)
