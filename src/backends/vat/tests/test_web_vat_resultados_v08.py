"""V08.01/V08.02: web API de resultados de evaluación (``/api/web/vat/resultados-evaluacion/``). Datos sintéticos."""

import itertools
from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client
from rest_framework.test import APIClient

from ciudadanos.models import Ciudadano
from core.models import Programa, Provincia
from VAT.models import (
    Centro,
    Comision,
    Evaluacion,
    Inscripcion,
    ModalidadCursada,
    OfertaInstitucional,
    PlanVersionCurricular,
    ResultadoEvaluacion,
    Sector,
)

pytestmark = pytest.mark.django_db

ROOT = "/api/web/vat/resultados-evaluacion/"
_COUNTER = itertools.count()


def _client(*codes, csrf=False):
    user = get_user_model().objects.create_user(f"u{next(_COUNTER)}")
    user.user_permissions.add(
        *Permission.objects.filter(content_type__app_label="VAT", codename__in=codes)
    )
    client = APIClient(enforce_csrf_checks=csrf)
    client.force_login(user)
    client.user = user
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


@pytest.fixture(name="inscripcion")
def inscripcion_fixture(comision):
    ciudadano = Ciudadano.objects.create(
        nombre="Ana",
        apellido="Prueba",
        documento=30111222,
        fecha_nacimiento=date(1990, 1, 1),
    )
    return Inscripcion.objects.create(ciudadano=ciudadano, comision=comision)


@pytest.fixture(name="resultado")
def resultado_fixture(evaluacion, inscripcion):
    return ResultadoEvaluacion.objects.create(
        evaluacion=evaluacion,
        inscripcion=inscripcion,
        calificacion=Decimal("7.5"),
        aprobo=True,
        observaciones="Obs <b>x</b>",
        registrado_por=get_user_model().objects.create_user("registrador"),
    )


def _datos(ev, ins, **extra):
    return {
        "evaluacion": ev.pk,
        "inscripcion": ins.pk,
        "calificacion": "8.25",
        "aprobo": "True",
        "observaciones": "Texto",
        **extra,
    }


def test_access_follows_each_native_route_rule(resultado):
    urls = {
        ROOT: ("view", "get"),
        f"{ROOT}{resultado.pk}/": ("view", "get"),
        f"{ROOT}nuevo/": ("add", "get"),
        f"{ROOT}{resultado.pk}/editar/": ("change", "get"),
        f"{ROOT}{resultado.pk}/eliminar/": ("delete", "get"),
    }
    for url, (accion, _metodo) in urls.items():
        assert APIClient().get(url).status_code == 401
        assert _client("view_evaluacion").get(url).status_code == 403
        otras = {"view", "add", "change", "delete"} - {accion}
        for otra in otras:
            assert _client(f"{otra}_resultadoevaluacion").get(url).status_code == 403
        assert _client(f"{accion}_resultadoevaluacion").get(url).status_code == 200
    assert _client("view_resultadoevaluacion").get(f"{ROOT}999999/").status_code == 404
    assert (
        _client("change_resultadoevaluacion").get(f"{ROOT}999999/editar/").status_code
        == 404
    )


def test_list_projects_the_native_rows_and_filters(resultado, evaluacion, inscripcion):
    otro = ResultadoEvaluacion.objects.create(
        evaluacion=Evaluacion.objects.create(
            comision=evaluacion.comision,
            tipo="final",
            nombre="Final 1",
            fecha=date(2026, 6, 2),
        ),
        inscripcion=inscripcion,
        calificacion=Decimal("0"),
        aprobo=None,
        registrado_por=resultado.registrado_por,
    )
    client = _client("view_resultadoevaluacion", "change_resultadoevaluacion")
    data = client.get(ROOT).json()
    assert data["permisos"] == {"editar": True, "eliminar": False}
    assert data["urls"] == {
        "list": "/vat/resultados-evaluacion/",
        "create": "/vat/resultados-evaluacion/nuevo/",
    }
    por_id = {r["id"]: r for r in data["results"]}
    assert por_id[resultado.pk]["calificacion"] == "7,50"
    assert por_id[resultado.pk]["aprobo"] is True
    assert por_id[resultado.pk]["persona"] == "Ana Prueba"
    assert por_id[resultado.pk]["evaluacion"] == "Parcial 1"
    assert por_id[otro.pk]["calificacion"] == "—"
    assert por_id[otro.pk]["aprobo"] is None
    assert por_id[resultado.pk]["delete_url"] == (
        f"/vat/resultados-evaluacion/{resultado.pk}/eliminar/"
    )
    assert [
        r["id"] for r in client.get(ROOT, {"busqueda": "Final"}).json()["results"]
    ] == [otro.pk]
    assert client.get(ROOT, {"busqueda": "Inexistente"}).json()["results"] == []
    assert client.get(ROOT, {"calificacion": "7.50"}).json()["page"]["count"] == 1
    assert client.get(ROOT, {"page": 9}).status_code == 404


def test_detail_projects_the_native_context(resultado):
    data = _client("view_resultadoevaluacion").get(f"{ROOT}{resultado.pk}/").json()
    assert data["persona"] == "Ana Prueba"
    assert data["comision"] == "COM-001"
    assert data["tipo_label"] == "Parcial"
    assert data["calificacion"] == "7,50"
    assert data["registrado_por"] == "registrador"
    assert data["observaciones"] == "Obs <b>x</b>"
    assert data["urls"]["update"] == (
        f"/vat/resultados-evaluacion/{resultado.pk}/editar/"
    )


def test_form_projects_the_native_widgets(resultado):
    data = (
        _client("change_resultadoevaluacion")
        .get(f"{ROOT}{resultado.pk}/editar/")
        .json()
    )
    assert data["editing"] is True
    por_nombre = {f["name"]: f for f in data["fields"]}
    assert list(por_nombre) == [
        "evaluacion",
        "inscripcion",
        "calificacion",
        "aprobo",
        "observaciones",
    ]
    assert por_nombre["evaluacion"]["tag"] == "select"
    assert por_nombre["evaluacion"]["value"] == str(resultado.evaluacion_id)
    assert "select2" in por_nombre["inscripcion"]["attrs"]["class"]
    assert por_nombre["calificacion"]["attrs"]["step"] == "0.01"
    assert por_nombre["calificacion"]["value"] == "7.50"
    aprobo = por_nombre["aprobo"]
    assert aprobo["tag"] == "select"
    assert aprobo["value"] == "True"
    assert [(o["value"], o["label"]) for o in aprobo["choices"]] == [
        ("", "---"),
        ("True", "Sí"),
        ("False", "No"),
    ]
    assert por_nombre["observaciones"]["attrs"]["rows"] == "3"
    vacio = _client("add_resultadoevaluacion").get(f"{ROOT}nuevo/").json()
    assert vacio["editing"] is False
    assert vacio["urls"] == {"list": "/vat/resultados-evaluacion/"}


def test_create_persists_registrado_por_and_queues_the_native_message(
    evaluacion, inscripcion
):
    client = _client("add_resultadoevaluacion", "view_resultadoevaluacion")
    respuesta = client.post(
        f"{ROOT}nuevo/", _datos(evaluacion, inscripcion), format="multipart"
    )
    assert respuesta.status_code == 200
    assert respuesta.json() == {"ok": True, "redirect": "/vat/resultados-evaluacion/"}
    r = ResultadoEvaluacion.objects.get()
    assert (r.calificacion, r.aprobo, r.observaciones) == (
        Decimal("8.25"),
        True,
        "Texto",
    )
    assert (r.evaluacion_id, r.inscripcion_id) == (evaluacion.pk, inscripcion.pk)
    assert r.registrado_por_id == client.user.pk
    assert client.get(ROOT).json()["messages"] == [
        {"message": "Resultado de evaluación creado exitosamente.", "level": "success"}
    ]


def test_create_rejects_invalid_data_with_the_bound_form_and_saves_nothing(
    evaluacion, inscripcion
):
    client = _client("add_resultadoevaluacion")
    respuesta = client.post(
        f"{ROOT}nuevo/",
        {**_datos(evaluacion, inscripcion), "inscripcion": "", "calificacion": "x"},
        format="multipart",
    )
    assert respuesta.status_code == 400
    campos = {f["name"]: f for f in respuesta.json()["fields"]}
    assert len(campos["inscripcion"]["errors"]) == 1
    assert len(campos["calificacion"]["errors"]) == 1
    assert campos["aprobo"]["value"] == "True"
    assert ResultadoEvaluacion.objects.count() == 0


def test_create_rejects_a_duplicated_evaluacion_and_inscripcion(
    resultado, evaluacion, inscripcion
):
    client = _client("add_resultadoevaluacion")
    respuesta = client.post(
        f"{ROOT}nuevo/", _datos(evaluacion, inscripcion), format="multipart"
    )
    assert respuesta.status_code == 400
    assert ResultadoEvaluacion.objects.count() == 1


def test_update_persists_and_keeps_the_object_on_invalid_data(
    resultado, evaluacion, inscripcion
):
    client = _client("change_resultadoevaluacion", "view_resultadoevaluacion")
    url = f"{ROOT}{resultado.pk}/editar/"
    assert (
        client.post(
            url,
            {**_datos(evaluacion, inscripcion), "evaluacion": ""},
            format="multipart",
        ).status_code
        == 400
    )
    resultado.refresh_from_db()
    assert resultado.calificacion == Decimal("7.50")
    respuesta = client.post(
        url,
        _datos(evaluacion, inscripcion, calificacion="3", aprobo="False"),
        format="multipart",
    )
    assert respuesta.json() == {"ok": True, "redirect": "/vat/resultados-evaluacion/"}
    resultado.refresh_from_db()
    assert (resultado.calificacion, resultado.aprobo) == (Decimal("3.00"), False)
    assert resultado.registrado_por_id == client.user.pk
    assert client.get(ROOT).json()["messages"] == [
        {
            "message": "Resultado de evaluación actualizado exitosamente.",
            "level": "success",
        }
    ]
    pendiente = client.post(
        url,
        _datos(evaluacion, inscripcion, aprobo="", calificacion=""),
        format="multipart",
    )
    assert pendiente.status_code == 200
    resultado.refresh_from_db()
    assert (resultado.calificacion, resultado.aprobo) == (None, None)


def test_delete_shows_the_confirmation_and_soft_deletes_through_the_native_view(
    resultado,
):
    client = _client("delete_resultadoevaluacion", "view_resultadoevaluacion")
    url = f"{ROOT}{resultado.pk}/eliminar/"
    assert client.get(url).json() == {
        "persona": "Ana Prueba",
        "evaluacion": "Parcial 1",
        "calificacion": "7,50",
        "urls": {"detail": f"/vat/resultados-evaluacion/{resultado.pk}/"},
    }
    assert ResultadoEvaluacion.objects.count() == 1
    assert client.post(url).json() == {
        "ok": True,
        "redirect": "/vat/resultados-evaluacion/",
    }
    assert ResultadoEvaluacion.objects.count() == 0
    assert ResultadoEvaluacion.all_objects.filter(pk=resultado.pk).exists()
    assert client.get(ROOT).json()["messages"] == [
        {"message": "Baja lógica realizada correctamente.", "level": "success"}
    ]
    assert client.post(url).status_code == 404


def test_writes_require_csrf_and_other_permissions_cannot_write(
    resultado, evaluacion, inscripcion
):
    todos = (
        "add_resultadoevaluacion",
        "change_resultadoevaluacion",
        "delete_resultadoevaluacion",
    )
    sin_csrf = _client(*todos, csrf=True)
    datos = _datos(evaluacion, inscripcion)
    assert sin_csrf.post(f"{ROOT}nuevo/", datos, format="multipart").status_code == 403
    assert sin_csrf.post(f"{ROOT}{resultado.pk}/eliminar/").status_code == 403
    lector = _client("view_resultadoevaluacion")
    assert lector.post(f"{ROOT}nuevo/", datos, format="multipart").status_code == 403
    assert lector.post(f"{ROOT}{resultado.pk}/eliminar/").status_code == 403
    assert (
        lector.post(
            f"{ROOT}{resultado.pk}/editar/", datos, format="multipart"
        ).status_code
        == 403
    )
    assert ResultadoEvaluacion.objects.count() == 1
    resultado.refresh_from_db()
    assert resultado.calificacion == Decimal("7.50")


def test_native_and_api_writers_leave_the_same_row(evaluacion, inscripcion):
    user = get_user_model().objects.create_superuser("super", password="x")
    nativo = Client()
    nativo.force_login(user)
    nativo.post("/vat/resultados-evaluacion/nuevo/", _datos(evaluacion, inscripcion))
    via_api = APIClient()
    via_api.force_login(user)
    otra = Evaluacion.objects.create(
        comision=evaluacion.comision,
        tipo="final",
        nombre="Final",
        fecha=date(2026, 6, 1),
    )
    via_api.post(f"{ROOT}nuevo/", _datos(otra, inscripcion), format="multipart")
    a, b = ResultadoEvaluacion.objects.order_by("pk")
    campos = (
        "inscripcion_id",
        "calificacion",
        "aprobo",
        "observaciones",
        "registrado_por_id",
    )
    assert [getattr(a, c) for c in campos] == [getattr(b, c) for c in campos]
