"""V01.02: alta de voucher, alta masiva y alta de parametría por la API web. Datos sintéticos."""

import itertools
from datetime import date, timedelta

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

ROOT = "/api/web/vat/vouchers/"
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


@pytest.fixture(name="programa")
def programa_fixture():
    return Programa.objects.create(nombre="Programa Sintetico")


@pytest.fixture(name="ciudadano")
def ciudadano_fixture():
    return Ciudadano.objects.create(
        nombre="Ana",
        apellido="Prueba",
        documento=30111222,
        fecha_nacimiento=date(1990, 1, 1),
    )


def _vence(dias=60):
    return (date.today() + timedelta(days=dias)).isoformat()


def _voucher(ciudadano, programa, **extra):
    return {
        "ciudadano": ciudadano.pk,
        "programa": programa.pk,
        "cantidad_inicial": "10",
        "fecha_vencimiento": _vence(),
        **extra,
    }


def _parametria(programa, **extra):
    return {
        "nombre": "Parametria sintetica",
        "descripcion": "Texto",
        "programa": programa.pk,
        "cantidad_inicial": "8",
        "fecha_vencimiento": _vence(),
        "renovacion_mensual": "on",
        "cantidad_renovacion": "3",
        "renovacion_tipo": "reinicia",
        "inscripcion_unica_activa": "on",
        **extra,
    }


def test_access_requires_add_voucher_on_the_three_routes():
    for url in (
        f"{ROOT}asignar/",
        f"{ROOT}asignar-masivo/",
        f"{ROOT}parametrias/nueva/",
    ):
        assert APIClient().get(url).status_code == 401
        assert _client("view_voucher", "change_voucher").get(url).status_code == 403
        assert _client("add_voucher").get(url).status_code == 200


def test_voucher_form_projects_the_native_widgets_and_the_initial_citizen(
    ciudadano, programa
):
    client = _client("add_voucher")
    data = client.get(f"{ROOT}asignar/", {"ciudadano": ciudadano.pk}).json()
    assert data["titulo"] == "Asignar Voucher"
    assert data["urls"] == {"list": "/vat/vouchers/"}
    campos = {f["name"]: f for f in data["fields"]}
    assert list(campos) == [
        "ciudadano",
        "programa",
        "cantidad_inicial",
        "fecha_vencimiento",
    ]
    assert campos["ciudadano"]["tag"] == "select"
    assert campos["ciudadano"]["value"] == str(ciudadano.pk)
    assert "select2" in campos["ciudadano"]["attrs"]["class"]
    assert campos["ciudadano"]["attrs"]["data-placeholder"] == (
        "Seleccionar ciudadano..."
    )
    assert [o["value"] for o in campos["programa"]["choices"]] == [
        "",
        str(programa.pk),
    ]
    assert campos["cantidad_inicial"]["attrs"]["type"] == "number"
    assert campos["fecha_vencimiento"]["attrs"]["type"] == "date"
    assert campos["fecha_vencimiento"]["help_text"] == ""


def test_voucher_create_persists_through_the_native_service_and_redirects(
    ciudadano, programa
):
    client = _client("add_voucher", "view_voucher")
    respuesta = client.post(
        f"{ROOT}asignar/", _voucher(ciudadano, programa), format="multipart"
    )
    voucher = Voucher.objects.get()
    assert respuesta.status_code == 200
    assert respuesta.json() == {"ok": True, "redirect": f"/vat/vouchers/{voucher.pk}/"}
    assert (voucher.ciudadano_id, voucher.programa_id, voucher.cantidad_inicial) == (
        ciudadano.pk,
        programa.pk,
        10,
    )
    assert voucher.cantidad_disponible == 10
    assert client.get(f"{ROOT}{voucher.pk}/").json()["messages"] == [
        {
            "message": "Voucher asignado exitosamente a Prueba, Ana.",
            "level": "success",
        }
    ]


def test_voucher_create_rejects_invalid_data_and_service_errors_without_saving(
    ciudadano, programa, monkeypatch
):
    client = _client("add_voucher")
    pasado = (date.today() - timedelta(days=1)).isoformat()
    respuesta = client.post(
        f"{ROOT}asignar/",
        _voucher(ciudadano, programa, fecha_vencimiento=pasado, cantidad_inicial="0"),
        format="multipart",
    )
    assert respuesta.status_code == 400
    campos = {f["name"]: f for f in respuesta.json()["fields"]}
    assert campos["fecha_vencimiento"]["errors"] == [
        "La fecha de vencimiento debe ser posterior a hoy."
    ]
    assert len(campos["cantidad_inicial"]["errors"]) == 1
    assert campos["ciudadano"]["value"] == str(ciudadano.pk)
    assert Voucher.objects.count() == 0

    def fallar(**_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(VoucherService, "crear_voucher", fallar)
    respuesta = client.post(
        f"{ROOT}asignar/", _voucher(ciudadano, programa), format="multipart"
    )
    assert respuesta.status_code == 400
    assert respuesta.json()["messages"] == [
        {"message": "Error al crear el voucher: boom", "level": "error"}
    ]
    assert Voucher.objects.count() == 0


def test_native_and_api_create_the_same_voucher(ciudadano, programa):
    user = get_user_model().objects.create_superuser("super", password="x")
    nativo = Client()
    nativo.force_login(user)
    nativo.post("/vat/vouchers/asignar/", _voucher(ciudadano, programa))
    via_api = APIClient()
    via_api.force_login(user)
    via_api.post(f"{ROOT}asignar/", _voucher(ciudadano, programa), format="multipart")
    a, b = Voucher.objects.order_by("pk")
    campos = (
        "ciudadano_id",
        "programa_id",
        "cantidad_inicial",
        "cantidad_disponible",
        "fecha_vencimiento",
        "estado",
    )
    assert [getattr(a, c) for c in campos] == [getattr(b, c) for c in campos]


def test_masivo_form_and_result_match_the_native_page(ciudadano, programa):
    client = _client("add_voucher")
    form = client.get(f"{ROOT}asignar-masivo/").json()
    assert [f["name"] for f in form["fields"]] == [
        "programa",
        "cantidad_inicial",
        "fecha_vencimiento",
        "dnis",
    ]
    assert form["resultado"] is None
    dnis = f"{ciudadano.documento}, 99999999;{ciudadano.documento}"
    datos = {
        "programa": programa.pk,
        "cantidad_inicial": "5",
        "fecha_vencimiento": _vence(),
        "dnis": dnis,
    }
    usuario = get_user_model().objects.create_superuser("super", password="x")
    nativo = Client()
    nativo.force_login(usuario)
    esperado = nativo.post("/vat/vouchers/asignar-masivo/", datos).context["resultado"]
    asignados = Voucher.objects.count()
    Voucher.objects.all().delete()
    respuesta = client.post(f"{ROOT}asignar-masivo/", datos, format="multipart")
    assert respuesta.status_code == 200
    assert respuesta.json()["resultado"] == esperado
    assert Voucher.objects.count() == asignados
    campos = {f["name"]: f for f in respuesta.json()["fields"]}
    assert campos["dnis"]["value"] == dnis
    assert campos["programa"]["value"] == str(programa.pk)


def test_masivo_rejects_invalid_data_and_saves_nothing(ciudadano, programa):
    client = _client("add_voucher")
    respuesta = client.post(
        f"{ROOT}asignar-masivo/",
        {
            "programa": programa.pk,
            "cantidad_inicial": "5",
            "fecha_vencimiento": _vence(),
            "dnis": " , ; ",
        },
        format="multipart",
    )
    assert respuesta.status_code == 400
    campos = {f["name"]: f for f in respuesta.json()["fields"]}
    assert campos["dnis"]["errors"] == ["Ingresá al menos un DNI."]
    assert respuesta.json()["resultado"] is None
    demasiados = ",".join(str(10_000_000 + n) for n in range(501))
    respuesta = client.post(
        f"{ROOT}asignar-masivo/",
        {
            "programa": programa.pk,
            "cantidad_inicial": "5",
            "fecha_vencimiento": _vence(),
            "dnis": demasiados,
        },
        format="multipart",
    )
    assert respuesta.status_code == 400
    assert Voucher.objects.count() == 0


def test_parametria_form_projects_radios_checkboxes_and_help_texts(programa):
    data = _client("add_voucher").get(f"{ROOT}parametrias/nueva/").json()
    assert data["titulo"] == "Nueva parametría de voucher"
    campos = {f["name"]: f for f in data["fields"]}
    assert list(campos) == [
        "nombre",
        "descripcion",
        "programa",
        "cantidad_inicial",
        "fecha_vencimiento",
        "renovacion_mensual",
        "cantidad_renovacion",
        "renovacion_tipo",
        "inscripcion_unica_activa",
    ]
    tipo = campos["renovacion_tipo"]
    assert (tipo["tag"], tipo["value"]) == ("radio", "suma")
    assert tipo["choices"] == [
        {
            "value": "suma",
            "label": "Sumar al saldo existente",
            "id": "id_renovacion_tipo_0",
        },
        {
            "value": "reinicia",
            "label": "Reiniciar al valor configurado",
            "id": "id_renovacion_tipo_1",
        },
    ]
    assert campos["renovacion_mensual"]["attrs"]["type"] == "checkbox"
    assert campos["renovacion_mensual"]["value"] is False
    assert campos["renovacion_mensual"]["help_text"].startswith("Si está activo")
    assert campos["descripcion"]["attrs"]["rows"] == "2"


def test_parametria_create_persists_creado_por_and_queues_the_message(programa):
    client = _client("add_voucher", "view_voucher")
    respuesta = client.post(
        f"{ROOT}parametrias/nueva/", _parametria(programa), format="multipart"
    )
    p = VoucherParametria.objects.get()
    assert respuesta.json() == {
        "ok": True,
        "redirect": f"/vat/vouchers/parametrias/{p.pk}/",
    }
    assert (
        p.nombre,
        p.programa_id,
        p.cantidad_inicial,
        p.renovacion_mensual,
        p.cantidad_renovacion,
        p.renovacion_tipo,
        p.inscripcion_unica_activa,
        p.creado_por_id,
    ) == (
        "Parametria sintetica",
        programa.pk,
        8,
        True,
        3,
        "reinicia",
        True,
        client.user.pk,
    )
    assert client.get(f"{ROOT}parametrias/").json()["messages"] == [
        {
            "message": "Parametría 'Parametria sintetica' creada correctamente.",
            "level": "success",
        }
    ]


def test_parametria_create_rejects_invalid_data_with_the_bound_form(programa):
    client = _client("add_voucher")
    pasado = (date.today() - timedelta(days=1)).isoformat()
    respuesta = client.post(
        f"{ROOT}parametrias/nueva/",
        _parametria(programa, nombre="", fecha_vencimiento=pasado, renovacion_tipo="x"),
        format="multipart",
    )
    assert respuesta.status_code == 400
    campos = {f["name"]: f for f in respuesta.json()["fields"]}
    assert len(campos["nombre"]["errors"]) == 1
    assert campos["fecha_vencimiento"]["errors"] == [
        "La fecha de vencimiento debe ser posterior a hoy."
    ]
    assert len(campos["renovacion_tipo"]["errors"]) == 1
    assert campos["inscripcion_unica_activa"]["value"] is True
    assert VoucherParametria.objects.count() == 0


def test_writes_require_csrf_and_view_only_users_cannot_write(ciudadano, programa):
    sin_csrf = _client("add_voucher", csrf=True)
    assert (
        sin_csrf.post(
            f"{ROOT}asignar/", _voucher(ciudadano, programa), format="multipart"
        ).status_code
        == 403
    )
    assert (
        sin_csrf.post(
            f"{ROOT}parametrias/nueva/", _parametria(programa), format="multipart"
        ).status_code
        == 403
    )
    lector = _client("view_voucher", "change_voucher")
    for url, datos in (
        (f"{ROOT}asignar/", _voucher(ciudadano, programa)),
        (f"{ROOT}parametrias/nueva/", _parametria(programa)),
        (f"{ROOT}asignar-masivo/", {"programa": programa.pk}),
    ):
        assert lector.post(url, datos, format="multipart").status_code == 403
    assert Voucher.objects.count() == 0
    assert VoucherParametria.objects.count() == 0
