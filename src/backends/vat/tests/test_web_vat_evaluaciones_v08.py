"""V08.01: web API de evaluaciones (``/api/web/vat/evaluaciones/``). Datos sintéticos."""

from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
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


def _user(name, *codes):
    user = get_user_model().objects.create_user(name, password="x")
    user.user_permissions.add(
        *Permission.objects.filter(content_type__app_label="VAT", codename__in=codes)
    )
    return user


def _client(user):
    client = APIClient()
    client.force_login(user)
    return client


@pytest.fixture(name="evaluaciones")
def evaluaciones_fixture(comision):
    return [
        Evaluacion.objects.create(
            comision=comision,
            tipo=tipo,
            nombre=f"Evaluacion {n}",
            fecha=date(2026, 5, n),
            es_final=tipo == "final",
            descripcion="Detalle sintetico" if n == 1 else None,
            observaciones="Obs <b>x</b>" if n == 1 else "",
        )
        for n, tipo in ((1, "parcial"), (2, "final"))
    ]


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
        nombre="Comision & Uno",
        fecha_inicio=date(2026, 3, 1),
        fecha_fin=date(2026, 12, 1),
        cupo=10,
    )


def test_access_follows_the_native_route_rule(evaluaciones):
    assert APIClient().get(ROOT).status_code == 401
    assert _client(_user("sin")).get(ROOT).status_code == 403
    assert _client(_user("otro", "view_voucher")).get(ROOT).status_code == 403
    assert _client(_user("lector", "view_evaluacion")).get(ROOT).status_code == 200
    detalle = f"{ROOT}{evaluaciones[0].pk}/"
    assert _client(_user("sin2")).get(detalle).status_code == 403
    assert _client(_user("lector2", "view_evaluacion")).get(detalle).status_code == 200
    assert (
        _client(_user("lector3", "view_evaluacion")).get(f"{ROOT}999999/").status_code
        == 404
    )


def test_list_projects_rows_and_buttons_by_permission(evaluaciones):
    lector = _client(_user("lector", "view_evaluacion"))
    data = lector.get(ROOT).json()
    assert data["permisos"] == {"editar": False, "eliminar": False}
    por_nombre = {r["nombre"]: r for r in data["results"]}
    final = por_nombre["Evaluacion 2"]
    assert (final["comision"], final["tipo_label"], final["fecha"]) == (
        "COM-001",
        "Final",
        "02/05/2026",
    )
    assert final["es_final"] is True
    assert final["ponderacion"] == "100,00"
    assert final["detail_url"] == f"/vat/evaluaciones/{final['id']}/"
    assert final["update_url"] == f"/vat/evaluaciones/{final['id']}/editar/"
    gestor = _client(
        _user("gestor", "view_evaluacion", "change_evaluacion", "delete_evaluacion")
    )
    assert gestor.get(ROOT).json()["permisos"] == {"editar": True, "eliminar": True}
    assert data["urls"] == {
        "list": "/vat/evaluaciones/",
        "create": "/vat/evaluaciones/nueva/",
    }


def test_list_filters_and_paginates_like_the_native_view(evaluaciones):
    lector = _client(_user("lector", "view_evaluacion"))
    assert [
        r["nombre"] for r in lector.get(ROOT, {"busqueda": "COM-001"}).json()["results"]
    ] == [
        "Evaluacion 2",
        "Evaluacion 1",
    ]
    assert lector.get(ROOT, {"tipo": "final"}).json()["page"]["count"] == 1
    assert lector.get(ROOT, {"busqueda": "nada"}).json()["results"] == []
    assert lector.get(ROOT, {"page": 5}).status_code == 404


def test_detail_projects_the_native_labels_without_html_escaping(evaluaciones):
    lector = _client(_user("lector", "view_evaluacion"))
    primera, segunda = evaluaciones
    data = lector.get(f"{ROOT}{primera.pk}/").json()
    assert data["comision_nombre"] == "Comision & Uno"
    assert data["titulo"] == "COM-001 - Evaluacion 1 (Parcial)"
    assert data["descripcion"] == "Detalle sintetico"
    assert data["observaciones"] == "Obs <b>x</b>"
    assert data["ponderacion"] == "100,00"
    assert data["urls"]["update"] == f"/vat/evaluaciones/{primera.pk}/editar/"
    otra = lector.get(f"{ROOT}{segunda.pk}/").json()
    assert otra["descripcion"] == "—"
    assert otra["observaciones"] == ""
