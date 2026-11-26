"""Canonical Inspecciones import pages with a compatible SISOC build."""

import json
import re
import types

import pytest
from django.test import Client, override_settings
from django.urls import reverse

from config.urls_all import urlpatterns as monolith_patterns
from inspecciones.models import AsignacionEscuela, Escuela
from inspecciones.web_preview import actas_preview_patterns

pytestmark = pytest.mark.django_db

MARKER = '<meta name="sisoc-react-inspecciones-importacion" content="1">'
SHELL = (
    '<!doctype html><html><head>{marker}<script type="module" '
    'src="/v2/sisoc/assets/app.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)
BOOTSTRAP = re.compile(
    r'<script id="inspecciones-importacion-data" type="application/json">(.*?)</script>',
    re.S,
)


@pytest.fixture
def import_urls(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "app.js").write_text("// synthetic build", encoding="utf-8")

    def install(*, compatible=True):
        (tmp_path / "index.html").write_text(
            SHELL.format(marker=MARKER if compatible else ""), encoding="utf-8"
        )
        module = types.ModuleType("inspecciones_import_preview_urls")
        module.urlpatterns = actas_preview_patterns(tmp_path) + list(monolith_patterns)
        return override_settings(ROOT_URLCONF=module)

    return install


def _data(response, step):
    assert response.status_code == 200
    body = response.content.decode()
    assert '/inspecciones/react/assets/app.js"' in body
    script = BOOTSTRAP.search(body)
    assert script is not None
    payload = json.loads(script.group(1))
    assert payload["paso"] == step
    assert "private" in response["Cache-Control"]
    assert "no-store" in response["Cache-Control"]
    assert "Cookie" in response["Vary"]
    return payload


def _file(tipo, planilla, escuela):
    if tipo == "asignaciones":
        return planilla(
            [
                ("fecha", "cueanexo", "inspector"),
                ("2026-10-15", escuela.cue, "inspector_a"),
                ("2026-10-15", "999999999", "inspector_a"),
            ],
            nombre="asignaciones.csv",
        )
    return planilla(
        [
            ("Jurisdicción", "Localidad", "Cueanexo", "Nombre", "Domicilio"),
            ("Buenos Aires", "SAN JUSTO", "060123401", "Escuela de prueba", "Calle 1"),
            ("Buenos Aires", "SAN JUSTO", "060123401", "</script>", "Calle 2"),
        ],
        nombre="escuelas.csv",
    )


@pytest.mark.parametrize("tipo", ["escuelas", "asignaciones"])
@pytest.mark.usefixtures("geografia", "inspector_a")
def test_canonical_import_review_and_result(
    tipo, panel, escuela, planilla, import_urls
):
    prefix = f"inspecciones_importar_{tipo}"
    models = Escuela if tipo == "escuelas" else AsignacionEscuela
    before = models.objects.count()
    with import_urls():
        upload = panel.post(
            reverse(prefix), {"archivo": _file(tipo, planilla, escuela)}
        )
        assert upload.status_code == 302
        review = panel.get(upload["Location"])
        data = _data(review, 2)
        assert data["tipo"] == tipo
        assert data["resumen"]["a_importar"] == 1
        assert data["total_observaciones"] == 1
        assert models.objects.count() == before
        assert data["urls"]["subir"] == reverse(prefix)
        assert panel.head(upload["Location"]).content == b""

        download = panel.get(data["urls"]["observaciones"])
        assert download.status_code == 200
        assert download["Cache-Control"] == "private, no-store"
        assert panel.get(data["urls"]["confirmar"]).status_code == 405

        result = _data(panel.post(data["urls"]["confirmar"]), 3)
        assert result["resumen"]["a_importar"] == 1
        assert result["urls"] == {"volver": data["urls"]["volver"]}
        assert models.objects.count() == before + 1
        for url, method in (
            (upload["Location"], panel.get),
            (data["urls"]["confirmar"], panel.post),
        ):
            assert method(url).status_code == 302
        assert models.objects.count() == before + 1


@pytest.mark.parametrize("tipo", ["escuelas", "asignaciones"])
@pytest.mark.usefixtures("geografia", "inspector_a")
def test_embedded_import_preserves_csrf_ownership_and_cancel(
    tipo, escuela, gestor, coordinacion, inspector_a, planilla, import_urls
):
    prefix = f"inspecciones_importar_{tipo}"
    model = Escuela if tipo == "escuelas" else AsignacionEscuela
    before = model.objects.count()
    owner = Client(enforce_csrf_checks=True)
    owner.force_login(gestor)
    other = Client()
    other.force_login(coordinacion)
    upload_path = reverse(prefix)

    with import_urls():
        entry = _data(owner.get(upload_path), 1)
        assert entry["errores"] == []
        assert owner.post(upload_path).status_code == 403
        invalid = owner.post(upload_path, {"csrfmiddlewaretoken": entry["csrf"]})
        assert _data(invalid, 1)["errores"]
        upload = owner.post(
            upload_path,
            {
                "archivo": _file(tipo, planilla, escuela),
                "csrfmiddlewaretoken": entry["csrf"],
            },
        )
        assert upload.status_code == 302
        path = upload["Location"]
        data = _data(owner.get(path), 2)
        assert "csrf" in data

        for url, request in [
            (path, other.get),
            (data["urls"]["confirmar"], other.post),
            (data["urls"]["observaciones"], other.get),
            (data["urls"]["cancelar"], other.post),
            (path, Client().get),
        ]:
            response = request(url)
            assert response.status_code == 302
            assert not BOOTSTRAP.search(response.content.decode())
        other.force_login(inspector_a)
        assert other.get(path).status_code == 403
        assert owner.post(data["urls"]["confirmar"]).status_code == 403
        assert owner.get(data["urls"]["cancelar"]).status_code == 405
        assert model.objects.count() == before

        cancelled = owner.post(
            data["urls"]["cancelar"], {"csrfmiddlewaretoken": data["csrf"]}
        )
        assert cancelled.status_code == 302
        assert cancelled["Location"] == data["urls"]["volver"]
        assert owner.get(path).status_code == 302
        assert model.objects.count() == before


@pytest.mark.usefixtures("geografia", "inspector_a")
def test_previous_build_keeps_native_import_response(
    panel, escuela, planilla, import_urls
):
    prefix = "inspecciones_importar_escuelas"
    with import_urls(compatible=False):
        upload_path = reverse(prefix)
        assert "inspecciones/importar_archivo.html" in [
            t.name for t in panel.get(upload_path).templates
        ]
        upload = panel.post(
            upload_path, {"archivo": _file("escuelas", planilla, escuela)}
        )
        review = panel.get(upload["Location"])
        assert "inspecciones/importar_revision.html" in [
            t.name for t in review.templates
        ]
        token = review.context["token"]
        result = panel.post(reverse(f"{prefix}_confirmar", args=[token]))
        assert "inspecciones/importar_resultado.html" in [
            t.name for t in result.templates
        ]
