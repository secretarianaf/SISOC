"""V03.01: web API y vista previa de inscripciones a comisiones de oferta. Datos sintéticos."""

import itertools
import types
from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, override_settings
from rest_framework.test import APIClient

from ciudadanos.models import Ciudadano
from config.urls_all import urlpatterns as monolith_patterns
from core.models import Programa, Provincia
from VAT.models import (
    Centro,
    Comision,
    InscripcionOferta,
    ModalidadCursada,
    OfertaInstitucional,
    PlanVersionCurricular,
    Sector,
)
from VAT.web_preview_vat_inscripcion_oferta import inscripcion_oferta_preview_patterns

pytestmark = pytest.mark.django_db

ROOT = "/api/web/vat/inscripciones-oferta/"
_COUNTER = itertools.count()
INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
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


def _ciudadano(documento, apellido, nombre):
    return Ciudadano.objects.create(
        nombre=nombre,
        apellido=apellido,
        documento=documento,
        fecha_nacimiento=date(1990, 1, 1),
    )


@pytest.fixture(name="comision")
def comision_fixture():
    provincia = Provincia.objects.create(nombre="Buenos Aires")
    centro = Centro.objects.create(
        nombre="CFP 401", codigo="060144900", provincia=provincia
    )
    plan = PlanVersionCurricular.objects.create(
        nombre="Electricidad",
        provincia=provincia,
        sector=Sector.objects.create(nombre="Industria"),
        modalidad_cursada=ModalidadCursada.objects.create(nombre="Presencial"),
        horas_reloj=100,
    )
    oferta = OfertaInstitucional.objects.create(
        centro=centro,
        plan_curricular=plan,
        programa=Programa.objects.create(nombre="Programa Sintetico"),
        ciclo_lectivo=2026,
    )
    return Comision.objects.create(
        oferta=oferta,
        codigo_comision="COM-001",
        nombre="Comision Uno",
        fecha_inicio=date(2026, 3, 1),
        fecha_fin=date(2099, 12, 1),
        cupo=10,
    )


@pytest.fixture(name="inscripcion")
def inscripcion_fixture(comision):
    return InscripcionOferta.objects.create(
        oferta=comision,
        ciudadano=_ciudadano(30111222, "Prueba", "Ana"),
        estado="inscrito",
        inscrito_por=get_user_model().objects.create_user(
            "inscriptor", first_name="Ines", last_name="Inscriptora"
        ),
    )


def test_access_follows_each_native_route_rule(inscripcion):
    urls = {
        ROOT: "view",
        f"{ROOT}{inscripcion.pk}/": "view",
        f"{ROOT}nueva/": "add",
        f"{ROOT}{inscripcion.pk}/editar/": "change",
        f"{ROOT}{inscripcion.pk}/eliminar/": "delete",
    }
    for url, accion in urls.items():
        assert APIClient().get(url).status_code == 401
        for otra in {"view", "add", "change", "delete"} - {accion}:
            assert _client(f"{otra}_inscripcionoferta").get(url).status_code == 403
        assert _client(f"{accion}_inscripcionoferta").get(url).status_code == 200
    assert _client("view_inscripcionoferta").get(f"{ROOT}999999/").status_code == 404
    assert (
        _client("change_inscripcionoferta").get(f"{ROOT}999999/editar/").status_code
        == 404
    )


def test_list_projects_rows_filters_and_buttons(inscripcion, comision):
    otra = InscripcionOferta.objects.create(
        oferta=comision,
        ciudadano=_ciudadano(30999888, "Otro", "Beto"),
        estado="lista_espera",
        inscrito_por=inscripcion.inscrito_por,
    )
    data = (
        _client("view_inscripcionoferta", "change_inscripcionoferta").get(ROOT).json()
    )
    assert {r["id"] for r in data["results"]} == {inscripcion.pk, otra.pk}
    fila = next(r for r in data["results"] if r["id"] == inscripcion.pk)
    assert fila["ciudadano"] == inscripcion.ciudadano.nombre_completo
    assert fila["documento"] == "30111222"
    assert (fila["estado"], fila["estado_label"]) == ("inscrito", "Inscrito")
    assert data["permisos"] == {"editar": True, "eliminar": False}
    assert data["urls"]["create"] == "/vat/inscripciones-oferta/nueva/"
    cliente = _client("view_inscripcionoferta")
    assert [
        r["id"] for r in cliente.get(ROOT, {"estado": "lista_espera"}).json()["results"]
    ] == [otra.pk]
    assert [
        r["id"] for r in cliente.get(ROOT, {"busqueda": "Prueba"}).json()["results"]
    ] == [inscripcion.pk]
    assert cliente.get(ROOT, {"page": 9}).status_code == 404


def test_projected_texts_are_the_ones_the_native_pages_print(inscripcion):
    from django.utils.html import escape  # pylint: disable=import-outside-toplevel

    api = _client(
        "view_inscripcionoferta",
        "change_inscripcionoferta",
        "delete_inscripcionoferta",
        "add_inscripcionoferta",
    )
    nativo = Client()
    nativo.force_login(api.user)
    lista = api.get(ROOT).json()["results"][0]
    html = nativo.get("/vat/inscripciones-oferta/").content.decode()
    assert escape(lista["ciudadano"]) in html and escape(lista["fecha"]) in html
    detalle = api.get(f"{ROOT}{inscripcion.pk}/").json()
    html = nativo.get(f"/vat/inscripciones-oferta/{inscripcion.pk}/").content.decode()
    assert detalle["inscrito_por"] == "Ines Inscriptora"
    for clave in (
        "ciudadano",
        "inscrito_por",
        "fecha_inscripcion",
        "fecha_modificacion",
        "periodo",
        "horario",
    ):
        assert escape(detalle[clave]) in html, clave
    borrar = api.get(f"{ROOT}{inscripcion.pk}/eliminar/").json()
    html = nativo.get(
        f"/vat/inscripciones-oferta/{inscripcion.pk}/eliminar/"
    ).content.decode()
    assert (
        escape(borrar["ciudadano"]) in html and escape(borrar["estado_label"]) in html
    )


def test_form_get_projects_the_native_fields(inscripcion):
    data = _client("add_inscripcionoferta").get(f"{ROOT}nueva/").json()
    assert data["editing"] is False
    assert [f["name"] for f in data["fields"]] == ["oferta", "ciudadano", "estado"]
    assert [c["value"] for c in data["fields"][2]["choices"]] == [
        "inscrito",
        "lista_espera",
        "completado",
        "abandonado",
        "rechazado",
    ]
    assert data["non_field_errors"] == [] and data["messages"] == []
    assert (
        _client("change_inscripcionoferta")
        .get(f"{ROOT}{inscripcion.pk}/editar/")
        .json()["editing"]
        is True
    )


def test_create_persists_through_the_native_service_and_queues_the_message(comision):
    client = _client("add_inscripcionoferta", "view_inscripcionoferta")
    ciudadano = _ciudadano(30555444, "Nueva", "Nora")
    response = client.post(
        f"{ROOT}nueva/",
        {"oferta": comision.pk, "ciudadano": ciudadano.pk, "estado": "lista_espera"},
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True, "redirect": "/vat/inscripciones-oferta/"}
    creada = InscripcionOferta.objects.get()
    assert (
        creada.oferta_id,
        creada.ciudadano_id,
        creada.estado,
        creada.inscrito_por_id,
    ) == (
        comision.pk,
        ciudadano.pk,
        "lista_espera",
        client.user.pk,
    )
    mensajes = client.get(ROOT).json()["messages"]
    assert [(m["message"], m["level"]) for m in mensajes] == [
        ("Inscripción creada exitosamente.", "success")
    ]
    assert client.get(ROOT).json()["messages"] == []


def test_invalid_create_is_400_with_errors_and_queued_native_message(comision):
    client = _client("add_inscripcionoferta")
    response = client.post(
        f"{ROOT}nueva/", {"oferta": comision.pk, "ciudadano": "", "estado": "inscrito"}
    )
    assert response.status_code == 400
    body = response.json()
    assert body["fields"][1]["errors"]
    assert [m["message"] for m in body["messages"]] == [
        "Error al crear la inscripción."
    ]
    assert InscripcionOferta.objects.count() == 0


def test_service_rejection_shows_both_native_messages_and_writes_nothing(comision):
    comision.fecha_fin = date(2020, 1, 1)
    comision.save()
    client = _client("add_inscripcionoferta")
    ciudadano = _ciudadano(30555444, "Nueva", "Nora")
    response = client.post(
        f"{ROOT}nueva/",
        {"oferta": comision.pk, "ciudadano": ciudadano.pk, "estado": "inscrito"},
    )
    assert response.status_code == 400
    assert len(response.json()["messages"]) == 2
    assert response.json()["messages"][1]["message"] == "Error al crear la inscripción."
    assert InscripcionOferta.objects.count() == 0


def test_update_and_delete_follow_the_native_views(inscripcion, comision):
    editor = _client("change_inscripcionoferta")
    url = f"{ROOT}{inscripcion.pk}/editar/"
    # The native update form needs the same required fields; an empty post is rejected unchanged.
    rechazo = editor.post(
        url,
        {"oferta": "", "ciudadano": inscripcion.ciudadano_id, "estado": "completado"},
    )
    assert rechazo.status_code == 400
    inscripcion.refresh_from_db()
    assert inscripcion.estado == "inscrito"
    ok = editor.post(
        url,
        {
            "oferta": comision.pk,
            "ciudadano": inscripcion.ciudadano_id,
            "estado": "completado",
        },
    )
    assert (
        ok.status_code == 200 and ok.json()["redirect"] == "/vat/inscripciones-oferta/"
    )
    inscripcion.refresh_from_db()
    assert inscripcion.estado == "completado"
    borrador = _client("delete_inscripcionoferta", "view_inscripcionoferta")
    assert borrador.post(f"{ROOT}999999/eliminar/").status_code == 404
    assert InscripcionOferta.objects.count() == 1
    assert borrador.post(f"{ROOT}{inscripcion.pk}/eliminar/").json() == {
        "ok": True,
        "redirect": "/vat/inscripciones-oferta/",
    }
    assert InscripcionOferta.objects.count() == 0
    # Django 4+ ``DeleteView.post`` does not call the ``delete`` override that queues the message: none is queued.
    assert borrador.get(ROOT).json()["messages"] == []


def test_rejected_writes_change_nothing(inscripcion, comision):
    cuerpo = {
        "oferta": comision.pk,
        "ciudadano": inscripcion.ciudadano_id,
        "estado": "completado",
    }
    assert (
        _client("change_inscripcionoferta", csrf=True)
        .post(f"{ROOT}{inscripcion.pk}/editar/", cuerpo)
        .status_code
        == 403
    )
    assert (
        _client("view_inscripcionoferta")
        .post(f"{ROOT}{inscripcion.pk}/editar/", cuerpo)
        .status_code
        == 403
    )
    assert (
        _client("delete_inscripcionoferta", csrf=True)
        .post(f"{ROOT}{inscripcion.pk}/eliminar/")
        .status_code
        == 403
    )
    assert (
        _client("view_inscripcionoferta")
        .post(f"{ROOT}{inscripcion.pk}/eliminar/")
        .status_code
        == 403
    )
    assert APIClient().post(f"{ROOT}nueva/", cuerpo).status_code == 401
    inscripcion.refresh_from_db()
    assert inscripcion.estado == "inscrito" and InscripcionOferta.objects.count() == 1


@pytest.fixture(name="preview")
def preview_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    (tmp_path / "assets" / "app-1.js").write_text("console.log(1);", encoding="utf-8")
    module = types.ModuleType("vat_inscripcion_oferta_preview_test_urls")
    module.urlpatterns = inscripcion_oferta_preview_patterns(tmp_path) + list(
        monolith_patterns
    )
    with override_settings(ROOT_URLCONF=module):
        yield


@pytest.mark.usefixtures("preview")
def test_entries_serve_the_frozen_index_behind_the_native_guards(inscripcion):
    pk = inscripcion.pk
    for url, code in [
        ("/vat/inscripciones-oferta/", "view"),
        ("/vat/inscripciones-oferta/nueva/", "add"),
        (f"/vat/inscripciones-oferta/{pk}/", "view"),
        (f"/vat/inscripciones-oferta/{pk}/editar/", "change"),
        (f"/vat/inscripciones-oferta/{pk}/eliminar/", "delete"),
    ]:
        response = _client(f"{code}_inscripcionoferta").get(url)
        assert response.status_code == 200
        body = response.content.decode()
        assert '/vat/react/assets/app-1.js"' in body and "/v2/sisoc/assets/" not in body
        assert (
            "no-store" in response["Cache-Control"] and "csrftoken" in response.cookies
        )
        assert Client().get(url).status_code == 403
        otro = "view" if code != "view" else "add"
        assert _client(f"{otro}_inscripcionoferta").get(url).status_code == 403
    assert (
        _client("view_inscripcionoferta")
        .get("/vat/inscripciones-oferta/999999/")
        .status_code
        == 404
    )
    assert (
        _client("view_inscripcionoferta")
        .get("/vat/inscripciones-oferta/", {"page": 9})
        .status_code
        == 404
    )
