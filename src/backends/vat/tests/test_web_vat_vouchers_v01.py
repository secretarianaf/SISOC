"""V01.01: web API de vouchers y parametrías (``/api/web/vat/vouchers/``).

Cada endpoint corre la vista nativa; los tests cubren acceso, datos, mensajes
pendientes y la compuerta G1 del runtime de VAT. Datos sintéticos.
"""

from datetime import date, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, override_settings
from rest_framework.test import APIClient

from ciudadanos.models import Ciudadano
from core import web_gate
from core.models import Programa
from VAT.models import Voucher, VoucherParametria
from VAT.services.voucher_service.impl import VoucherService

pytestmark = pytest.mark.django_db

ROOT = "/api/web/vat/vouchers/"


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


@pytest.fixture(name="programa")
def programa_fixture():
    return Programa.objects.create(nombre="Programa Sintetico")


@pytest.fixture(name="admin")
def admin_fixture(superuser):
    return superuser


def _voucher(programa, user, n=1, **extra):
    ciudadano = Ciudadano.objects.create(
        nombre=f"Ana{n}",
        apellido="Prueba",
        documento=30000000 + n,
        fecha_nacimiento=date(1990, 1, 1),
    )
    voucher = VoucherService.crear_voucher(
        ciudadano_id=ciudadano.id,
        programa_id=programa.id,
        cantidad=10,
        fecha_vencimiento=date.today() + timedelta(days=30),
        usuario=user,
    )
    for campo, valor in extra.items():
        setattr(voucher, campo, valor)
    if extra:
        voucher.save()
    return voucher


def test_list_requires_session_and_the_native_permission(programa, admin):
    assert APIClient().get(ROOT).status_code == 401
    sin_permiso = _user("sin_permiso")
    assert _client(sin_permiso).get(ROOT).status_code == 403
    lector = _user("lector", "view_voucher")
    assert _client(lector).get(ROOT).status_code == 200
    # Otro permiso de VAT no alcanza: es la regla de la ruta nativa.
    assert _client(_user("otro", "view_centro")).get(ROOT).status_code == 403


def test_list_projects_the_native_rows_and_urls(programa, admin):
    voucher = _voucher(programa, admin)
    data = _client(admin).get(ROOT).json()
    fila = data["results"][0]
    assert fila == {
        "id": voucher.pk,
        "ciudadano": "Ana1 Prueba",
        "documento": "30000001",
        "programa": "Programa Sintetico",
        "disponible": 10,
        "inicial": 10,
        "vencimiento": voucher.fecha_vencimiento.strftime("%d/%m/%Y"),
        "estado": "activo",
        "estado_label": "Activo",
        "detail_url": f"/vat/vouchers/{voucher.pk}/",
    }
    assert data["urls"] == {
        "list": "/vat/vouchers/",
        "create": "/vat/vouchers/asignar/",
    }
    assert data["page"]["count"] == 1
    assert data["messages"] == []


def test_list_filters_with_the_native_queryset_and_drops_busqueda_from_page_links(
    programa, admin
):
    for n in range(1, 24):
        _voucher(programa, admin, n)
    client = _client(admin)
    pagina = client.get(ROOT, {"busqueda": "Prueba", "estado": "activo"}).json()
    assert len(pagina["results"]) == 20
    assert pagina["page"]["num_pages"] == 2
    # ``components/pagination.html`` repite el resto de los parámetros y descarta busqueda.
    assert pagina["page"]["query_without_page"] == "estado=activo&"
    assert pagina["busqueda"] == "Prueba"
    assert client.get(ROOT, {"busqueda": "30000007"}).json()["page"]["count"] == 1
    assert client.get(ROOT, {"busqueda": "zzz"}).json()["results"] == []
    assert client.get(ROOT, {"page": 9}).status_code == 404


def test_detail_projects_credits_history_and_native_action_forms(programa, admin):
    voucher = _voucher(programa, admin)
    VoucherService.recargar_voucher(
        voucher=voucher, cantidad=5, motivo="manual", usuario=admin
    )
    data = _client(admin).get(f"{ROOT}{voucher.pk}/").json()
    assert data["ciudadano"] == "Ana1 Prueba"
    assert data["estado_label"] == "Activo"
    assert (data["disponible"], data["inicial"]) == (15, 10)
    assert data["asignado_por"] == str(admin)
    assert data["dias_para_vencer"] == 30
    assert data["recargas"][0]["cantidad"] == 5
    assert data["recargas"][0]["motivo"] == "manual"
    assert {log["tipo_evento"] for log in data["logs"]} >= {"asignacion", "recarga"}
    acciones = data["acciones"]
    assert acciones["recargar"] and acciones["cancelar"]
    assert acciones["recargar_url"] == f"/vat/vouchers/{voucher.pk}/recargar/"
    assert acciones["cancelar_url"] == f"/vat/vouchers/{voucher.pk}/cancelar/"
    cantidad, motivo = acciones["campos"]
    assert (cantidad["name"], cantidad["tag"], cantidad["min"]) == (
        "cantidad",
        "input",
        1,
    )
    assert motivo["tag"] == "select"
    assert [c["value"] for c in motivo["choices"]] == [
        "automatica",
        "manual",
        "ajuste",
        "compensacion",
    ]


def test_detail_hides_credit_actions_without_change_permission_or_by_state(
    programa, admin
):
    voucher = _voucher(programa, admin)
    lector = _user("lector", "view_voucher")
    acciones = _client(lector).get(f"{ROOT}{voucher.pk}/").json()["acciones"]
    assert not acciones["recargar"] and not acciones["cancelar"]
    voucher.estado = "cancelado"
    voucher.save()
    acciones = _client(admin).get(f"{ROOT}{voucher.pk}/").json()["acciones"]
    assert not acciones["recargar"] and not acciones["cancelar"]
    assert _client(admin).get(f"{ROOT}999999/").status_code == 404


def test_detail_serves_the_pending_native_messages_once(programa, admin):
    voucher = _voucher(programa, admin)
    client = _client(admin)
    # El POST nativo encola el mensaje antes de redirigir.
    nativo = Client()
    nativo.force_login(admin)
    respuesta = nativo.post(f"/vat/vouchers/{voucher.pk}/cancelar/", follow=False)
    assert respuesta.status_code == 302
    # Mismo almacén de sesión: la API consume el mensaje como la página nativa.
    client.cookies = nativo.cookies
    data = client.get(f"{ROOT}{voucher.pk}/").json()
    assert data["messages"] == [
        {"message": "Voucher cancelado correctamente.", "level": "success"}
    ]
    assert client.get(f"{ROOT}{voucher.pk}/").json()["messages"] == []


def test_parametrias_list_matches_the_native_rows(programa, admin):
    parametria = VoucherParametria.objects.create(
        nombre="Parametria A",
        programa=programa,
        cantidad_inicial=8,
        fecha_vencimiento=date(2027, 3, 1),
        creado_por=admin,
    )
    _voucher(programa, admin, parametria=parametria)
    assert APIClient().get(f"{ROOT}parametrias/").status_code == 401
    assert _client(_user("sin")).get(f"{ROOT}parametrias/").status_code == 403
    data = _client(_user("lector", "view_voucher")).get(f"{ROOT}parametrias/").json()
    assert data["results"] == [
        {
            "id": parametria.pk,
            "nombre": "Parametria A",
            "programa": "Programa Sintetico",
            "cantidad_inicial": 8,
            "vencimiento": "01/03/2027",
            "activa": True,
            "vouchers": 1,
            "detail_url": f"/vat/vouchers/parametrias/{parametria.pk}/",
        }
    ]
    assert data["urls"]["create"] == "/vat/vouchers/parametrias/nueva/"


@pytest.mark.parametrize(
    "target",
    [
        ROOT,
        f"{ROOT}parametrias/",
        "/api/web/vat/evaluaciones/",
    ],
)
def test_runtime_requires_the_core_signed_gate(admin, target):
    with override_settings(
        SISOC_BACKEND="vat",
        ROOT_URLCONF="vat_runtime.urls",
        SISOC_WEB_ACCESS_POLICY=lambda request: type(
            "Access", (), {"state": "ready", "required_action_url": None}
        )(),
        INTERNAL_IPS=[],
    ):
        client = APIClient()
        client.force_login(admin)
        key = client.cookies["sessionid"].value
        assert client.get(target, RAW_URI=target).status_code == 403
        signed = web_gate.sign(
            audience="vat",
            user_pk=admin.pk,
            session_key=key,
            method="GET",
            target=target,
        )
        assert (
            client.get(target, RAW_URI=target, HTTP_X_SISOC_WEB_GATE=signed).status_code
            == 200
        )
    assert Voucher.objects.count() == 0
