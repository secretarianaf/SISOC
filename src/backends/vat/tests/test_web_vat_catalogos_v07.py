"""V07.01 y V07.02: web API y vista previa de los catálogos de VAT (sectores, subsectores, modalidades, títulos)."""

import itertools
import types

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, override_settings
from django.utils.html import escape
from rest_framework.test import APIClient

from config.urls_all import urlpatterns as monolith_patterns
from core.models import Provincia
from VAT.models import (
    ModalidadCursada,
    PlanVersionCurricular,
    Sector,
    Subsector,
    TituloReferencia,
)
from VAT.web_preview_vat_catalogos import catalogos_preview_patterns

pytestmark = pytest.mark.django_db

ROOT = "/api/web/vat/catalogos/"
_COUNTER = itertools.count()
INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)
# slug, segmento de alta, codename, modelo
CATALOGOS = (
    ("sectores", "nuevo", "sector", Sector),
    ("subsectores", "nuevo", "subsector", Subsector),
    ("modalidades-cursado", "nueva", "modalidadcursada", ModalidadCursada),
    ("titulos-referencia", "nuevo", "tituloreferencia", TituloReferencia),
)


def _client(*codes, csrf=False):
    user = get_user_model().objects.create_user(f"u{next(_COUNTER)}")
    user.user_permissions.add(
        *Permission.objects.filter(content_type__app_label="VAT", codename__in=codes)
    )
    client = APIClient(enforce_csrf_checks=csrf)
    client.force_login(user)
    client.user = user
    return client


@pytest.fixture(name="datos")
def datos_fixture():
    sector = Sector.objects.create(nombre="Industria", descripcion="una " * 14 + "fin")
    subsector = Subsector.objects.create(sector=sector, nombre="Metalurgia")
    modalidad = ModalidadCursada.objects.create(nombre="Presencial", activo=True)
    plan = PlanVersionCurricular.objects.create(
        nombre="Electricidad",
        provincia=Provincia.objects.create(nombre="Buenos Aires"),
        sector=sector,
        subsector=subsector,
        modalidad_cursada=modalidad,
        horas_reloj=100,
    )
    titulo = TituloReferencia.objects.create(
        nombre="Electricista", codigo_referencia="E-1", plan_estudio=plan, activo=True
    )
    plan.titulos.add(titulo)
    return types.SimpleNamespace(
        sector=sector, subsector=subsector, modalidad=modalidad, titulo=titulo
    )


def _objeto(datos, modelo):
    return {
        "sector": datos.sector,
        "subsector": datos.subsector,
        "modalidadcursada": datos.modalidad,
        "tituloreferencia": datos.titulo,
    }[modelo]


def test_access_follows_each_native_route_rule(datos):
    for slug, nuevo, modelo, _clase in CATALOGOS:
        pk = _objeto(datos, modelo).pk
        urls = {
            f"{ROOT}{slug}/": "view",
            f"{ROOT}{slug}/{pk}/": "view",
            f"{ROOT}{slug}/{nuevo}/": "add",
            f"{ROOT}{slug}/{pk}/editar/": "change",
            f"{ROOT}{slug}/{pk}/eliminar/": "delete",
        }
        for url, accion in urls.items():
            assert APIClient().get(url).status_code == 401, url
            for otra in {"view", "add", "change", "delete"} - {accion}:
                assert _client(f"{otra}_{modelo}").get(url).status_code == 403, url
            assert _client(f"{accion}_{modelo}").get(url).status_code == 200, url
        assert _client(f"view_{modelo}").get(f"{ROOT}{slug}/999999/").status_code == 404
        assert (
            _client(f"change_{modelo}").get(f"{ROOT}{slug}/999999/editar/").status_code
            == 404
        )


def test_lists_project_rows_buttons_and_page(datos):
    cliente = _client("view_sector", "change_sector")
    data = cliente.get(f"{ROOT}sectores/").json()
    fila = data["results"][0]
    assert (fila["id"], fila["nombre"], fila["subsectores"]) == (
        datos.sector.pk,
        "Industria",
        1,
    )
    assert fila["descripcion"] == "una " * 9 + "una …"
    assert data["permisos"] == {"editar": True, "eliminar": False}
    assert data["urls"] == {
        "list": "/vat/catalogos/sectores/",
        "create": "/vat/catalogos/sectores/nuevo/",
    }
    assert data["page"]["count"] == 1 and data["messages"] == []
    sub = _client("view_subsector").get(f"{ROOT}subsectores/").json()["results"][0]
    assert (sub["sector"], sub["nombre"], sub["descripcion"]) == (
        "Industria",
        "Metalurgia",
        "None",  # ``truncatewords`` prints a null description as the native list does
    )
    mod = _client("view_modalidadcursada").get(f"{ROOT}modalidades-cursado/").json()
    assert mod["results"][0]["activo"] is True
    assert [f["name"] for f in mod["filters_config"]["fields"]] == [
        "nombre",
        "descripcion",
        "activo",
    ]
    assert mod["favorites"]["url"] == "/ajax/filtros-favoritos/"
    tit = _client("view_tituloreferencia").get(f"{ROOT}titulos-referencia/").json()
    fila = tit["results"][0]
    assert (fila["codigo"], fila["activo"]) == ("E-1", True)
    assert fila["plan_estudio"] == str(datos.titulo.plan_estudio)
    assert cliente.get(f"{ROOT}sectores/", {"page": 9}).status_code == 404


def test_details_project_the_native_context(datos):
    sector = _client("view_sector").get(f"{ROOT}sectores/{datos.sector.pk}/").json()
    assert (sector["nombre"], sector["subsectores"]) == ("Industria", ["Metalurgia"])
    sub = _client("view_subsector").get(f"{ROOT}subsectores/{datos.subsector.pk}/")
    assert sub.json()["sector"] == {
        "nombre": "Industria",
        "url": f"/vat/catalogos/sectores/{datos.sector.pk}/",
    }
    assert sub.json()["descripcion"] == "Sin descripción"
    mod = _client("view_modalidadcursada").get(
        f"{ROOT}modalidades-cursado/{datos.modalidad.pk}/"
    )
    assert mod.json()["activo"] is True
    tit = _client("view_tituloreferencia").get(
        f"{ROOT}titulos-referencia/{datos.titulo.pk}/"
    )
    assert tit.json()["planes"] == ["Industria / Metalurgia - Presencial"]
    assert (tit.json()["codigo"], tit.json()["plan_estudio"]) == (
        "E-1",
        str(datos.titulo.plan_estudio),
    )


def test_projected_texts_are_the_ones_the_native_pages_print(datos):
    todos = [
        f"{a}_{m}"
        for a in ("view", "add", "change", "delete")
        for m in ("sector", "subsector", "modalidadcursada", "tituloreferencia")
    ]
    api = _client(*todos)
    nativo = Client()
    nativo.force_login(api.user)
    html = nativo.get("/vat/catalogos/sectores/").content.decode()
    fila = api.get(f"{ROOT}sectores/").json()["results"][0]
    assert escape(fila["descripcion"]) in html
    html = nativo.get(
        f"/vat/catalogos/titulos-referencia/{datos.titulo.pk}/"
    ).content.decode()
    detalle = api.get(f"{ROOT}titulos-referencia/{datos.titulo.pk}/").json()
    assert escape(detalle["plan_estudio"]) in html
    assert " ".join(html.split()).count(detalle["planes"][0]) == 1
    html = nativo.get(
        f"/vat/catalogos/subsectores/{datos.subsector.pk}/eliminar/"
    ).content.decode()
    borrar = api.get(f"{ROOT}subsectores/{datos.subsector.pk}/eliminar/").json()
    assert (borrar["nombre"], borrar["sector"]) == ("Metalurgia", "Industria")
    assert "Metalurgia</strong> (Industria)" in html


def test_form_get_projects_the_native_fields(datos):
    data = _client("add_sector").get(f"{ROOT}sectores/nuevo/").json()
    assert data["editing"] is False and data["messages"] == []
    assert [f["name"] for f in data["fields"]] == ["nombre", "descripcion"]
    assert data["urls"]["list"] == "/vat/catalogos/sectores/"
    sub = _client("add_subsector").get(f"{ROOT}subsectores/nuevo/").json()
    assert [f["name"] for f in sub["fields"]] == ["sector", "nombre", "descripcion"]
    assert "select2" in sub["fields"][0]["attrs"]["class"]
    mod = (
        _client("change_modalidadcursada")
        .get(f"{ROOT}modalidades-cursado/{datos.modalidad.pk}/editar/")
        .json()
    )
    assert mod["editing"] is True
    assert mod["page"]["page_title"] == "Editar Modalidad de Cursado"
    assert (
        mod["urls"]["cancel"]
        == f"/vat/catalogos/modalidades-cursado/{datos.modalidad.pk}/"
    )
    tit = _client("add_tituloreferencia").get(f"{ROOT}titulos-referencia/nuevo/").json()
    assert [f["name"] for f in tit["fields"]] == [
        "plan_estudio",
        "nombre",
        "codigo_referencia",
        "descripcion",
        "activo",
    ]


def test_create_persists_and_queues_the_native_message(datos):
    cliente = _client("add_sector", "view_sector")
    respuesta = cliente.post(f"{ROOT}sectores/nuevo/", {"nombre": "Servicios"})
    assert respuesta.status_code == 200
    nuevo = Sector.objects.get(nombre="Servicios")
    assert respuesta.json() == {
        "ok": True,
        "redirect": f"/vat/catalogos/sectores/{nuevo.pk}/",
    }
    assert [
        (m["message"], m["level"])
        for m in cliente.get(f"{ROOT}sectores/").json()["messages"]
    ] == [("Sector creado correctamente.", "success")]
    tit = _client("add_tituloreferencia").post(
        f"{ROOT}titulos-referencia/nuevo/",
        {"nombre": "Soldador", "plan_estudio": "", "activo": "on"},
    )
    assert tit.status_code == 200
    creado = TituloReferencia.objects.get(nombre="Soldador")
    assert creado.activo is True and creado.plan_estudio is None
    sub = _client("add_subsector").post(
        f"{ROOT}subsectores/nuevo/", {"sector": datos.sector.pk, "nombre": "Textil"}
    )
    assert sub.status_code == 200 and Subsector.objects.filter(nombre="Textil").exists()
    mod = _client("add_modalidadcursada").post(
        f"{ROOT}modalidades-cursado/nueva/", {"nombre": "Virtual"}
    )
    assert mod.status_code == 200
    assert ModalidadCursada.objects.get(nombre="Virtual").activo is False


def test_invalid_post_is_400_with_errors_and_writes_nothing(datos):
    antes = Sector.objects.count()
    respuesta = _client("add_sector").post(f"{ROOT}sectores/nuevo/", {"nombre": ""})
    assert respuesta.status_code == 400
    assert respuesta.json()["fields"][0]["errors"]
    assert Sector.objects.count() == antes
    rechazo = _client("change_subsector").post(
        f"{ROOT}subsectores/{datos.subsector.pk}/editar/",
        {"sector": datos.sector.pk, "nombre": ""},
    )
    assert rechazo.status_code == 400
    datos.subsector.refresh_from_db()
    assert datos.subsector.nombre == "Metalurgia"


def test_update_and_delete_follow_the_native_views(datos):
    editor = _client("change_modalidadcursada")
    url = f"{ROOT}modalidades-cursado/{datos.modalidad.pk}/editar/"
    ok = editor.post(url, {"nombre": "Distancia"})
    assert ok.status_code == 200
    datos.modalidad.refresh_from_db()
    assert (datos.modalidad.nombre, datos.modalidad.activo) == ("Distancia", False)
    borrador = _client("delete_subsector", "view_subsector")
    assert borrador.post(f"{ROOT}subsectores/999999/eliminar/").status_code == 404
    assert Subsector.objects.count() == 1
    assert borrador.post(
        f"{ROOT}subsectores/{datos.subsector.pk}/eliminar/"
    ).json() == {
        "ok": True,
        "redirect": "/vat/catalogos/subsectores/",
    }
    assert not Subsector.objects.filter(pk=datos.subsector.pk).exists()
    titulo = _client("delete_tituloreferencia")
    assert (
        titulo.post(f"{ROOT}titulos-referencia/{datos.titulo.pk}/eliminar/").status_code
        == 200
    )
    assert not TituloReferencia.objects.filter(pk=datos.titulo.pk).exists()


def test_rejected_writes_change_nothing(datos):
    cuerpo = {"nombre": "Cambiado"}
    for slug, _nuevo, modelo, _clase in CATALOGOS:
        pk = _objeto(datos, modelo).pk
        assert (
            _client(f"change_{modelo}", csrf=True)
            .post(f"{ROOT}{slug}/{pk}/editar/", cuerpo)
            .status_code
            == 403
        )
        assert (
            _client(f"view_{modelo}")
            .post(f"{ROOT}{slug}/{pk}/editar/", cuerpo)
            .status_code
            == 403
        )
        assert (
            _client(f"delete_{modelo}", csrf=True)
            .post(f"{ROOT}{slug}/{pk}/eliminar/")
            .status_code
            == 403
        )
        assert (
            _client(f"view_{modelo}").post(f"{ROOT}{slug}/{pk}/eliminar/").status_code
            == 403
        )
        assert APIClient().post(f"{ROOT}{slug}/{pk}/eliminar/").status_code == 401
    datos.sector.refresh_from_db()
    assert datos.sector.nombre == "Industria"
    assert Sector.objects.count() == Subsector.objects.count() == 1
    assert ModalidadCursada.objects.count() == TituloReferencia.objects.count() == 1


@pytest.fixture(name="preview")
def preview_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    (tmp_path / "assets" / "app-1.js").write_text("console.log(1);", encoding="utf-8")
    module = types.ModuleType("vat_catalogos_preview_test_urls")
    module.urlpatterns = catalogos_preview_patterns(tmp_path) + list(monolith_patterns)
    with override_settings(ROOT_URLCONF=module):
        yield


@pytest.mark.usefixtures("preview")
def test_entries_serve_the_frozen_index_behind_the_native_guards(datos):
    for slug, nuevo, modelo, _clase in CATALOGOS:
        pk = _objeto(datos, modelo).pk
        for url, code in [
            (f"/vat/catalogos/{slug}/", "view"),
            (f"/vat/catalogos/{slug}/{nuevo}/", "add"),
            (f"/vat/catalogos/{slug}/{pk}/", "view"),
            (f"/vat/catalogos/{slug}/{pk}/editar/", "change"),
            (f"/vat/catalogos/{slug}/{pk}/eliminar/", "delete"),
        ]:
            response = _client(f"{code}_{modelo}").get(url)
            assert response.status_code == 200, url
            body = response.content.decode()
            assert (
                '/vat/react/assets/app-1.js"' in body
                and "/v2/sisoc/assets/" not in body
            )
            assert "no-store" in response["Cache-Control"]
            assert Client().get(url).status_code == 403
            otro = "view" if code != "view" else "add"
            assert _client(f"{otro}_{modelo}").get(url).status_code == 403
        assert (
            _client(f"view_{modelo}").get(f"/vat/catalogos/{slug}/999999/").status_code
            == 404
        )
        assert (
            _client(f"view_{modelo}")
            .get(f"/vat/catalogos/{slug}/", {"page": 9})
            .status_code
            == 404
        )


def test_native_title_delete_page_cannot_render_so_the_api_uses_the_view_context(datos):
    api = _client("delete_tituloreferencia")
    nativo = Client(raise_request_exception=False)
    nativo.force_login(api.user)
    assert (
        nativo.get(
            f"/vat/catalogos/titulos-referencia/{datos.titulo.pk}/eliminar/"
        ).status_code
        == 500
    )
    borrar = api.get(f"{ROOT}titulos-referencia/{datos.titulo.pk}/eliminar/").json()
    assert borrar["nombre"] == "Electricista"
