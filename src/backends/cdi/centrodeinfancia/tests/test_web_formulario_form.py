"""Web API (G1 v1) of the CDI institutional form create and edit screens (CDI03).

``/api/web/cdi/centros/<pk>/formularios/crear/`` and ``.../<form_pk>/editar/``
run the native create and update views, so every write goes through
``FormularioCDIForm``, the three fixed formsets and the native transaction. The
native behaviour the contract asks not to correct (the edit GET creating the
missing fixed rows, the POST saving with ``save(commit=False)``) is compared
with the native URLs, not asserted by name.
"""

from datetime import date
from urllib.parse import urlencode

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.test import Client, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils.html import escape
from django.utils import timezone

from centrodeinfancia.formulario_cdi_schema import (
    OPCIONES_GRUPO_ETARIO_DEMANDA,
    OPCIONES_GRUPO_ETARIO_SALAS,
    OPCIONES_INSTITUCIONES_ARTICULACION,
)
from centrodeinfancia.models import (
    AccesoCDI,
    CentroDeInfancia,
    FormularioCDI,
    FormularioCDIArticulationFrequency,
    FormularioCDIHorarioFuncionamiento,
    FormularioCDIRoomDistribution,
    FormularioCDIWaitlistByAgeGroup,
)
from core import web_gate
from core.constants import UserGroups
from core.models import Provincia

ALTA = "centrodeinfancia.add_formulariocdi"
EDICION = "centrodeinfancia.change_formulariocdi"
VER = "centrodeinfancia.view_formulariocdi"
VETO = "El rol Auditoría tiene acceso de solo lectura."
WRITES = ("INSERT", "UPDATE", "DELETE")

pytestmark = pytest.mark.django_db


def _crear(centro_pk):
    return f"/api/web/cdi/centros/{centro_pk}/formularios/crear/"


def _editar(centro_pk, form_pk):
    return f"/api/web/cdi/centros/{centro_pk}/formularios/{form_pk}/editar/"


def _ready(user):
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    return User.objects.get(pk=user.pk)


def _permiso(codigo):
    app, codename = codigo.split(".")
    permiso = Permission.objects.filter(
        content_type__app_label=app, codename=codename
    ).first()
    return permiso or Permission.objects.create(
        content_type=ContentType.objects.get_for_model(Group),
        codename=codename,
        name=codename,
    )


def _usuario(username, *, perms=(ALTA, EDICION, VER), superuser=False, grupos=()):
    user = User.objects.create_user(username=username, is_superuser=superuser)
    for codigo in perms:
        user.user_permissions.add(_permiso(codigo))
    for nombre in grupos:
        user.groups.add(Group.objects.get_or_create(name=nombre)[0])
    return _ready(user)


def _cliente(user, **kwargs):
    client = Client(**kwargs)
    client.force_login(user)
    return client


@pytest.fixture(name="datos")
def datos_fixture():
    provincia = Provincia.objects.create(nombre="Mendoza")
    centro = CentroDeInfancia.objects.create(
        nombre="CDI Girasoles", provincia=provincia, codigo_cdi="CDI-7"
    )
    otro = CentroDeInfancia.objects.create(nombre="CDI Ajeno", provincia=provincia)
    return {"centro": centro, "otro": otro}


def _payload_alta(centro, **cambios):
    payload = {
        "fecha_relevamiento": "2026-03-13",
        "nombre_completo_respondente": "Ana Perez",
        "nombre_cdi": centro.nombre,
        "codigo_cdi": centro.codigo_cdi,
        "dias_funcionamiento": ["lunes", "martes"],
        "horario_lunes_apertura": "08:00",
        "horario_lunes_cierre": "16:00",
    }
    for prefijo, opciones, clave in (
        ("distribucion_salas", OPCIONES_GRUPO_ETARIO_SALAS, "grupo_etario"),
        (
            "demanda_insatisfecha_por_grupo_etario",
            OPCIONES_GRUPO_ETARIO_DEMANDA,
            "grupo_etario",
        ),
        (
            "frecuencia_articulacion",
            OPCIONES_INSTITUCIONES_ARTICULACION,
            "tipo_institucion",
        ),
    ):
        payload[f"{prefijo}-TOTAL_FORMS"] = str(len(opciones))
        payload[f"{prefijo}-INITIAL_FORMS"] = "0"
        payload[f"{prefijo}-MIN_NUM_FORMS"] = "0"
        payload[f"{prefijo}-MAX_NUM_FORMS"] = "1000"
        for indice, (valor, _etiqueta) in enumerate(opciones):
            payload[f"{prefijo}-{indice}-{clave}"] = valor
    payload["distribucion_salas-0-cantidad_salas"] = "2"
    payload["distribucion_salas-0-cantidad_personal_sala"] = "4"
    payload.update(cambios)
    return payload


def _payload_edicion(formulario, **cambios):
    payload = {
        "fecha_relevamiento": (
            formulario.fecha_relevamiento.isoformat()
            if formulario.fecha_relevamiento
            else ""
        ),
        "nombre_completo_respondente": formulario.nombre_completo_respondente or "",
        "nombre_cdi": formulario.nombre_cdi or "",
        "codigo_cdi": formulario.codigo_cdi or "",
        "dias_funcionamiento": formulario.dias_funcionamiento or [],
    }
    for prefijo, filas, campos in (
        (
            "distribucion_salas",
            formulario.filas_distribucion_salas.order_by("id"),
            ("grupo_etario",),
        ),
        (
            "demanda_insatisfecha_por_grupo_etario",
            formulario.filas_demanda_insatisfecha.order_by("id"),
            ("grupo_etario",),
        ),
        (
            "frecuencia_articulacion",
            formulario.filas_articulacion.order_by("id"),
            ("tipo_institucion", "frecuencia"),
        ),
    ):
        filas = list(filas)
        payload[f"{prefijo}-TOTAL_FORMS"] = str(len(filas))
        payload[f"{prefijo}-INITIAL_FORMS"] = str(len(filas))
        payload[f"{prefijo}-MIN_NUM_FORMS"] = "0"
        payload[f"{prefijo}-MAX_NUM_FORMS"] = "1000"
        for indice, fila in enumerate(filas):
            payload[f"{prefijo}-{indice}-id"] = str(fila.pk)
            for campo in campos:
                payload[f"{prefijo}-{indice}-{campo}"] = getattr(fila, campo) or ""
    payload.update(cambios)
    return payload


def _enviar(client, url, datos):
    return client.post(
        url,
        urlencode(datos, doseq=True),
        content_type="application/x-www-form-urlencoded",
    )


def _borrar_filas(formulario):
    """Physical delete (the models soft delete) of two fixed rows' worth of data."""
    # pylint: disable=protected-access
    FormularioCDIRoomDistribution.all_objects.filter(formulario=formulario)._raw_delete(
        "default"
    )
    FormularioCDIArticulationFrequency.all_objects.filter(
        formulario=formulario, tipo_institucion="cultura_iglesias"
    )._raw_delete("default")


def _estado():
    return {
        "formularios": list(FormularioCDI.all_objects.order_by("pk").values()),
        "salas": FormularioCDIRoomDistribution.all_objects.count(),
        "demanda": FormularioCDIWaitlistByAgeGroup.all_objects.count(),
        "articulacion": FormularioCDIArticulationFrequency.all_objects.count(),
        "horarios": FormularioCDIHorarioFuncionamiento.objects.count(),
    }


# --- Create: the native page, as JSON ------------------------------------------------


def test_create_form_projects_the_native_markup_and_the_three_fixed_formsets(datos):
    client = _cliente(_usuario("ff-paridad", superuser=True))
    centro = datos["centro"]

    api = client.get(_crear(centro.pk))
    nativo = client.get(reverse("centrodeinfancia_formulario_crear", args=[centro.pk]))

    assert api.status_code == 200
    assert api["Content-Type"] == "application/json"
    assert api["Cache-Control"] == "private, no-store"
    assert "csrftoken" in api.cookies
    data = api.json()
    html = nativo.content.decode()
    campos = [c for s in data["sections"] for fila in s["rows"] for c in fila]
    assert len(campos) > 60
    for campo in campos:
        assert campo["html"] in html, campo["name"]
        assert campo["col_class"] in ("col-md-6", "col-12")
    for horario in data["horarios"]:
        assert horario["apertura"] in html and horario["cierre"] in html
    assert [
        len(data["formsets"][n]["rows"]) for n in ("salas", "demanda", "articulacion")
    ] == [
        len(OPCIONES_GRUPO_ETARIO_SALAS),
        len(OPCIONES_GRUPO_ETARIO_DEMANDA),
        len(OPCIONES_INSTITUCIONES_ARTICULACION),
    ]
    for formset in data["formsets"].values():
        assert {m["name"].split("-")[-1] for m in formset["management"]} == {
            "TOTAL_FORMS",
            "INITIAL_FORMS",
            "MIN_NUM_FORMS",
            "MAX_NUM_FORMS",
        }
        assert all(f'name="{m["name"]}"' in html for m in formset["management"])
        for fila in formset["rows"]:
            assert all(f'name="{h["name"]}"' in html for h in fila["hidden"])
            assert [h["name"].split("-")[-1] for h in fila["hidden"]][0] == "id"
            assert escape(fila["label"]) in html and fila["label"]
            for celda in fila["cells"]:
                assert celda["html"] in html and celda["errors"] == []
    assert data["is_edit"] is False
    assert data["has_errors"] is False
    assert data["centro"]["nombre"] == "CDI Girasoles"
    assert data["centro"]["codigo"] == "CDI-7"
    assert data["centro"]["cancelar_url"] == f"/centrodeinfancia/detalle/{centro.pk}"
    assert (
        data["centro"]["listado_url"] == f"/centrodeinfancia/{centro.pk}/formularios/"
    )
    assert 'value="CDI Girasoles"' in next(
        c["html"] for c in campos if c["name"] == "nombre_cdi"
    )
    assert not FormularioCDI.objects.exists()


def test_a_centre_without_code_shows_the_native_placeholder(datos):
    CentroDeInfancia.objects.filter(pk=datos["centro"].pk).update(codigo_cdi=None)
    client = _cliente(_usuario("ff-sin-codigo", superuser=True))

    data = client.get(_crear(datos["centro"].pk)).json()

    assert data["centro"]["codigo"] == "Sin codigo"


# --- Create: writes -------------------------------------------------------------------


def test_valid_create_persists_form_rows_and_follows_the_native_redirect(datos):
    user = _usuario("ff-alta")
    client = _cliente(user)
    centro = datos["centro"]

    respuesta = _enviar(client, _crear(centro.pk), _payload_alta(centro))

    assert respuesta.status_code == 200
    formulario = FormularioCDI.objects.get()
    assert respuesta.json() == {
        "ok": True,
        "redirect": f"/centrodeinfancia/{centro.pk}/formularios/{formulario.pk}/",
    }
    assert formulario.centro_id == centro.pk
    assert formulario.created_by_id == user.pk
    assert formulario.fecha_relevamiento == date(2026, 3, 13)
    assert formulario.dias_funcionamiento == ["lunes", "martes"]
    assert formulario.filas_distribucion_salas.count() == 6
    assert formulario.filas_demanda_insatisfecha.count() == 6
    assert formulario.filas_articulacion.count() == 15
    sala = formulario.filas_distribucion_salas.get(grupo_etario="lactantes")
    assert (sala.cantidad_salas, sala.cantidad_personal_sala) == (2, 4)
    mensajes = client.get(_crear(centro.pk)).json()["messages"]
    assert mensajes == [
        {
            "message": f"Formulario #{formulario.pk} creado correctamente.",
            "level": "success",
        }
    ]


@pytest.mark.parametrize(
    ("cambios", "campo"),
    [
        ({"dias_funcionamiento": []}, "dias_funcionamiento"),
        ({"email_cdi": "no-es-un-correo"}, "email_cdi"),
        ({"telefono_cdi": "abc"}, "telefono_cdi"),
    ],
)
def test_a_rejected_create_is_a_400_with_the_native_errors_and_no_effects(
    datos, cambios, campo
):
    client = _cliente(_usuario("ff-rechazo"))
    antes = _estado()

    respuesta = _enviar(
        client, _crear(datos["centro"].pk), _payload_alta(datos["centro"], **cambios)
    )

    assert respuesta.status_code == 400
    data = respuesta.json()
    assert data["has_errors"] is True
    campos = {
        c["name"]: c["html"] for s in data["sections"] for f in s["rows"] for c in f
    }
    assert "is-invalid" in campos[campo] or "invalid-feedback" in campos[campo]
    assert _estado() == antes


def test_a_rejected_formset_row_reports_its_cell_errors_and_keeps_the_typed_values(
    datos,
):
    client = _cliente(_usuario("ff-fila"))
    antes = _estado()

    respuesta = _enviar(
        client,
        _crear(datos["centro"].pk),
        _payload_alta(datos["centro"], **{"distribucion_salas-1-cantidad_salas": "-3"}),
    )

    assert respuesta.status_code == 400
    data = respuesta.json()
    fila = data["formsets"]["salas"]["rows"][1]
    assert fila["cells"][0]["errors"]
    assert 'value="-3"' in fila["cells"][0]["html"]
    assert data["formsets"]["salas"]["rows"][0]["cells"][0]["errors"] == []
    assert any(
        m["name"].endswith("TOTAL_FORMS")
        for m in data["formsets"]["salas"]["management"]
    )
    assert data["has_errors"] is True
    assert _estado() == antes


def test_a_tampered_management_form_is_rejected_without_effects(datos):
    client = _cliente(_usuario("ff-management"))
    antes = _estado()

    respuesta = _enviar(
        client,
        _crear(datos["centro"].pk),
        _payload_alta(datos["centro"], **{"distribucion_salas-TOTAL_FORMS": "abc"}),
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["formsets"]["salas"]["non_form_errors"]
    assert _estado() == antes


# --- Edit -------------------------------------------------------------------------------


@pytest.fixture(name="formulario")
def formulario_fixture(datos):
    client = _cliente(_usuario("ff-semilla", superuser=True))
    _enviar(client, _crear(datos["centro"].pk), _payload_alta(datos["centro"]))
    return FormularioCDI.objects.get()


def test_edit_form_shows_the_instance_and_keeps_the_historic_snapshot(
    datos, formulario
):
    CentroDeInfancia.objects.filter(pk=datos["centro"].pk).update(nombre="Nombre nuevo")
    client = _cliente(_usuario("ff-editar-ver"))
    centro = datos["centro"]

    data = client.get(_editar(centro.pk, formulario.pk)).json()
    nativo = client.get(
        reverse("centrodeinfancia_formulario_editar", args=[centro.pk, formulario.pk])
    ).content.decode()

    assert data["is_edit"] is True
    campos = {
        c["name"]: c["html"] for s in data["sections"] for f in s["rows"] for c in f
    }
    assert 'value="CDI Girasoles"' in campos["nombre_cdi"]
    for html in campos.values():
        assert html in nativo
    assert data["centro"]["cancelar_url"] == (
        f"/centrodeinfancia/{centro.pk}/formularios/{formulario.pk}/"
    )
    assert data["formsets"]["salas"]["rows"][0]["cells"][0]["html"]


def test_the_edit_get_creates_the_missing_fixed_rows_exactly_like_the_native_url(
    datos, formulario
):
    centro = datos["centro"]
    client = _cliente(_usuario("ff-filas", superuser=True))
    _borrar_filas(formulario)
    antes = _estado()

    nativo = client.get(
        reverse("centrodeinfancia_formulario_editar", args=[centro.pk, formulario.pk])
    )
    tras_nativo = _estado()
    _borrar_filas(formulario)
    client.get(_editar(centro.pk, formulario.pk))
    tras_api = _estado()

    assert nativo.status_code == 200
    assert (antes["salas"], antes["articulacion"]) == (0, 14)
    assert (tras_nativo["salas"], tras_nativo["articulacion"]) == (6, 15)
    assert (tras_api["salas"], tras_api["articulacion"]) == (6, 15)
    assert tras_api["demanda"] == tras_nativo["demanda"]


def test_valid_edit_updates_in_place_and_keeps_the_author_and_the_code(
    datos, formulario
):
    otro_usuario = _usuario("ff-editor")
    client = _cliente(otro_usuario)
    centro = datos["centro"]
    cambios = _payload_edicion(
        formulario,
        nombre_completo_respondente="Otra Persona",
        codigo_cdi="HACK",
        **{"distribucion_salas-0-cantidad_salas": "9"},
    )

    respuesta = _enviar(client, _editar(centro.pk, formulario.pk), cambios)

    assert respuesta.status_code == 200
    formulario.refresh_from_db()
    assert formulario.nombre_completo_respondente == "Otra Persona"
    assert formulario.codigo_cdi == "CDI-7"
    assert formulario.created_by_id != otro_usuario.pk
    assert (
        formulario.filas_distribucion_salas.order_by("id").first().cantidad_salas == 9
    )
    assert FormularioCDI.objects.count() == 1
    assert client.get(_editar(centro.pk, formulario.pk)).json()["messages"] == [
        {
            "message": f"Formulario #{formulario.pk} actualizado correctamente.",
            "level": "success",
        }
    ]


def test_the_post_schedule_outcome_is_the_one_of_the_native_url(datos, formulario):
    centro = datos["centro"]
    client = _cliente(_usuario("ff-horarios", superuser=True))
    cambios = _payload_edicion(
        formulario,
        horario_martes_apertura="09:00",
        horario_martes_cierre="17:00",
        horario_lunes_apertura="07:00",
    )

    _enviar(client, _editar(centro.pk, formulario.pk), cambios)
    horarios_api = sorted(
        FormularioCDIHorarioFuncionamiento.objects.values_list(
            "dia", "hora_apertura", "hora_cierre"
        )
    )
    FormularioCDIHorarioFuncionamiento.objects.all().delete()
    client.post(
        reverse("centrodeinfancia_formulario_editar", args=[centro.pk, formulario.pk]),
        cambios,
    )
    horarios_nativo = sorted(
        FormularioCDIHorarioFuncionamiento.objects.values_list(
            "dia", "hora_apertura", "hora_cierre"
        )
    )

    assert horarios_api == horarios_nativo


def test_a_rejected_edit_changes_nothing(datos, formulario):
    client = _cliente(_usuario("ff-editar-rechazo"))
    antes = _estado()

    respuesta = _enviar(
        client,
        _editar(datos["centro"].pk, formulario.pk),
        _payload_edicion(formulario, dias_funcionamiento=[]),
    )

    assert respuesta.status_code == 400
    assert _estado() == antes


# --- Scope, permissions and the auditor veto ---------------------------------------------


def test_scope_and_nested_ids_are_enforced(datos, formulario):
    user = _usuario("ff-referente")
    AccesoCDI.objects.create(user=user, centro=datos["centro"])
    cliente = _cliente(user)
    ajeno = FormularioCDI.objects.create(centro=datos["otro"])
    antes = _estado()

    assert cliente.get(_crear(datos["centro"].pk)).status_code == 200
    assert cliente.get(_editar(datos["centro"].pk, formulario.pk)).status_code == 200
    assert cliente.get(_crear(datos["otro"].pk)).status_code == 404
    assert (
        _enviar(
            cliente, _crear(datos["otro"].pk), _payload_alta(datos["otro"])
        ).status_code
        == 404
    )
    assert cliente.get(_editar(datos["otro"].pk, ajeno.pk)).status_code == 404
    assert cliente.get(_editar(datos["centro"].pk, ajeno.pk)).status_code == 404
    assert (
        _enviar(
            cliente, _editar(datos["centro"].pk, ajeno.pk), _payload_edicion(ajeno)
        ).status_code
        == 404
    )
    assert _estado() == antes


def test_the_url_permission_is_required_for_each_screen(datos, formulario):
    solo_alta = _cliente(_usuario("ff-solo-alta", perms=(ALTA,)))
    solo_edicion = _cliente(_usuario("ff-solo-edicion", perms=(EDICION,)))
    solo_ver = _cliente(_usuario("ff-solo-ver", perms=(VER,)))
    centro = datos["centro"]
    antes = _estado()

    assert solo_alta.get(_crear(centro.pk)).status_code == 200
    assert solo_alta.get(_editar(centro.pk, formulario.pk)).status_code == 403
    assert solo_edicion.get(_crear(centro.pk)).status_code == 403
    assert (
        _enviar(solo_edicion, _crear(centro.pk), _payload_alta(centro)).status_code
        == 403
    )
    assert solo_edicion.get(_editar(centro.pk, formulario.pk)).status_code == 200
    assert solo_ver.get(_crear(centro.pk)).status_code == 403
    assert solo_ver.get(_editar(centro.pk, formulario.pk)).status_code == 403
    assert _estado() == antes


@pytest.mark.parametrize(
    "grupos",
    [
        [UserGroups.SIMEPI_AUDITORIA],
        [UserGroups.SIMEPI_AUDITORIA, UserGroups.SIMEPI_EGP],
    ],
    ids=["auditoria", "auditoria_egp"],
)
def test_auditor_posts_are_rejected_before_anything_is_saved(datos, formulario, grupos):
    client = _cliente(_usuario("ff-veto-" + str(len(grupos)), grupos=grupos))
    centro = datos["centro"]
    antes = _estado()

    alta = _enviar(client, _crear(centro.pk), _payload_alta(centro))
    edicion = _enviar(
        client, _editar(centro.pk, formulario.pk), _payload_edicion(formulario)
    )
    lectura = client.get(_crear(centro.pk))

    assert alta.status_code == 403 and alta.json() == {"detail": VETO}
    assert edicion.status_code == 403 and edicion.json() == {"detail": VETO}
    assert lectura.status_code == 200
    assert _estado() == antes


def test_creating_reads_never_write(datos, formulario):
    client = _cliente(_usuario("ff-lectura", superuser=True))
    client.get(_crear(datos["centro"].pk))

    with CaptureQueriesContext(connection) as queries:
        assert client.get(_crear(datos["centro"].pk)).status_code == 200

    assert not [
        q["sql"] for q in queries.captured_queries if q["sql"].startswith(WRITES)
    ]


def test_csrf_format_and_methods_are_enforced(datos, formulario):
    user = _usuario("ff-transporte")
    estricto = _cliente(user, enforce_csrf_checks=True)
    client = _cliente(user)
    centro = datos["centro"]
    antes = _estado()

    assert estricto.post(_crear(centro.pk), _payload_alta(centro)).status_code == 403
    assert (
        client.post(
            _crear(centro.pk), "{}", content_type="application/json"
        ).status_code
        == 415
    )
    assert client.put(_crear(centro.pk)).status_code == 405
    assert client.delete(_editar(centro.pk, formulario.pk)).status_code == 405
    assert _estado() == antes


def test_anonymous_gets_401_json_and_the_pending_requirement_is_reported(datos):
    destino = _crear(datos["centro"].pk)
    pendiente = _usuario("ff-pendiente", superuser=True)
    pendiente.profile.must_change_password = True
    pendiente.profile.save()
    cliente = _cliente(pendiente)
    falso = web_gate.sign(
        audience="cdi",
        user_pk=pendiente.pk,
        session_key=cliente.cookies[settings.SESSION_COOKIE_NAME].value,
        method="GET",
        target=destino,
    )

    anonimo = Client().get(destino)
    rechazo = cliente.get(destino, HTTP_X_SISOC_WEB_GATE=falso, RAW_URI=destino)

    assert anonimo.status_code == 401
    assert anonimo.json() == {"detail": web_gate.DETAIL_UNAUTHENTICATED}
    assert rechazo.status_code == 403
    assert rechazo.json()["detail"] == web_gate.DETAIL_REQUIREMENT


def test_admindocs_head_does_not_bypass_the_web_api(datos):
    staff = User.objects.create_user("ff-staff", is_staff=True)

    respuesta = _cliente(_ready(staff)).head(_crear(datos["centro"].pk))

    assert "X-View" not in respuesta
    assert respuesta.status_code == 403


# --- Runtime: only the core's signed attestation reaches the view -------------------------


@pytest.fixture(name="runtime")
def runtime_fixture():
    with override_settings(
        SISOC_BACKEND="cdi",
        ROOT_URLCONF="cdi_runtime.urls",
        SISOC_BACKENDS={},
        INTERNAL_IPS=[],
    ):
        yield


def _signed(user, client, target, *, method="GET", now=None, audience="cdi"):
    return web_gate.sign(
        audience=audience,
        user_pk=user.pk,
        session_key=client.cookies[settings.SESSION_COOKIE_NAME].value,
        method=method,
        target=target,
        now=now,
    )


@pytest.mark.usefixtures("runtime")
def test_runtime_serves_a_signed_request_and_rejects_bad_ones(datos):
    user = _usuario("ff-runtime", superuser=True)
    client = _cliente(user)
    destino = _crear(datos["centro"].pk)
    valido = _signed(user, client, destino)

    ok = client.get(destino, RAW_URI=destino, HTTP_X_SISOC_WEB_GATE=valido)

    assert ok.status_code == 200
    alterados = {
        "missing": None,
        "other_target": _signed(user, client, destino + "?x=1"),
        "other_audience": _signed(user, client, destino, audience="inspecciones"),
        "other_method": _signed(user, client, destino, method="POST"),
        "expired": _signed(user, client, destino, now=timezone.now().timestamp() - 61),
    }
    for motivo, token in alterados.items():
        extra = {"RAW_URI": destino}
        if token is not None:
            extra["HTTP_X_SISOC_WEB_GATE"] = token
        rechazo = client.get(destino, **extra)
        assert rechazo.status_code == 403, motivo
        assert rechazo.json() == {"detail": web_gate.DETAIL_REJECTED}, motivo


@pytest.mark.usefixtures("runtime")
def test_runtime_keeps_the_permission_and_the_auditor_veto_after_a_valid_attestation(
    datos,
):
    destino = _crear(datos["centro"].pk)
    sin = _usuario("ff-runtime-sin", perms=())
    auditor = _usuario("ff-runtime-auditor", grupos=[UserGroups.SIMEPI_AUDITORIA])
    c_sin, c_aud = _cliente(sin), _cliente(auditor)

    denegado = c_sin.get(
        destino, RAW_URI=destino, HTTP_X_SISOC_WEB_GATE=_signed(sin, c_sin, destino)
    )
    veto = c_aud.post(
        destino,
        urlencode(_payload_alta(datos["centro"]), doseq=True),
        content_type="application/x-www-form-urlencoded",
        RAW_URI=destino,
        HTTP_X_SISOC_WEB_GATE=_signed(auditor, c_aud, destino, method="POST"),
    )

    assert denegado.status_code == 403
    assert denegado.json() != {"detail": web_gate.DETAIL_REJECTED}
    assert veto.status_code == 403
    assert veto.json() == {"detail": VETO}
    assert not FormularioCDI.objects.exists()
