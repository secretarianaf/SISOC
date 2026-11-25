"""Web API (G1 v1) of the payment files (EX01.01 and EX01.02).

``/api/web/comedores/expedientespagos/`` runs the native views of
``expedientespagos.views``. The tests pin today's access on purpose (reading
needs only a session; writing needs one of four read codes) and today's create,
which stores a second row without comedor.
"""

from decimal import Decimal

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, override_settings
from django.utils import timezone

from comedores.models import Comedor
from core import web_gate
from expedientespagos.models import ExpedientePago
from expedientespagos.views import _build_expediente_pago_list_item
from expedientespagos.web_api import FORM_FIELDS

ROOT = "/api/web/comedores/expedientespagos/"
NATIVO = "/expedientespagos/expedientespagos/"
CODES = [
    "comedores.view_comedor",
    "admisiones.view_admision",
    "acompanamientos.view_informacionrelevante",
    "expedientespagos.view_expedientepago",
]
COMIDAS = ("desayuno", "almuerzo", "merienda", "cena")

pytestmark = pytest.mark.django_db


def _ready(user):
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    return user


def _usuario(nombre, *codes, **extra):
    usuario = _ready(get_user_model().objects.create_user(nombre, **extra))
    for code in codes:
        app, codename = code.split(".")
        usuario.user_permissions.add(
            Permission.objects.get(content_type__app_label=app, codename=codename)
        )
    return usuario


def _client(usuario, **extra):
    client = Client(**extra)
    client.force_login(usuario)
    return client


@pytest.fixture(name="tecnico")
def tecnico_fixture():
    return _usuario("tecnico_exp", "comedores.view_comedor")


@pytest.fixture(name="web")
def web_fixture(tecnico):
    return _client(tecnico)


@pytest.fixture(name="comedor")
def comedor_fixture():
    return Comedor.objects.create(nombre="Comedor Expedientes")


def _expediente(comedor, **extra):
    datos = {
        "expediente_convenio": "EX-CONV-1",
        **{f"prestaciones_mensuales_{c}": 10 for c in COMIDAS},
        **{f"monto_mensual_{c}": Decimal("100") for c in COMIDAS},
    }
    datos.update(extra)
    return ExpedientePago.objects.create(comedor=comedor, **datos)


def _completo(**extra):
    datos = {
        "expediente_pago": "EX-PAGO-9",
        "expediente_convenio": "EX-CONV-9",
        "ano": "2026",
        "mes_pago": "marzo",
        "total": "1500.50",
        **{f"prestaciones_mensuales_{c}": "3" for c in COMIDAS},
        **{f"monto_mensual_{c}": "12.25" for c in COMIDAS},
    }
    datos.update(extra)
    return datos


# --- EX01.01 list ------------------------------------------------------------


def test_list_projects_the_native_rows_in_period_order(web, comedor):
    viejo = _expediente(comedor, ano="2025", mes_pago="diciembre", total=Decimal("9"))
    setiembre = _expediente(
        comedor, ano="2026", mes_pago="setiembre", expediente_pago="EP<1>"
    )
    marzo = _expediente(comedor, ano="2026", mes_pago="03", total=Decimal("1234.5"))
    _expediente(Comedor.objects.create(nombre="Otro"), ano="2027")

    respuesta = web.get(f"{ROOT}comedores/{comedor.pk}/")

    assert respuesta.status_code == 200
    assert respuesta["Cache-Control"] == "private, no-store"
    data = respuesta.json()
    assert [r["id"] for r in data["results"]] == [setiembre.pk, marzo.pk, viejo.pk]
    nativas = [
        [str(c["content"]) for c in _build_expediente_pago_list_item(e)["cells"]]
        for e in (setiembre, marzo, viejo)
    ]
    assert nativas[0][2] == "EP&lt;1&gt;"
    assert [r["cells"] for r in data["results"]][0][2] == "EP<1>"
    assert [r["cells"] for r in data["results"]][1] == [
        "03",
        "2026",
        "-",
        "EX-CONV-1",
        "$1.235",
        timezone.localtime(marzo.fecha_creacion).strftime("%d/%m/%Y"),
    ]
    assert [r["cells"] for r in data["results"]][1] == nativas[1]
    assert data["results"][0]["detail_url"] == f"{NATIVO}{setiembre.pk}/detalle/"
    assert data["headers"] == [
        "Mes de Pago",
        "Año",
        "Expediente de Pago",
        "Expediente del Convenio",
        "Total",
        "Fecha de creación",
    ]
    assert data["can_create"] is True
    assert data["create_url"] == f"{NATIVO}{comedor.pk}/nuevo/"
    assert data["breadcrumb_url"] == (
        f"/acompanamientos/acompanamiento/{comedor.pk}/detalle/"
    )
    assert data["columns"]["list_key"] == "expedientes_pagos_list"
    assert data["columns"]["endpoint"] == "/ajax/columnas-preferencias/"


def test_reading_needs_only_a_session_like_the_native_pages(client, comedor):
    expediente = _expediente(comedor)
    client.force_login(_usuario("sin_permisos_exp"))

    lista = client.get(f"{ROOT}comedores/{comedor.pk}/")
    ficha = client.get(f"{ROOT}{expediente.pk}/")

    assert lista.status_code == ficha.status_code == 200
    assert lista.json()["can_create"] is False
    assert client.get(f"{NATIVO}{comedor.pk}/").status_code == 200
    assert client.get(f"{NATIVO}{expediente.pk}/detalle/").status_code == 200


def test_view_expedientepago_alone_shows_the_create_button(client, comedor):
    client.force_login(_usuario("lector_exp", "expedientespagos.view_expedientepago"))
    assert client.get(f"{ROOT}comedores/{comedor.pk}/").json()["can_create"] is True


def test_unknown_comedor_and_a_global_page_out_of_range_are_404(web, comedor):
    _expediente(comedor)

    assert web.get(f"{ROOT}comedores/999999/").status_code == 404
    for url in (f"{ROOT}comedores/{comedor.pk}/", f"{NATIVO}{comedor.pk}/"):
        assert web.get(url, {"page": "2"}).status_code == 404, url
        assert web.get(url, {"page": "1"}).status_code == 200, url


def test_list_applies_the_saved_column_preferences(web, comedor):
    _expediente(comedor, ano="2026", mes_pago="mayo")
    guardado = web.post(
        "/ajax/columnas-preferencias/",
        data='{"list_key": "expedientes_pagos_list", "columns": ["ano", "mes_pago"]}',
        content_type="application/json",
    )
    assert guardado.status_code == 200

    data = web.get(f"{ROOT}comedores/{comedor.pk}/").json()

    assert data["headers"] == ["Año", "Mes de Pago"]
    assert data["results"][0]["cells"] == ["2026", "mayo"]


# --- EX01.01 detail ----------------------------------------------------------


def test_detail_renders_the_stored_values_without_recomputing(web, comedor):
    expediente = _expediente(
        comedor,
        expediente_pago="EP-7",
        mes_pago="abril",
        ano="2026",
        total=Decimal("2000.4"),
        total_prestaciones=Decimal("1.5"),
        fecha_acreditacion="2026-04-30",
        observaciones="Pagado & conciliado",
        prestaciones_mensuales_cena=0,
    )

    respuesta = web.get(f"{ROOT}{expediente.pk}/")

    assert respuesta.status_code == 200
    data = respuesta.json()
    e = data["expediente"]
    assert e["expediente_pago"] == "EP-7"
    assert e["mes_convenio"] == "-"
    assert e["organizacion_creacion"] == "-"
    assert e["total"] == "$2.000"
    assert e["total_prestaciones"] == "$2"
    assert e["gastos_accesorios"] == "$-"
    assert e["fecha_acreditacion"] == "30/04/2026"
    assert e["fecha_pago_al_banco"] == "-"
    assert e["observaciones"] == "Pagado & conciliado"
    assert e["prestaciones_mensuales_cena"] == "-"
    assert e["prestaciones_mensuales_desayuno"] == "10"
    assert e["monto_mensual_desayuno"] == "$100"
    assert data["list_url"] == f"{NATIVO}{comedor.pk}/"
    assert data["update_url"] == f"{NATIVO}{expediente.pk}/editar/"
    assert data["delete_url"] == f"{NATIVO}{expediente.pk}/eliminar/"


def test_detail_without_observations_and_missing_or_deleted_is_404(
    web, tecnico, comedor
):
    expediente = _expediente(comedor)
    assert (
        web.get(f"{ROOT}{expediente.pk}/").json()["expediente"]["observaciones"] == ""
    )
    assert web.get(f"{ROOT}999999/").status_code == 404
    expediente.delete(user=tecnico)
    assert web.get(f"{ROOT}{expediente.pk}/").status_code == 404
    assert web.get(f"{NATIVO}{expediente.pk}/detalle/").status_code == 404


# --- EX01.02 create ----------------------------------------------------------


def test_create_form_is_the_unbound_native_form(web, comedor):
    data = web.get(f"{ROOT}comedores/{comedor.pk}/crear/").json()

    assert [f["name"] for f in data["fields"]] == list(FORM_FIELDS)
    campos = {f["name"]: f for f in data["fields"]}
    assert campos["expediente_convenio"]["required"] is True
    # The unbound form without role flags: ``ano`` is optional on the page.
    assert campos["ano"]["required"] is False
    assert campos["ano"]["max_length"] == "4"
    assert campos["prestaciones_mensuales_cena"]["required"] is True
    assert campos["total"]["type"] == "number"
    assert campos["total"]["step"] == "0.01"
    assert campos["fecha_acreditacion"]["type"] == "date"
    assert campos["observaciones"]["type"] == "textarea"
    assert campos["expediente_pago"]["label"] == "Expediente de Pago"
    assert data["cancel_url"] == f"{NATIVO}{comedor.pk}/"


@pytest.mark.parametrize("code", CODES)
def test_create_saves_twice_like_the_native_view(client, comedor, code):
    client.force_login(_usuario(f"alta_{code.split('.')[1]}", code))

    respuesta = client.post(f"{ROOT}comedores/{comedor.pk}/crear/", _completo())

    assert respuesta.status_code == 200
    assert respuesta.json() == {"ok": True, "redirect": f"{NATIVO}{comedor.pk}/"}
    filas = ExpedientePago.objects.order_by("pk")
    # Native ``CreateView.form_valid`` saves the form after the service.
    assert [f.comedor_id for f in filas] == [comedor.pk, None]
    assert {f.total for f in filas} == {Decimal("1500.50")}
    assert {f.expediente_convenio for f in filas} == {"EX-CONV-9"}


def test_native_create_also_saves_twice(client, comedor):
    client.force_login(_usuario("super_exp", is_superuser=True))

    respuesta = client.post(f"{NATIVO}{comedor.pk}/nuevo/", _completo())

    assert respuesta.status_code == 302
    assert respuesta["Location"] == f"{NATIVO}{comedor.pk}/"
    assert list(
        ExpedientePago.objects.order_by("pk").values_list("comedor_id", flat=True)
    ) == [comedor.pk, None]


def test_technician_must_fill_year_and_monthly_values(web, comedor):
    datos = _completo(ano="")
    for comida in COMIDAS:
        datos.pop(f"monto_mensual_{comida}")

    respuesta = web.post(f"{ROOT}comedores/{comedor.pk}/crear/", datos)

    assert respuesta.status_code == 400
    data = respuesta.json()
    assert data["reset_form"] is True
    assert set(data["errors"]) == {"ano", *(f"monto_mensual_{c}" for c in COMIDAS)}
    assert data["errors"]["ano"][0]["message"] == "Este campo es requerido."
    # The native page shows the empty form without errors.
    assert {f["value"] for f in data["fields"]} == {""}
    assert all(f["errors"] == [] for f in data["fields"])
    assert ExpedientePago.objects.count() == 0


def test_only_view_expedientepago_accepts_empty_values_and_saves_zeros(client, comedor):
    client.force_login(_usuario("legales_exp", "expedientespagos.view_expedientepago"))

    respuesta = client.post(
        f"{ROOT}comedores/{comedor.pk}/crear/", {"expediente_convenio": "EC-L"}
    )

    assert respuesta.status_code == 200
    primero = ExpedientePago.objects.order_by("pk").first()
    assert primero.comedor_id == comedor.pk
    assert primero.ano is None
    assert primero.prestaciones_mensuales_cena == 0
    assert primero.monto_mensual_cena == Decimal("0")


@pytest.mark.parametrize(
    "cambio, campo, mensaje",
    [
        (
            {"expediente_convenio": ""},
            "expediente_convenio",
            "Este campo es requerido.",
        ),
        (
            {"ano": "20261"},
            "ano",
            "Asegúrese de que este valor tenga como máximo 4 caracteres (tiene 5).",
        ),
        ({"mes_pago": "m" * 21}, "mes_pago", None),
        (
            {"total": "1.234"},
            "total",
            "Asegúrese de que no existan mas de 2 lugares decimales.",
        ),
    ],
)
def test_create_rejects_what_the_form_rejects(web, comedor, cambio, campo, mensaje):
    respuesta = web.post(f"{ROOT}comedores/{comedor.pk}/crear/", _completo(**cambio))

    assert respuesta.status_code == 400
    errores = respuesta.json()["errors"]
    assert list(errores) == [campo]
    if mensaje:
        assert errores[campo][0]["message"] == mensaje
    assert ExpedientePago.objects.count() == 0


def test_create_for_a_missing_comedor_is_404_without_rows(web):
    respuesta = web.post(f"{ROOT}comedores/999999/crear/", _completo())

    assert respuesta.status_code == 404
    assert ExpedientePago.objects.count() == 0


def test_create_ignores_fields_the_page_does_not_render(web, tecnico, comedor):
    otro = Comedor.objects.create(nombre="Otro comedor")

    web.post(
        f"{ROOT}comedores/{comedor.pk}/crear/",
        _completo(
            deleted_at="2026-01-01T00:00:00",
            deleted_by=tecnico.pk,
            comedor=otro.pk,
            mes_convenio="3",
        ),
    )

    filas = list(ExpedientePago.all_objects.order_by("pk"))
    assert [f.comedor_id for f in filas] == [comedor.pk, None]
    assert all(f.deleted_at is None and f.deleted_by_id is None for f in filas)
    assert all(f.mes_convenio is None for f in filas)


# --- EX01.02 edit ------------------------------------------------------------


def test_edit_form_carries_the_values_and_the_role_flags(web, comedor):
    expediente = _expediente(
        comedor, ano="2026", fecha_pago_al_banco="2026-02-03", observaciones="Nota"
    )

    data = web.get(f"{ROOT}{expediente.pk}/editar/").json()

    campos = {f["name"]: f for f in data["fields"]}
    assert campos["ano"]["required"] is True
    assert campos["ano"]["value"] == "2026"
    assert campos["fecha_pago_al_banco"]["value"] == "2026-02-03"
    assert campos["observaciones"]["value"] == "Nota"
    assert campos["monto_mensual_cena"]["value"] == "100.00"
    assert data["cancel_url"] == f"{NATIVO}{comedor.pk}/"
    assert data["comedor_id"] == comedor.pk
    assert data["errors"] == {}


def test_edit_saves_keeps_the_comedor_and_ignores_unrendered_fields(
    web, tecnico, comedor
):
    expediente = _expediente(comedor, total=Decimal("1"))
    otro = Comedor.objects.create(nombre="Otro")

    respuesta = web.post(
        f"{ROOT}{expediente.pk}/editar/",
        _completo(total="77", comedor=otro.pk, deleted_at="2026-01-01T00:00:00"),
    )

    assert respuesta.json() == {"ok": True, "redirect": f"{NATIVO}{comedor.pk}/"}
    expediente.refresh_from_db()
    assert expediente.total == Decimal("77")
    assert expediente.comedor_id == comedor.pk
    assert expediente.deleted_at is None
    assert ExpedientePago.objects.count() == 1


def test_edit_errors_return_the_bound_form(web, comedor):
    expediente = _expediente(comedor)

    respuesta = web.post(
        f"{ROOT}{expediente.pk}/editar/", _completo(ano="20261", expediente_convenio="")
    )

    assert respuesta.status_code == 400
    data = respuesta.json()
    campos = {f["name"]: f for f in data["fields"]}
    assert campos["ano"]["value"] == "20261"
    assert campos["ano"]["errors"] == [
        "Asegúrese de que este valor tenga como máximo 4 caracteres (tiene 5)."
    ]
    assert campos["expediente_convenio"]["errors"] == ["Este campo es requerido."]
    assert "reset_form" not in data
    expediente.refresh_from_db()
    assert expediente.expediente_convenio == "EX-CONV-1"


# --- EX01.02 delete ----------------------------------------------------------


def test_delete_confirms_then_soft_deletes_with_the_native_message(
    web, tecnico, comedor
):
    expediente = _expediente(comedor, expediente_pago="ep-chico")

    confirmacion = web.get(f"{ROOT}{expediente.pk}/eliminar/").json()

    assert confirmacion["expediente_pago"] == "EP-CHICO"
    assert confirmacion["message"] == (
        "¿Estás seguro que deseas dar de baja lógica el expediente"
    )
    assert confirmacion["cascade_preview"]["total_afectados"] == 1
    assert confirmacion["cascade_preview"]["desglose_por_modelo"][0]["modo"] == (
        "baja_logica"
    )
    assert confirmacion["cancel_url"] == f"{NATIVO}{expediente.pk}/detalle/"

    respuesta = web.post(f"{ROOT}{expediente.pk}/eliminar/")

    assert respuesta.json() == {
        "ok": True,
        "message": "Expediente dado de baja correctamente.",
        "redirect": "/acompanamientos/acompanamiento/",
    }
    borrado = ExpedientePago.all_objects.get(pk=expediente.pk)
    assert borrado.deleted_at is not None
    assert borrado.deleted_by_id == tecnico.pk
    assert web.get(f"{ROOT}{expediente.pk}/").status_code == 404
    assert web.post(f"{ROOT}{expediente.pk}/eliminar/").status_code == 404
    mensajes = web.get(f"{ROOT}comedores/{comedor.pk}/").json()["messages"]
    assert mensajes == [
        {"message": "Expediente dado de baja correctamente.", "level": "success"}
    ]


# --- Access ------------------------------------------------------------------


def test_operations_need_one_of_the_four_codes_on_get_and_post(client, comedor):
    expediente = _expediente(comedor)
    client.force_login(_usuario("solo_lectura_exp", "comedores.change_comedor"))

    for url in (
        f"{ROOT}comedores/{comedor.pk}/crear/",
        f"{ROOT}{expediente.pk}/editar/",
        f"{ROOT}{expediente.pk}/eliminar/",
    ):
        assert client.get(url).status_code == 403, url
        assert client.post(url, _completo(total="5")).status_code == 403, url
    assert ExpedientePago.objects.get().total is None
    assert client.get(f"{NATIVO}{comedor.pk}/nuevo/").status_code == 403


def test_superuser_passes_every_operation(client, comedor):
    expediente = _expediente(comedor)
    client.force_login(_usuario("root_exp", is_superuser=True))

    for url in (
        f"{ROOT}comedores/{comedor.pk}/crear/",
        f"{ROOT}{expediente.pk}/editar/",
        f"{ROOT}{expediente.pk}/eliminar/",
    ):
        assert client.get(url).status_code == 200, url


def test_anonymous_gets_401_and_a_pending_requirement_403(client, tecnico, comedor):
    expediente = _expediente(comedor)
    urls = (
        f"{ROOT}comedores/{comedor.pk}/",
        f"{ROOT}{expediente.pk}/",
        f"{ROOT}comedores/{comedor.pk}/crear/",
        f"{ROOT}{expediente.pk}/editar/",
        f"{ROOT}{expediente.pk}/eliminar/",
    )
    for url in urls:
        respuesta = client.get(url)
        assert respuesta.status_code == 401, url
        assert respuesta.json() == {"detail": web_gate.DETAIL_UNAUTHENTICATED}
    tecnico.profile.must_change_password = True
    tecnico.profile.save()
    client.force_login(tecnico)
    for url in urls:
        respuesta = client.get(url)
        assert respuesta.status_code == 403, url
        assert respuesta.json()["state"] == "password_change_required"


def test_writes_require_the_csrf_token(tecnico, comedor):
    expediente = _expediente(comedor)
    client = _client(tecnico, enforce_csrf_checks=True)

    assert (
        client.post(f"{ROOT}comedores/{comedor.pk}/crear/", _completo()).status_code
        == 403
    )
    assert client.post(f"{ROOT}{expediente.pk}/eliminar/").status_code == 403
    assert ExpedientePago.objects.count() == 1


def test_read_endpoints_only_answer_get(web, comedor):
    expediente = _expediente(comedor)
    for url in (f"{ROOT}comedores/{comedor.pk}/", f"{ROOT}{expediente.pk}/"):
        for metodo in ("post", "put", "delete"):
            assert getattr(web, metodo)(url).status_code == 405, (url, metodo)
    assert web.put(f"{ROOT}{expediente.pk}/editar/").status_code == 405


def test_admindocs_head_does_not_bypass_the_web_api(client, comedor):
    expediente = _expediente(comedor)
    client.force_login(
        _ready(get_user_model().objects.create_user("staff_exp", is_staff=True))
    )

    for url in (
        f"{ROOT}comedores/{comedor.pk}/crear/",
        f"{ROOT}{expediente.pk}/editar/",
        f"{ROOT}{expediente.pk}/eliminar/",
    ):
        respuesta = client.head(url)
        assert respuesta.status_code == 403, url
        assert "X-View" not in respuesta
    assert "X-View" not in client.head(f"{ROOT}{expediente.pk}/")


@pytest.fixture(name="runtime")
def runtime_fixture():
    with override_settings(
        SISOC_BACKEND="comedores",
        ROOT_URLCONF="comedores_runtime.urls",
        SISOC_BACKENDS={},
        INTERNAL_IPS=[],
    ):
        yield


def _signed(user, client, *, target, method="GET"):
    return web_gate.sign(
        audience="comedores",
        user_pk=user.pk,
        session_key=client.cookies[settings.SESSION_COOKIE_NAME].value,
        method=method,
        target=target,
    )


@pytest.mark.usefixtures("runtime")
def test_runtime_serves_signed_reads_and_writes_only(web, tecnico, comedor):
    lista = f"{ROOT}comedores/{comedor.pk}/"
    assert (
        web.get(
            lista,
            RAW_URI=lista,
            HTTP_X_SISOC_WEB_GATE=_signed(tecnico, web, target=lista),
        ).status_code
        == 200
    )
    target = f"{ROOT}comedores/{comedor.pk}/crear/"
    sin_firma = web.post(target, _completo(), RAW_URI=target)
    firmado_get = web.post(
        target,
        _completo(),
        RAW_URI=target,
        HTTP_X_SISOC_WEB_GATE=_signed(tecnico, web, target=target),
    )
    assert sin_firma.status_code == firmado_get.status_code == 403
    assert ExpedientePago.objects.count() == 0
    firmado = web.post(
        target,
        _completo(),
        RAW_URI=target,
        HTTP_X_SISOC_WEB_GATE=_signed(tecnico, web, target=target, method="POST"),
    )
    assert firmado.status_code == 200
    assert ExpedientePago.objects.filter(comedor=comedor).count() == 1
