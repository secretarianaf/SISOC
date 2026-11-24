"""Web API (G1 v1) of the amounts-per-program ABM: ``/api/web/comedores/montos/``.

Every endpoint runs the native ``views.montos_prestacion`` view. The monolith
tests go through ``config.settings_all`` (policy evaluated locally); the
runtime tests switch to ``SISOC_BACKEND="comedores"`` with the real runtime
URLconf, where only a request the core signed reaches the view.
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone

from core import web_gate
from core.models import MontoPrestacionPrograma, Programa
from historial.models import Historial
from historial.services.historial_service import HistorialService

ROOT = "/api/web/comedores/montos/"
LISTA = "/montoprestacion/listar"

pytestmark = pytest.mark.django_db


def _ready(user):
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    return user


@pytest.fixture(name="gestor")
def gestor_fixture():
    # The native decorator only admits canonical codes or a superuser: the
    # «Gestor prestaciones»/«Prestacion» names resolve to no permission code.
    return _ready(
        get_user_model().objects.create_superuser("gestor_montos", password="x")
    )


@pytest.fixture(name="web")
def web_fixture(gestor):
    client = Client()
    client.force_login(gestor)
    return client


@pytest.fixture(name="programas")
def programas_fixture():
    return [Programa.objects.create(nombre=n) for n in ("Programa B", "Programa A")]


def _monto(programa, usuario, **valores):
    return MontoPrestacionPrograma.objects.create(
        programa=programa, usuario_creador=usuario, **valores
    )


def _con_permiso_de_ver():
    usuario = _ready(get_user_model().objects.create_user("ve_montos"))
    usuario.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="core", codename="view_montoprestacionprograma"
        )
    )
    return usuario


# --- Monolith: list, detail and pages ---------------------------------------


def test_list_renders_the_native_values_and_pages_of_ten(web, gestor, programas):
    primero = _monto(
        programas[0], gestor, desayuno_valor=Decimal("1025.50"), cena_valor=Decimal("0")
    )
    fecha = timezone.make_aware(datetime(2026, 11, 9, 12, 0))
    MontoPrestacionPrograma.objects.filter(pk=primero.pk).update(
        fecha_creacion=fecha, fecha_modificacion=fecha + timedelta(hours=1)
    )
    for _ in range(10):
        _monto(programas[1], gestor, almuerzo_valor=Decimal("1"))

    respuesta = web.get(ROOT)

    assert respuesta.status_code == 200
    assert respuesta["Cache-Control"] == "private, no-store"
    data = respuesta.json()
    assert len(data["results"]) == 10
    assert data["results"][0] == {
        "id": primero.pk,
        "programa": "Programa B",
        "desayuno_valor": "1025,50",
        "almuerzo_valor": "None",
        "merienda_valor": "None",
        "cena_valor": "0,00",
        "usuario_creador": "gestor_montos",
        "fecha_creacion": timezone.localtime(fecha).strftime("%d/%m/%Y %H:%M"),
        "fecha_modificacion": timezone.localtime(fecha + timedelta(hours=1)).strftime(
            "%d/%m/%Y %H:%M"
        ),
    }
    assert data["page"] == {
        "number": 1,
        "count": 11,
        "is_paginated": True,
        "previous": None,
        "next": 2,
        "range": [1, 2],
        "query_without_page": "",
    }
    assert data["urls"] == {"listar": LISTA, "crear": "/montoprestacion/crear"}
    nativo = web.get(LISTA).context["prestaciones"]
    assert [fila["id"] for fila in data["results"]] == [m.pk for m in nativo]


def test_list_page_two_keeps_other_params_and_an_invalid_page_is_404(
    web, gestor, programas
):
    for _ in range(11):
        _monto(programas[0], gestor, desayuno_valor=Decimal("1"))

    data = web.get(ROOT, {"orden": "a b", "page": "2"}).json()

    assert len(data["results"]) == 1
    assert data["page"]["query_without_page"] == "orden=a%20b&"
    assert data["page"]["previous"] == 1
    assert web.get(ROOT, {"page": "9"}).status_code == 404
    assert web.get(LISTA, {"page": "9"}).status_code == 404


def test_empty_list_has_no_rows(web):
    data = web.get(ROOT).json()

    assert data["results"] == []
    assert data["page"]["count"] == 0
    assert data["page"]["is_paginated"] is False


def test_detail_matches_the_native_table(web, gestor, programas):
    monto = _monto(programas[0], gestor, merienda_valor=Decimal("12.5"))

    data = web.get(f"{ROOT}{monto.pk}/").json()

    assert data["breadcrumb"] == [
        {"text": "Monto de Prestaciones", "url": LISTA},
        {"text": "Detalle", "url": None},
    ]
    assert data["back_button"] == {
        "url": LISTA,
        "text": "Volver",
        "type": "outline-light",
    }
    assert data["monto"]["merienda_valor"] == "12,50"
    assert data["monto"]["desayuno_valor"] == "None"
    assert web.get(f"{ROOT}999999/").status_code == 404


# --- Monolith: create, edit, delete -----------------------------------------


def test_create_form_lists_programs_by_name(web, programas):
    data = web.get(ROOT + "crear/").json()

    assert data["breadcrumb"][-1] == {"text": "Crear Monto de Prestación", "url": None}
    assert [f["name"] for f in data["fields"]] == [
        "programa",
        "desayuno_valor",
        "almuerzo_valor",
        "merienda_valor",
        "cena_valor",
    ]
    assert data["fields"][0]["required"] is True
    assert data["fields"][1]["label"] == "Valor desayuno"
    assert [c["label"] for c in data["fields"][0]["choices"]] == [
        "---------",
        "Programa A",
        "Programa B",
    ]
    assert data["errors"] == {}


def test_create_saves_through_the_native_view(web, gestor, programas, monkeypatch):
    monkeypatch.setattr(
        "config.middlewares.threadlocals.get_current_user", lambda: gestor
    )

    respuesta = web.post(
        ROOT + "crear/",
        {
            "programa": programas[0].pk,
            "desayuno_valor": "150.25",
            "almuerzo_valor": "",
            "merienda_valor": "0",
            "cena_valor": "",
        },
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {"ok": True, "redirect": LISTA}
    creado = MontoPrestacionPrograma.objects.get()
    assert (creado.programa, creado.usuario_creador) == (programas[0], gestor)
    assert creado.desayuno_valor == Decimal("150.25")
    assert creado.merienda_valor == Decimal("0")
    assert creado.almuerzo_valor is None
    assert Historial.objects.filter(
        accion="Creación de Monto de Prestación", object_id=str(creado.pk)
    ).exists()
    assert web.get(ROOT).json()["messages"] == [
        {"message": "Monto de Prestación creada correctamente.", "level": "success"}
    ]
    assert web.get(ROOT).json()["messages"] == []


def test_create_without_amounts_returns_the_native_errors(web, programas):
    datos = {"programa": programas[0].pk, "desayuno_valor": "", "cena_valor": "x"}

    respuesta = web.post(ROOT + "crear/", datos)

    assert respuesta.status_code == 400
    data = respuesta.json()
    nativo = web.post("/montoprestacion/crear", datos).context["form"].errors
    assert data["errors"] == nativo.get_json_data()
    assert data["errors"]["cena_valor"][0]["message"] == "Introduzca un número."
    assert data["fields"][4]["value"] == "x"
    assert data["fields"][0]["value"] == str(programas[0].pk)
    sin_montos = web.post(ROOT + "crear/", {"programa": programas[0].pk}).json()
    assert [e["message"] for e in sin_montos["errors"]["__all__"]] == [
        "Debe informar al menos un monto.",
        "No se cumple la restricción “monto_prestacion_al_menos_un_valor”.",
    ]
    assert MontoPrestacionPrograma.objects.count() == 0


def test_edit_shows_the_widget_values_and_saves_with_history(web, gestor, programas):
    monto = _monto(programas[0], gestor, cena_valor=Decimal("3702.75"))

    data = web.get(f"{ROOT}{monto.pk}/editar/").json()

    assert [f["value"] for f in data["fields"]] == [
        str(programas[0].pk),
        "",
        "",
        "",
        "3702.75",
    ]
    assert data["breadcrumb"][-1]["text"] == "Editar Monto de Prestación"
    respuesta = web.post(
        f"{ROOT}{monto.pk}/editar/",
        {"programa": programas[1].pk, "cena_valor": "", "almuerzo_valor": "9.99"},
    )
    assert respuesta.json() == {"ok": True, "redirect": LISTA}
    monto.refresh_from_db()
    assert (monto.programa, monto.cena_valor, monto.almuerzo_valor) == (
        programas[1],
        None,
        Decimal("9.99"),
    )
    assert monto.usuario_creador == gestor
    assert Historial.objects.filter(
        accion="Edición de Monto de Prestación", object_id=str(monto.pk)
    ).exists()
    assert web.get(ROOT).json()["messages"][0]["message"] == (
        "Monto de Prestación actualizado correctamente."
    )


def test_delete_confirms_then_removes_physically_with_history(web, gestor, programas):
    monto = _monto(programas[0], gestor, desayuno_valor=Decimal("1"))

    data = web.get(f"{ROOT}{monto.pk}/eliminar/").json()

    assert data == {
        "breadcrumb": [
            {"text": "Monto de Prestaciones", "url": LISTA},
            {"text": "Eliminar Monto de Prestación", "url": None},
        ],
        "object_name": "PROGRAMA B",
        "delete_message": (
            "¿Desea eliminar este monto de prestación? Esta acción no se puede deshacer."
        ),
        "cancel_url": LISTA,
    }
    respuesta = web.post(f"{ROOT}{monto.pk}/eliminar/")
    assert respuesta.json() == {"ok": True, "redirect": LISTA}
    assert not MontoPrestacionPrograma.objects.filter(pk=monto.pk).exists()
    assert Programa.objects.filter(pk=programas[0].pk).exists()
    assert Historial.objects.filter(
        accion="Eliminación de Prestación", object_id=str(monto.pk)
    ).exists()
    assert web.get(ROOT).json()["messages"][0]["message"] == (
        "Monto de Prestación eliminado correctamente."
    )
    assert web.get(f"{ROOT}{monto.pk}/eliminar/").status_code == 404


def test_delete_keeps_the_row_when_history_fails(web, gestor, programas, monkeypatch):
    monto = _monto(programas[0], gestor, desayuno_valor=Decimal("1"))
    monkeypatch.setattr(
        HistorialService,
        "registrar_historial",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("historial caido")),
    )

    with pytest.raises(RuntimeError, match="historial caido"):
        web.post(f"{ROOT}{monto.pk}/eliminar/")

    assert MontoPrestacionPrograma.objects.filter(pk=monto.pk).exists()


def test_read_endpoints_only_answer_get(web, gestor, programas):
    monto = _monto(programas[0], gestor, desayuno_valor=Decimal("1"))

    for url in (ROOT, f"{ROOT}{monto.pk}/"):
        for metodo in ("post", "put", "delete"):
            assert getattr(web, metodo)(url).status_code == 405, (url, metodo)
    assert MontoPrestacionPrograma.objects.count() == 1


def test_writes_require_the_csrf_token(gestor, programas):
    client = Client(enforce_csrf_checks=True)
    client.force_login(gestor)

    respuesta = client.post(
        ROOT + "crear/", {"programa": programas[0].pk, "desayuno_valor": "1"}
    )

    assert respuesta.status_code == 403
    assert MontoPrestacionPrograma.objects.count() == 0


# --- Monolith: access, same rule as the native routes -----------------------


def test_anonymous_gets_401_json(client):
    respuesta = client.get(ROOT)

    assert respuesta.status_code == 401
    assert respuesta.json() == {"detail": web_gate.DETAIL_UNAUTHENTICATED}


def test_view_permission_alone_is_still_rejected_like_the_native_routes(
    client, gestor, programas
):
    monto = _monto(programas[0], gestor, desayuno_valor=Decimal("1"))
    client.force_login(_con_permiso_de_ver())

    for url in (ROOT, ROOT + "crear/", f"{ROOT}{monto.pk}/eliminar/"):
        assert client.get(url).status_code == 403, url
        assert "state" not in client.get(url).json()
    assert client.post(f"{ROOT}{monto.pk}/eliminar/").status_code == 403
    assert client.get(LISTA).status_code == 403
    assert MontoPrestacionPrograma.objects.filter(pk=monto.pk).exists()


def test_pending_web_requirement_is_reported_and_a_forged_header_is_ignored(
    web, gestor
):
    gestor.profile.must_change_password = True
    gestor.profile.save()
    falso = web_gate.sign(
        audience="comedores",
        user_pk=gestor.pk,
        session_key=web.cookies[settings.SESSION_COOKIE_NAME].value,
        method="GET",
        target=ROOT,
    )

    respuesta = web.get(ROOT, HTTP_X_SISOC_WEB_GATE=falso, RAW_URI=ROOT)

    assert respuesta.status_code == 403
    assert respuesta.json()["state"] == "password_change_required"


def test_admindocs_head_does_not_bypass_the_web_api(client, gestor, programas):
    monto = _monto(programas[0], gestor, desayuno_valor=Decimal("1"))
    staff = _ready(get_user_model().objects.create_user("staff_montos", is_staff=True))
    client.force_login(staff)

    for url in (
        ROOT,
        ROOT + "crear/",
        f"{ROOT}{monto.pk}/",
        f"{ROOT}{monto.pk}/editar/",
    ):
        respuesta = client.head(url)
        assert respuesta.status_code == 403, url
        assert "X-View" not in respuesta


# --- Split runtime ----------------------------------------------------------


@pytest.fixture(name="runtime")
def runtime_fixture():
    with override_settings(
        SISOC_BACKEND="comedores",
        ROOT_URLCONF="comedores_runtime.urls",
        SISOC_BACKENDS={},
        INTERNAL_IPS=[],
    ):
        yield


def _signed(user, client, *, target=ROOT, method="GET", now=None):
    return web_gate.sign(
        audience="comedores",
        user_pk=user.pk,
        session_key=client.cookies[settings.SESSION_COOKIE_NAME].value,
        method=method,
        target=target,
        now=now,
    )


@pytest.mark.usefixtures("runtime")
def test_runtime_serves_signed_reads_and_writes(web, gestor, programas):
    respuesta = web.get(ROOT, RAW_URI=ROOT, HTTP_X_SISOC_WEB_GATE=_signed(gestor, web))
    assert respuesta.status_code == 200

    target = ROOT + "crear/"
    respuesta = web.post(
        target,
        {"programa": programas[0].pk, "cena_valor": "5"},
        RAW_URI=target,
        HTTP_X_SISOC_WEB_GATE=_signed(gestor, web, target=target, method="POST"),
    )

    assert respuesta.json() == {"ok": True, "redirect": LISTA}
    assert MontoPrestacionPrograma.objects.get().cena_valor == Decimal("5")


@pytest.mark.usefixtures("runtime")
def test_runtime_rejects_unsigned_and_stale_requests(web, gestor, programas):
    target = ROOT + "crear/"
    for token in (
        None,
        _signed(gestor, web, target=target),  # signed for GET
        _signed(
            gestor,
            web,
            target=target,
            method="POST",
            now=timezone.now().timestamp() - 61,
        ),
    ):
        extra = {"RAW_URI": target}
        if token:
            extra["HTTP_X_SISOC_WEB_GATE"] = token
        respuesta = web.post(
            target, {"programa": programas[0].pk, "cena_valor": "5"}, **extra
        )
        assert respuesta.status_code == 403
        assert respuesta.json() == {"detail": web_gate.DETAIL_REJECTED}
    assert MontoPrestacionPrograma.objects.count() == 0


@pytest.mark.usefixtures("runtime")
def test_runtime_still_applies_the_native_rule(client):
    usuario = _con_permiso_de_ver()
    client.force_login(usuario)

    respuesta = client.get(
        ROOT, RAW_URI=ROOT, HTTP_X_SISOC_WEB_GATE=_signed(usuario, client)
    )

    assert respuesta.status_code == 403
    assert respuesta.json() != {"detail": web_gate.DETAIL_REJECTED}


def test_comedores_publishes_its_web_api_prefix():
    from config.backends import (
        load_backends_registry,
    )  # pylint: disable=import-outside-toplevel

    prefijos = load_backends_registry()["comedores"]["url_prefixes"]

    assert web_gate.web_api_prefix("comedores") in prefijos
    assert reverse("comedores_web_montos") == ROOT
