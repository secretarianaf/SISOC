"""Local React preview entries of VAT vouchers and evaluaciones (``VAT.web_preview_vat``)."""

import itertools
import types

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, override_settings

from config.urls_all import urlpatterns as monolith_patterns
from VAT.web_preview_vat import vat_preview_patterns

INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)

pytestmark = pytest.mark.django_db
_COUNTER = itertools.count()


@pytest.fixture(name="build")
def build_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    (tmp_path / "assets" / "app-1.js").write_text("console.log(1);", encoding="utf-8")
    (tmp_path / "assets" / "notes.txt").write_text("not served", encoding="utf-8")
    return tmp_path


@pytest.fixture(name="preview")
def preview_fixture(build):
    module = types.ModuleType("vat_preview_test_urls")
    module.urlpatterns = vat_preview_patterns(build) + list(monolith_patterns)
    with override_settings(ROOT_URLCONF=module):
        yield


def _client(*codes):
    user = get_user_model().objects.create_user(f"u{next(_COUNTER)}")
    user.user_permissions.add(
        *Permission.objects.filter(content_type__app_label="VAT", codename__in=codes)
    )
    client = Client()
    client.force_login(user)
    return client


@pytest.mark.usefixtures("preview")
@pytest.mark.parametrize(
    "url,code",
    [
        ("/vat/vouchers/", "view_voucher"),
        ("/vat/vouchers/parametrias/", "view_voucher"),
        ("/vat/evaluaciones/", "view_evaluacion"),
        ("/vat/evaluaciones/nueva/", "add_evaluacion"),
        ("/vat/resultados-evaluacion/", "view_resultadoevaluacion"),
        ("/vat/resultados-evaluacion/nuevo/", "add_resultadoevaluacion"),
        ("/vat/vouchers/asignar/", "add_voucher"),
        ("/vat/vouchers/asignar-masivo/", "add_voucher"),
        ("/vat/vouchers/parametrias/nueva/", "add_voucher"),
    ],
)
def test_list_entries_serve_the_frozen_index_behind_the_native_guards(url, code):
    response = _client(code).get(url)
    assert response.status_code == 200
    body = response.content.decode()
    assert '/vat/react/assets/app-1.js"' in body
    assert "/v2/sisoc/assets/" not in body
    assert "no-store" in response["Cache-Control"]
    assert "csrftoken" in response.cookies
    assert _client("view_centro").get(url).status_code == 403
    if "nueva" not in url and "nuevo" not in url and "asignar" not in url:
        assert _client(code).get(url, {"page": 9}).status_code == 404
    assert Client().get(url).status_code == 403


@pytest.mark.usefixtures("preview")
@pytest.mark.parametrize(
    "url,code",
    [
        ("/vat/vouchers/999999/", "view_voucher"),
        ("/vat/vouchers/parametrias/999999/", "view_voucher"),
        ("/vat/evaluaciones/999999/", "view_evaluacion"),
        ("/vat/evaluaciones/999999/editar/", "change_evaluacion"),
        ("/vat/evaluaciones/999999/eliminar/", "delete_evaluacion"),
        ("/vat/resultados-evaluacion/999999/", "view_resultadoevaluacion"),
        ("/vat/resultados-evaluacion/999999/editar/", "change_resultadoevaluacion"),
        ("/vat/resultados-evaluacion/999999/eliminar/", "delete_resultadoevaluacion"),
    ],
)
def test_detail_entries_keep_the_native_404(url, code):
    assert _client(code).get(url).status_code == 404


@pytest.mark.usefixtures("preview")
def test_only_frozen_assets_are_served(client):
    assert client.get("/vat/react/assets/app-1.js").status_code == 200
    assert client.get("/vat/react/assets/notes.txt").status_code == 404
    assert client.get("/vat/react/assets/app-1.js?x=1").status_code == 404
    assert client.get("/vat/react/assets/../index.html").status_code == 404


@pytest.mark.usefixtures("preview")
def test_report_entry_keeps_the_native_downloads():
    for code in ("view_inscripcion", "view_comisioncurso", "view_centro"):
        entry = _client(code).get("/vat/reportes/inscripciones-asistencias/")
        assert entry.status_code == 200
        assert '/vat/react/assets/app-1.js"' in entry.content.decode()
        assert "csrftoken" in entry.cookies
    assert Client().get("/vat/reportes/inscripciones-asistencias/").status_code == 403
    client = _client("view_inscripcion")
    for export, tipo in (("csv", "text/csv"), ("detalle_csv", "text/csv")):
        response = client.get(
            "/vat/reportes/inscripciones-asistencias/", {"export": export}
        )
        assert response.status_code == 200
        assert response["Content-Type"].startswith(tipo)
        assert "attachment" in response["Content-Disposition"]
    assert client.get("/vat/reportes/inscripciones-asistencias/", {"export": "otro"})[
        "Content-Type"
    ].startswith("text/html")
    assert (
        _client("view_voucher")
        .get("/vat/reportes/inscripciones-asistencias/", {"export": "csv"})
        .status_code
        == 403
    )
