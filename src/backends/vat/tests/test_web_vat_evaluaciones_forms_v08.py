"""V08.02: alta, edición y baja de evaluaciones por la API web (vistas nativas). Datos sintéticos."""

import itertools
from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client
from rest_framework.test import APIClient

from core.models import Programa, Provincia
from VAT.models import (
    Centro,
    Comision,
    Evaluacion,
    ModalidadCursada,
    OfertaInstitucional,
    PlanVersionCurricular,
    Sector,
)

pytestmark = pytest.mark.django_db

ROOT = "/api/web/vat/evaluaciones/"
_COUNTER = itertools.count()


def _client(*codes, csrf=False):
    user = get_user_model().objects.create_user(f"u{next(_COUNTER)}")
    user.user_permissions.add(
        *Permission.objects.filter(content_type__app_label="VAT", codename__in=codes)
    )
    client = APIClient(enforce_csrf_checks=csrf)
    client.force_login(user)
    return client


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
        fecha_fin=date(2026, 12, 1),
        cupo=10,
    )


@pytest.fixture(name="evaluacion")
def evaluacion_fixture(comision):
    return Evaluacion.objects.create(
        comision=comision, tipo="parcial", nombre="Parcial 1", fecha=date(2026, 5, 2)
    )


def _datos(comision, **extra):
    return {
        "comision": comision.pk,
        "tipo": "final",
        "nombre": "Final sintetico",
        "fecha": "2026-06-01",
        "ponderacion": "40.00",
        "es_final": "on",
        "descripcion": "Texto",
        "observaciones": "",
        **extra,
    }


def test_access_follows_each_native_route_rule(comision, evaluacion):
    for url in (
        f"{ROOT}nueva/",
        f"{ROOT}{evaluacion.pk}/editar/",
        f"{ROOT}{evaluacion.pk}/eliminar/",
    ):
        assert APIClient().get(url).status_code == 401
        assert _client("view_evaluacion").get(url).status_code == 403
    assert _client("add_evaluacion").get(f"{ROOT}nueva/").status_code == 200
    editar = f"{ROOT}{evaluacion.pk}/editar/"
    assert _client("add_evaluacion").get(editar).status_code == 403
    assert _client("change_evaluacion").get(editar).status_code == 200
    eliminar = f"{ROOT}{evaluacion.pk}/eliminar/"
    assert _client("delete_evaluacion").get(eliminar).status_code == 200
    assert _client("change_evaluacion").get(f"{ROOT}999999/editar/").status_code == 404
    assert (
        _client("delete_evaluacion").get(f"{ROOT}999999/eliminar/").status_code == 404
    )


def test_form_projects_the_native_widgets(comision, evaluacion):
    data = _client("change_evaluacion").get(f"{ROOT}{evaluacion.pk}/editar/").json()
    assert data["editing"] is True
    por_nombre = {f["name"]: f for f in data["fields"]}
    assert list(por_nombre) == [
        "comision",
        "tipo",
        "nombre",
        "descripcion",
        "fecha",
        "es_final",
        "ponderacion",
        "observaciones",
    ]
    c = por_nombre["comision"]
    assert (c["tag"], c["id"], c["value"], c["label"]) == (
        "select",
        "id_comision",
        str(comision.pk),
        "Comisión",
    )
    assert "select2" in c["attrs"]["class"]
    assert c["attrs"]["data-placeholder"] == "Seleccionar comisión..."
    assert [o["value"] for o in c["choices"]] == ["", str(comision.pk)]
    assert por_nombre["descripcion"]["tag"] == "textarea"
    assert por_nombre["descripcion"]["attrs"]["rows"] == "3"
    assert por_nombre["fecha"]["attrs"]["type"] == "date"
    assert por_nombre["es_final"]["value"] is False
    assert "required" not in por_nombre["es_final"]["attrs"]
    assert por_nombre["nombre"]["attrs"]["required"] == "required"
    vacio = _client("add_evaluacion").get(f"{ROOT}nueva/").json()
    assert vacio["editing"] is False
    assert vacio["urls"] == {"list": "/vat/evaluaciones/"}


def test_create_persists_through_the_native_view_and_queues_its_message(comision):
    client = _client("add_evaluacion", "view_evaluacion")
    respuesta = client.post(f"{ROOT}nueva/", _datos(comision), format="multipart")
    assert respuesta.status_code == 200
    assert respuesta.json() == {"ok": True, "redirect": "/vat/evaluaciones/"}
    e = Evaluacion.objects.get()
    assert (e.nombre, e.tipo, e.es_final, str(e.ponderacion), e.fecha) == (
        "Final sintetico",
        "final",
        True,
        "40.00",
        date(2026, 6, 1),
    )
    assert e.comision_id == comision.pk
    assert client.get(ROOT).json()["messages"] == [
        {"message": "Evaluación creada exitosamente.", "level": "success"}
    ]


def test_create_rejects_invalid_data_with_the_bound_form_and_saves_nothing(comision):
    client = _client("add_evaluacion")
    respuesta = client.post(
        f"{ROOT}nueva/",
        _datos(comision, nombre="", ponderacion="x"),
        format="multipart",
    )
    assert respuesta.status_code == 400
    campos = {f["name"]: f for f in respuesta.json()["fields"]}
    assert len(campos["nombre"]["errors"]) == 1
    assert len(campos["ponderacion"]["errors"]) == 1
    assert campos["tipo"]["value"] == "final"
    assert Evaluacion.objects.count() == 0


def test_update_persists_and_keeps_the_object_on_invalid_data(comision, evaluacion):
    client = _client("change_evaluacion", "view_evaluacion")
    url = f"{ROOT}{evaluacion.pk}/editar/"
    assert (
        client.post(url, _datos(comision, nombre=""), format="multipart").status_code
        == 400
    )
    evaluacion.refresh_from_db()
    assert evaluacion.nombre == "Parcial 1"
    respuesta = client.post(
        url, _datos(comision, nombre="Parcial editado", es_final=""), format="multipart"
    )
    assert respuesta.json() == {"ok": True, "redirect": "/vat/evaluaciones/"}
    evaluacion.refresh_from_db()
    assert (evaluacion.nombre, evaluacion.tipo, evaluacion.es_final) == (
        "Parcial editado",
        "final",
        False,
    )
    assert client.get(ROOT).json()["messages"] == [
        {"message": "Evaluación actualizada exitosamente.", "level": "success"}
    ]


def test_delete_shows_the_confirmation_and_removes_the_row_physically(
    comision, evaluacion
):
    client = _client("delete_evaluacion")
    url = f"{ROOT}{evaluacion.pk}/eliminar/"
    assert client.get(url).json() == {
        "nombre": "Parcial 1",
        "tipo_label": "Parcial",
        "comision": "COM-001",
        "urls": {"detail": f"/vat/evaluaciones/{evaluacion.pk}/"},
    }
    assert Evaluacion.objects.count() == 1
    assert client.post(url).json() == {"ok": True, "redirect": "/vat/evaluaciones/"}
    assert Evaluacion.objects.count() == 0
    assert client.post(url).status_code == 404


def test_writes_require_csrf_and_other_permissions_cannot_write(comision, evaluacion):
    sin_csrf = _client(
        "add_evaluacion", "change_evaluacion", "delete_evaluacion", csrf=True
    )
    assert (
        sin_csrf.post(f"{ROOT}nueva/", _datos(comision), format="multipart").status_code
        == 403
    )
    assert sin_csrf.post(f"{ROOT}{evaluacion.pk}/eliminar/").status_code == 403
    lector = _client("view_evaluacion")
    assert (
        lector.post(f"{ROOT}nueva/", _datos(comision), format="multipart").status_code
        == 403
    )
    assert lector.post(f"{ROOT}{evaluacion.pk}/eliminar/").status_code == 403
    assert Evaluacion.objects.count() == 1


def test_native_and_api_writers_leave_the_same_row(comision):
    user = get_user_model().objects.create_superuser("super", password="x")
    nativo = Client()
    nativo.force_login(user)
    nativo.post("/vat/evaluaciones/nueva/", _datos(comision))
    via_api = APIClient()
    via_api.force_login(user)
    via_api.post(f"{ROOT}nueva/", _datos(comision), format="multipart")
    a, b = Evaluacion.objects.order_by("pk")
    campos = (
        "comision_id",
        "tipo",
        "nombre",
        "fecha",
        "es_final",
        "ponderacion",
        "descripcion",
    )
    assert [getattr(a, c) for c in campos] == [getattr(b, c) for c in campos]
