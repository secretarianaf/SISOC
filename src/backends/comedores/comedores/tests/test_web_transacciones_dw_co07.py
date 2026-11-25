"""Web API (G1 v1) of the DW transactions history: ``/api/web/comedores/comedores/`` (CO07.01).

The endpoint runs the native ``ComedorTransaccionesDetailView``; these tests compare the
JSON with what ``comedor_transacciones_detail.html`` shows (period, movements and the
Transferido=debito_total / Gastado=credito_total mapping, «Sin información»), check the
page forwarded to the service, the native guards and that reading never writes.
"""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client

from comedores.models import Comedor
from comedores.services.dw_transacciones_service.impl import (
    DWTransaccion,
    DWTransaccionesService,
)

pytestmark = pytest.mark.django_db


@pytest.fixture(name="comedor_fixture", autouse=True)
def sin_dobles_del_conftest():
    """Same name as the folder's autouse double: the endpoint runs the real scope."""


def _client(username, *codenames):
    usuario = get_user_model().objects.create_user(username, password="x")
    profile = usuario.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    for codename in codenames:
        usuario.user_permissions.add(Permission.objects.get(codename=codename))
    client = Client()
    client.force_login(usuario)
    return client


@pytest.fixture(name="web")
def web_fixture():
    return _client("lector_transacciones_co07", "view_comedor")


@pytest.fixture(name="comedor")
def comedor_fixture():
    return Comedor.objects.create(nombre="Comedor DW")


def _url(comedor):
    return f"/api/web/comedores/comedores/{comedor.pk}/transacciones/"


def _servir(monkeypatch, filas, total=None, llamadas=None):
    def historico(comedor_id, page=1, per_page=20):
        if llamadas is not None:
            llamadas.append((comedor_id, page, per_page))
        return filas, len(filas) if total is None else total

    monkeypatch.setattr(
        DWTransaccionesService, "obtener_historico_completo", staticmethod(historico)
    )


def _dw(periodo, debitos, credito, debito, cereo, comedor_id=1):
    return DWTransaccion(
        comedor_id_sisoc=comedor_id,
        periodo=periodo,
        cantidad_debitos=debitos,
        credito_total=credito,
        debito_total=debito,
        cereo=cereo,
    )


def test_rows_match_the_native_template(web, comedor, monkeypatch):
    llamadas = []
    _servir(
        monkeypatch,
        [
            _dw("202609", 14, Decimal("1500"), Decimal("1234567"), Decimal("0")),
            _dw("202608", 3, None, None, None),
            _dw("2026", 0, Decimal("0"), Decimal("0"), Decimal("999")),
        ],
        llamadas=llamadas,
    )

    respuesta = web.get(_url(comedor))

    assert respuesta.status_code == 200, respuesta.content[:400]
    datos = respuesta.json()
    assert datos["comedor"] == {"id": comedor.pk, "nombre": "Comedor DW"}
    # Transferido is debito_total and Gastado is credito_total (not swapped by name).
    assert datos["transacciones"] == [
        {
            "periodo": "2026-09",
            "movimientos": "14",
            "transferido": "$1.234.567",
            "gastado": "$1.500",
            "saldo": "$0",
        },
        {
            "periodo": "2026-08",
            "movimientos": "3",
            "transferido": "Sin información",
            "gastado": "Sin información",
            "saldo": "Sin información",
        },
        {
            "periodo": "2026",
            "movimientos": "0",
            "transferido": "$0",
            "gastado": "$0",
            "saldo": "$999",
        },
    ]
    assert datos["urls"] == {
        "comedores": "/comedores/listar",
        "comedor": f"/comedores/{comedor.pk}",
    }
    # First page, 1000 per page, for the authorized comedor only.
    assert llamadas == [(comedor.pk, 1, 1000)]


def test_page_is_forwarded_and_an_invalid_one_falls_back_to_the_first(
    web, comedor, monkeypatch
):
    llamadas = []
    _servir(monkeypatch, [], llamadas=llamadas)

    web.get(_url(comedor), {"page": "3"})
    web.get(_url(comedor), {"page": "abc"})

    assert [pagina for _, pagina, _ in llamadas] == [3, 1]


def test_no_data_and_a_failing_dw_show_the_same_empty_list(web, comedor):
    # Without the DW view (test database) the real service logs the error and returns [], 0.
    respuesta = web.get(_url(comedor))

    assert respuesta.status_code == 200
    assert respuesta.json()["transacciones"] == []


def test_guards_are_the_native_ones(web, comedor, monkeypatch):
    llamadas = []
    _servir(monkeypatch, [], llamadas=llamadas)
    sin_permiso = _client("sin_permiso_transacciones_co07")
    otro_permiso = _client("otro_permiso_transacciones_co07", "view_admision")

    assert Client().get(_url(comedor)).status_code in (401, 403)
    assert sin_permiso.get(_url(comedor)).status_code == 403
    # The native route admits only ``comedores.view_comedor``.
    assert otro_permiso.get(_url(comedor)).status_code == 403
    assert web.get(_url(Comedor(pk=999999))).status_code == 404
    assert llamadas == []


def test_post_is_not_allowed_and_the_dw_is_not_queried(web, comedor, monkeypatch):
    llamadas = []
    _servir(monkeypatch, [], llamadas=llamadas)

    respuesta = web.post(_url(comedor), {"x": "1"})

    assert respuesta.status_code in (403, 405)
    assert llamadas == []
