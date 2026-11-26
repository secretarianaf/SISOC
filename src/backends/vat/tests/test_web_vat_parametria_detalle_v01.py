"""V01.01/V01.03: detalle de parametría y asignaciones por la API web. Datos sintéticos."""

import itertools
from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client
from rest_framework.test import APIClient

from ciudadanos.models import Ciudadano
from core.models import Programa
from VAT.models import Voucher, VoucherParametria
from VAT.services.voucher_service.impl import VoucherService

pytestmark = pytest.mark.django_db

ROOT = "/api/web/vat/vouchers/parametrias/"
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


def _ciudadano(n):
    return Ciudadano.objects.create(
        nombre=f"Nombre{n}",
        apellido=f"Apellido{n}",
        documento=30500000 + n,
        fecha_nacimiento=date(1990, 1, 1),
    )


@pytest.fixture(name="parametria")
def parametria_fixture():
    creador = get_user_model().objects.create_user("creador")
    return VoucherParametria.objects.create(
        nombre="Parametria <1>",
        descripcion="Descripcion sintetica",
        programa=Programa.objects.create(nombre="Programa Sintetico"),
        cantidad_inicial=10,
        fecha_vencimiento=date(2027, 3, 1),
        renovacion_mensual=True,
        cantidad_renovacion=4,
        renovacion_tipo="reinicia",
        creado_por=creador,
    )


def _asignar(parametria, n, estado="activo", disponible=None):
    voucher = VoucherService.crear_voucher(
        ciudadano_id=_ciudadano(n).id,
        programa_id=parametria.programa_id,
        cantidad=10,
        fecha_vencimiento=parametria.fecha_vencimiento,
        usuario=get_user_model().objects.get(username="creador"),
        parametria=parametria,
    )
    Voucher.objects.filter(pk=voucher.pk).update(
        estado=estado,
        cantidad_disponible=10 if disponible is None else disponible,
        cantidad_usada=0 if disponible is None else 10 - disponible,
    )
    return voucher


def test_access_follows_the_native_route_rules(parametria):
    detalle = f"{ROOT}{parametria.pk}/"
    assert APIClient().get(detalle).status_code == 401
    assert _client("add_voucher").get(detalle).status_code == 403
    assert _client("view_voucher").get(detalle).status_code == 200
    assert _client("view_voucher").get(f"{ROOT}999999/").status_code == 404
    for sufijo in ("asignar/", "asignar-masivo/"):
        assert APIClient().post(f"{detalle}{sufijo}", {}).status_code == 401
        assert _client("view_voucher").post(f"{detalle}{sufijo}", {}).status_code == 403
        assert _client("add_voucher").get(f"{detalle}{sufijo}").status_code == 405
    assert _client("add_voucher").post(f"{ROOT}999999/asignar/", {}).status_code == 404


def test_detail_projects_header_stats_rows_and_metrics(parametria):
    _asignar(parametria, 1)
    _asignar(parametria, 2, "agotado", 0)
    _asignar(parametria, 3, "vencido", 4)
    data = _client("view_voucher", "add_voucher").get(f"{ROOT}{parametria.pk}/").json()
    assert (data["nombre"], data["descripcion"], data["vencimiento"]) == (
        "Parametria <1>",
        "Descripcion sintetica",
        "01/03/2027",
    )
    assert (data["renovacion_tipo_label"], data["cantidad_renovacion"]) == (
        "Reiniciar al valor configurado",
        4,
    )
    assert (data["total"], data["activos"], data["agotados"], data["vencidos"]) == (
        3,
        1,
        1,
        1,
    )
    assert (data["creditos_emitidos"], data["creditos_usados"]) == (30, 16)
    assert (data["pct_uso"], data["pct_activos"]) == (53, 33)
    assert data["pct_agotados"] == "33"
    assert data["permisos"] == {"asignar": True}
    por_dni = {v["documento"]: v for v in data["vouchers"]}
    assert por_dni["30500002"]["barra"] == "bg-danger"
    assert por_dni["30500003"]["barra"] == "bg-warning"
    assert por_dni["30500001"]["barra"] == "bg-success"
    assert por_dni["30500002"]["badge"] == "bg-warning text-dark"
    assert por_dni["30500003"]["ancho"] == "40"
    assert len(data["ultimas"]) == 3
    assert data["page"]["shown"] is True
    assert (
        data["urls"]["asignar"] == f"/vat/vouchers/parametrias/{parametria.pk}/asignar/"
    )
    sin_alta = _client("view_voucher").get(f"{ROOT}{parametria.pk}/").json()
    assert sin_alta["permisos"] == {"asignar": False}


def test_detail_filters_and_paginates_like_the_native_view(parametria, monkeypatch):
    for n in range(1, 4):
        _asignar(parametria, n)
    monkeypatch.setattr(
        "VAT.views.voucher_parametria.VoucherParametriaDetailView.vouchers_per_page", 2
    )
    client = _client("view_voucher")
    data = client.get(
        f"{ROOT}{parametria.pk}/", {"vouchers_page": "2", "x": "y z"}
    ).json()
    assert data["page"]["number"] == 2
    assert data["page"]["is_paginated"] is True
    assert data["page"]["query_prefix"] == "x=y%20z&"
    assert len(data["vouchers"]) == 1
    filtrado = client.get(f"{ROOT}{parametria.pk}/", {"busqueda": "Apellido2"}).json()
    assert [v["documento"] for v in filtrado["vouchers"]] == ["30500002"]
    assert filtrado["search_query"] == "Apellido2"
    assert filtrado["vouchers_total_filtrados"] == 1
    assert filtrado["page"]["query_prefix"] == "busqueda=Apellido2&"
    vacio = client.get(f"{ROOT}{parametria.pk}/", {"busqueda": "zzz"}).json()
    assert vacio["vouchers"] == [] and vacio["page"]["shown"] is False


def test_empty_parametria_has_no_metrics(parametria):
    data = _client("view_voucher").get(f"{ROOT}{parametria.pk}/").json()
    assert (data["total"], data["vouchers"], data["ultimas"]) == (0, [], [])


def test_asignar_persists_through_the_native_view_and_queues_the_message(parametria):
    ciudadano = _ciudadano(1)
    client = _client("add_voucher", "view_voucher")
    url = f"{ROOT}{parametria.pk}/asignar/"
    respuesta = client.post(url, {"dni": str(ciudadano.documento)}, format="multipart")
    assert respuesta.json() == {
        "ok": True,
        "redirect": f"/vat/vouchers/parametrias/{parametria.pk}/",
    }
    voucher = Voucher.objects.get()
    assert (voucher.ciudadano_id, voucher.parametria_id, voucher.cantidad_inicial) == (
        ciudadano.pk,
        parametria.pk,
        10,
    )
    detalle = client.get(f"{ROOT}{parametria.pk}/").json()
    assert detalle["messages"] == [
        {
            "message": "Voucher creado y asignado a Nombre1 Apellido1.",
            "level": "success",
        }
    ]
    client.post(url, {"dni": str(ciudadano.documento)}, format="multipart")
    assert Voucher.objects.count() == 1
    assert (
        client.get(f"{ROOT}{parametria.pk}/").json()["messages"][0]["level"]
        == "warning"
    )


def test_asignar_rejections_save_nothing_and_keep_the_native_messages(parametria):
    client = _client("add_voucher", "view_voucher")
    url = f"{ROOT}{parametria.pk}/asignar/"
    assert client.post(url, {"dni": ""}, format="multipart").json()["ok"] is True
    assert client.get(f"{ROOT}{parametria.pk}/").json()["messages"] == [
        {"message": "Ingresá un DNI.", "level": "error"}
    ]
    client.post(url, {"dni": "99999999"}, format="multipart")
    assert client.get(f"{ROOT}{parametria.pk}/").json()["messages"] == [
        {
            "message": "No se encontró ningún ciudadano con DNI 99999999.",
            "level": "error",
        }
    ]
    assert Voucher.objects.count() == 0


def test_asignar_masivo_counts_like_the_native_view_and_reactivates(parametria):
    reactivable = _asignar(parametria, 1, "agotado", 0)
    _asignar(parametria, 2)
    _ciudadano(3)
    client = _client("add_voucher", "view_voucher")
    url = f"{ROOT}{parametria.pk}/asignar-masivo/"
    dnis = "30500001, 30500002\n30500003;99999999"
    assert client.post(url, {"dnis": dnis}, format="multipart").json()["ok"] is True
    assert client.get(f"{ROOT}{parametria.pk}/").json()["messages"] == [
        {
            "message": "Asignación masiva completada: 1 creados, 1 reactivados, "
            "1 ya activos, 1 DNIs no encontrados.",
            "level": "success",
        }
    ]
    reactivable.refresh_from_db()
    assert (reactivable.estado, reactivable.cantidad_disponible) == ("activo", 4)
    assert Voucher.objects.count() == 3
    assert client.post(url, {"dnis": " "}, format="multipart").json()["ok"] is True
    assert client.get(f"{ROOT}{parametria.pk}/").json()["messages"] == [
        {"message": "No ingresaste ningún DNI.", "level": "error"}
    ]
    demasiados = ",".join(str(10_000_000 + n) for n in range(501))
    client.post(url, {"dnis": demasiados}, format="multipart")
    assert client.get(f"{ROOT}{parametria.pk}/").json()["messages"] == [
        {"message": "Máximo 500 DNIs por operación.", "level": "error"}
    ]
    assert Voucher.objects.count() == 3


def test_writes_require_csrf_and_view_only_users_cannot_assign(parametria):
    ciudadano = _ciudadano(1)
    datos = {"dni": str(ciudadano.documento)}
    sin_csrf = _client("add_voucher", csrf=True)
    assert (
        sin_csrf.post(
            f"{ROOT}{parametria.pk}/asignar/", datos, format="multipart"
        ).status_code
        == 403
    )
    lector = _client("view_voucher", "change_voucher")
    assert (
        lector.post(
            f"{ROOT}{parametria.pk}/asignar/", datos, format="multipart"
        ).status_code
        == 403
    )
    assert Voucher.objects.count() == 0


def test_native_and_api_assignments_leave_the_same_voucher(parametria):
    a, b = _ciudadano(1), _ciudadano(2)
    user = get_user_model().objects.create_superuser("super", password="x")
    nativo = Client()
    nativo.force_login(user)
    nativo.post(
        f"/vat/vouchers/parametrias/{parametria.pk}/asignar/", {"dni": str(a.documento)}
    )
    via_api = APIClient()
    via_api.force_login(user)
    via_api.post(
        f"{ROOT}{parametria.pk}/asignar/", {"dni": str(b.documento)}, format="multipart"
    )
    uno, dos = Voucher.objects.order_by("pk")
    campos = (
        "programa_id",
        "parametria_id",
        "cantidad_inicial",
        "cantidad_disponible",
        "fecha_vencimiento",
        "estado",
    )
    assert [getattr(uno, c) for c in campos] == [getattr(dos, c) for c in campos]
