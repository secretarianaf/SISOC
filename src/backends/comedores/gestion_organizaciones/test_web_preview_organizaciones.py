"""Local React preview entry of O05 (``gestion_organizaciones.web_preview``)."""

import types

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.test import Client, override_settings

from comedores.models import Comedor
from duplas.models import Dupla
from organizaciones.models import Organizacion
from config.urls_all import urlpatterns as monolith_patterns
from gestion_organizaciones.web_preview import organizaciones_preview_patterns

INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)
LISTADO = "/organizaciones/listar"

pytestmark = pytest.mark.django_db


@pytest.fixture(name="build")
def build_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    (tmp_path / "assets" / "app-1.js").write_text("console.log(1);", encoding="utf-8")
    return tmp_path


@pytest.fixture(name="preview")
def preview_fixture(build):
    module = types.ModuleType("organizaciones_preview_test_urls")
    module.urlpatterns = organizaciones_preview_patterns(build) + list(
        monolith_patterns
    )
    with override_settings(ROOT_URLCONF=module):
        yield


def _permiso(code):
    app, codename = code.split(".")
    if app == "auth":
        return Permission.objects.get_or_create(
            content_type=ContentType.objects.get_for_model(Group),
            codename=codename,
            defaults={"name": codename},
        )[0]
    return Permission.objects.get(content_type__app_label=app, codename=codename)


def _login(nombre, *codes):
    usuario = get_user_model().objects.create_user(nombre)
    for code in codes:
        usuario.user_permissions.add(_permiso(code))
    client = Client()
    client.force_login(usuario)
    return client


@pytest.mark.usefixtures("preview")
def test_the_list_gets_the_frozen_index():
    client = _login("tecnico_prev_org", "auth.role_tecnico_comedor")

    respuesta = client.get(LISTADO, {"filters": '{"items": []}', "page": "9"})

    assert respuesta.status_code == 200
    assert '/organizaciones/react/assets/app-1.js"' in respuesta.content.decode()
    assert "no-store" in respuesta["Cache-Control"]
    assert "csrftoken" in respuesta.cookies
    asset = client.get("/organizaciones/react/assets/app-1.js")
    assert asset.content == b"console.log(1);"


@pytest.mark.usefixtures("preview")
def test_native_guards_decide_first():
    # The URL decorator answers before ``LoginRequiredMixin``: 403, not a redirect.
    assert Client().get(LISTADO).status_code == 403
    assert _login("sin_prev_org").get(LISTADO).status_code == 403
    assert (
        _login("csv_prev_org", "auth.role_exportar_a_csv").get(LISTADO).status_code
        == 403
    )


@pytest.mark.usefixtures("preview")
def test_the_csv_stays_the_native_download():
    exporta = _login(
        "exporta_prev_org",
        "organizaciones.view_organizacion",
        "auth.role_exportar_a_csv",
    )

    respuesta = exporta.get("/organizaciones/exportar")

    assert respuesta.status_code == 200
    assert respuesta["Content-Type"].startswith("text/csv")
    assert 'filename="exportacion_organizaciones_' in respuesta["Content-Disposition"]


@pytest.mark.usefixtures("preview")
def test_the_legajo_gets_the_frozen_index_inside_the_dupla_scope():
    propia = Organizacion.objects.create(nombre="Propia")
    ajena = Organizacion.objects.create(nombre="Ajena")
    tecnico = get_user_model().objects.create_user("tec_leg_prev")
    abogado = get_user_model().objects.create_user("abo_leg_prev")
    dupla = Dupla.objects.create(nombre="D", estado="Activo", abogado=abogado)
    dupla.tecnico.add(tecnico)
    Comedor.objects.create(nombre="C", organizacion=propia, dupla=dupla)
    client = _login("lector_leg_prev", "organizaciones.view_organizacion")
    assert Client().get(f"/organizaciones/detalle/{propia.pk}").status_code == 403

    todo = client.get(f"/organizaciones/detalle/{ajena.pk}")
    assert todo.status_code == 200
    assert '/organizaciones/react/assets/app-1.js"' in todo.content.decode()
    assert "no-store" in todo["Cache-Control"]
    limitado = Client()
    limitado.force_login(tecnico)
    tecnico.user_permissions.add(_permiso("auth.role_tecnico_comedor"))
    assert limitado.get(f"/organizaciones/detalle/{propia.pk}").status_code == 200
    assert limitado.get(f"/organizaciones/detalle/{ajena.pk}").status_code == 404


@pytest.mark.usefixtures("preview")
def test_the_abm_gets_the_frozen_index_with_the_native_guards():
    organizacion = Organizacion.objects.create(nombre="Abm preview")
    paths = (
        "/organizaciones/crear",
        f"/organizaciones/editar/{organizacion.pk}",
        f"/organizaciones/eliminar/{organizacion.pk}",
    )
    lector = _login("abm_prev_org", "organizaciones.view_organizacion")
    tecnico = _login("abm_prev_tec", "auth.role_tecnico_comedor")

    for path in paths:
        assert Client().get(path).status_code == 403
        assert tecnico.get(path).status_code == 403
        respuesta = lector.get(path)
        assert respuesta.status_code == 200
        assert '/organizaciones/react/assets/app-1.js"' in respuesta.content.decode()
        assert "no-store" in respuesta["Cache-Control"]
        # React saves through the web API: the entry has no native POST.
        assert lector.post(path).status_code == 405
    assert lector.get("/organizaciones/editar/999999").status_code == 404
    assert lector.get("/organizaciones/eliminar/999999").status_code == 404


def test_build_without_index_is_refused(tmp_path):
    with pytest.raises(ValueError):
        organizaciones_preview_patterns(tmp_path)
