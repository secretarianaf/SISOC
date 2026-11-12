"""Local React preview entries of CDI screens (``centrodeinfancia.web_preview``)."""

import types

import pytest
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.test import Client, override_settings
from django.urls import reverse

from centrodeinfancia.web_preview import cdi_preview_patterns
from config.urls_all import urlpatterns as monolith_patterns

INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)
REPORTES = "/centrodeinfancia/reportes/"

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
    module = types.ModuleType("cdi_preview_test_urls")
    module.urlpatterns = cdi_preview_patterns(build) + list(monolith_patterns)
    with override_settings(ROOT_URLCONF=module):
        yield


def _cliente(user):
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture(name="reportes")
def reportes_fixture():
    user = User.objects.create_user("preview-reportes")
    permiso, _ = Permission.objects.get_or_create(
        content_type=ContentType.objects.get_for_model(Group),
        codename="role_reportes_cdi",
        defaults={"name": "Reportes CDI"},
    )
    user.user_permissions.add(permiso)
    return _cliente(user)


@pytest.mark.usefixtures("preview")
def test_reports_entry_returns_the_frozen_index_with_rewritten_assets(reportes):
    respuesta = reportes.get(REPORTES, {"provincia": "1"})

    assert respuesta.status_code == 200
    body = respuesta.content.decode()
    assert '/centrodeinfancia/react/assets/app-1.js"' in body
    assert "/v2/sisoc/assets/" not in body
    assert respuesta["Content-Type"] == "text/html; charset=utf-8"
    assert "no-store" in respuesta["Cache-Control"]
    assert "private" in respuesta["Cache-Control"]
    assert "Cookie" in respuesta["Vary"]
    assert "csrftoken" in respuesta.cookies
    assert reportes.head(REPORTES).content == b""


@pytest.mark.usefixtures("preview")
def test_reports_entry_keeps_the_native_guards():
    native = Client().get(REPORTES)
    with override_settings(ROOT_URLCONF="config.urls_all"):
        expected = Client().get(REPORTES)
    assert native.status_code == expected.status_code
    assert native.get("Location") == expected.get("Location")

    sin_permiso = _cliente(User.objects.create_user("preview-sin-reportes"))
    assert sin_permiso.get(REPORTES).status_code == 403


@pytest.mark.usefixtures("preview")
def test_only_frozen_assets_are_served(client):
    asset = client.get("/centrodeinfancia/react/assets/app-1.js")

    assert asset.status_code == 200
    assert asset.content == b"console.log(1);"
    assert asset["Cache-Control"] == "public, max-age=31536000, immutable"
    assert asset["X-Content-Type-Options"] == "nosniff"
    assert client.get("/centrodeinfancia/react/assets/app-1.js?x=1").status_code == 404
    assert client.get("/centrodeinfancia/react/assets/notes.txt").status_code == 404
    assert client.get("/centrodeinfancia/react/assets/otro.js").status_code == 404
    assert client.post("/centrodeinfancia/react/assets/app-1.js").status_code == 405


def test_build_without_index_is_refused(tmp_path):
    with pytest.raises(ValueError):
        cdi_preview_patterns(tmp_path)


def test_production_urlconf_keeps_the_native_page(reportes):
    respuesta = reportes.get(REPORTES)

    assert respuesta.status_code == 200
    assert "centrodeinfancia/reportes.html" in [t.name for t in respuesta.templates]


# --- Observations (CDI07) -------------------------------------------------------

OPERACIONES = (
    "view_centrodeinfancia",
    "add_intervencioncentroinfancia",
    "change_intervencioncentroinfancia",
    "delete_intervencioncentroinfancia",
)


@pytest.fixture(name="observacion")
def observacion_fixture():
    from centrodeinfancia.models import CentroDeInfancia, ObservacionCentroInfancia

    centro = CentroDeInfancia.objects.create(nombre="CDI Preview")
    return ObservacionCentroInfancia.objects.create(centro=centro, observacion="Texto.")


@pytest.fixture(name="operador")
def operador_fixture():
    user = User.objects.create_user("preview-operador", first_name="Ana")
    for codename in OPERACIONES:
        user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="centrodeinfancia", codename=codename
            )
        )
    return _cliente(user)


def _rutas(observacion):
    return [
        f"/centrodeinfancia/{observacion.centro_id}/observacion/crear/",
        f"/centrodeinfancia/observacion/{observacion.pk}/",
        f"/centrodeinfancia/observacion/{observacion.pk}/editar/",
        f"/centrodeinfancia/observacion/{observacion.pk}/eliminar/",
    ]


@pytest.mark.usefixtures("preview")
def test_observation_entries_return_the_index_after_the_native_checks(
    operador, observacion
):
    for ruta in _rutas(observacion):
        respuesta = operador.get(ruta)
        assert respuesta.status_code == 200, ruta
        assert b"/centrodeinfancia/react/assets/app-1.js" in respuesta.content, ruta
        assert "no-store" in respuesta["Cache-Control"], ruta

    for ruta in (
        "/centrodeinfancia/999999/observacion/crear/",
        "/centrodeinfancia/observacion/999999/",
        "/centrodeinfancia/observacion/999999/editar/",
        "/centrodeinfancia/observacion/999999/eliminar/",
    ):
        assert operador.get(ruta).status_code == 404, ruta
    sin_permiso = _cliente(User.objects.create_user("preview-sin-obs"))
    for ruta in _rutas(observacion):
        assert sin_permiso.get(ruta).status_code == 403, ruta


@pytest.mark.usefixtures("preview")
def test_observation_entries_keep_the_native_posts(operador, observacion):
    from centrodeinfancia.models import ObservacionCentroInfancia

    ficha = reverse("centrodeinfancia_detalle", args=[observacion.centro_id])
    crear, _detalle, editar, eliminar = _rutas(observacion)

    alta = operador.post(crear, {"observacion": "Nueva", "next": ficha})
    edicion = operador.post(editar, {"observacion": "Editada"})
    baja = operador.post(eliminar)

    assert alta.status_code == 302 and alta["Location"] == ficha
    assert ObservacionCentroInfancia.objects.filter(observacion="Nueva").exists()
    assert edicion.status_code == 302
    assert baja.status_code == 302 and baja["Location"] == ficha
    assert ObservacionCentroInfancia.all_objects.get(pk=observacion.pk).deleted_at
    assert operador.post(_detalle).status_code == 405


# --- Centres list (CDI09.01) and beneficiary detail (CDI04.01) ---------------------


@pytest.fixture(name="ficha")
def ficha_fixture():
    from centrodeinfancia.models import CentroDeInfancia, NominaCentroInfancia
    from ciudadanos.models import Ciudadano

    centro = CentroDeInfancia.objects.create(nombre="CDI Lista")
    ciudadano = Ciudadano.objects.create(apellido="Gomez", nombre="Luz", documento=3)
    return NominaCentroInfancia.objects.create(
        centro=centro, ciudadano=ciudadano, apellido="Gomez", nombre="Luz"
    )


@pytest.mark.usefixtures("preview")
def test_list_and_detail_entries_return_the_index_after_the_native_checks(ficha):
    user = User.objects.create_user("preview-lista")
    user.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="centrodeinfancia", codename="view_centrodeinfancia"
        )
    )
    client = _cliente(user)
    detalle = f"/centrodeinfancia/{ficha.centro_id}/nomina/{ficha.pk}/ver/"

    for ruta in ("/centrodeinfancia/listar", detalle):
        respuesta = client.get(ruta)
        assert respuesta.status_code == 200, ruta
        assert b"/centrodeinfancia/react/assets/app-1.js" in respuesta.content, ruta
        assert "no-store" in respuesta["Cache-Control"], ruta
        assert client.head(ruta).content == b"", ruta
    assert client.get("/centrodeinfancia/listar", {"page": "9"}).status_code == 404
    assert (
        client.get(
            f"/centrodeinfancia/{ficha.centro_id}/nomina/999999/ver/"
        ).status_code
        == 404
    )
    sin_permiso = _cliente(User.objects.create_user("preview-lista-sin"))
    for ruta in ("/centrodeinfancia/listar", detalle):
        assert sin_permiso.get(ruta).status_code == 403, ruta
        assert Client().get(ruta).status_code in (302, 401, 403), ruta
