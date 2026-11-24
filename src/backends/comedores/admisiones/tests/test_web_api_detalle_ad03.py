"""Web API (G1 v1) of the admision detail page (AD03.01)."""

from decimal import Decimal

import types

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.db import models
from django.test import Client, override_settings
from django.utils import timezone

from admisiones.models.admisiones import (
    Admision,
    HistorialEstadosAdmision,
    InformeComplementario,
    InformeTecnico,
)
from admisiones.web_preview_seguimiento import seguimiento_preview_patterns
from comedores.models import Comedor
from config.urls_all import urlpatterns as monolith_patterns

API = "/api/web/comedores/admisiones/"

pytestmark = pytest.mark.django_db


def _usuario(nombre, permiso=None, superuser=False, grupo=None):
    usuario = get_user_model().objects.create_user(nombre)
    perfil = usuario.profile
    perfil.acceso_web = True
    perfil.must_change_password = False
    perfil.needs_profile_confirmation = False
    perfil.save()
    if permiso:
        app, codigo = permiso.split(".")
        usuario.user_permissions.add(
            Permission.objects.get(content_type__app_label=app, codename=codigo)
        )
    if grupo:
        usuario.groups.add(Group.objects.get_or_create(name=grupo)[0])
    if superuser:
        usuario.is_superuser = True
        usuario.save()
    return usuario


def _cliente(usuario):
    client = Client()
    client.force_login(usuario)
    return client


def _valor(field):
    if field.choices:
        return field.choices[0][0]
    kinds = (
        (models.EmailField, "test@example.com"),
        (models.BooleanField, False),
        (models.DecimalField, Decimal("1.0")),
        (models.FloatField, 1.0),
        (models.DateTimeField, timezone.now()),
        (models.DateField, timezone.now().date()),
        (models.IntegerField, 1),
    )
    return next((v for k, v in kinds if isinstance(field, k)), "test")


def _informe(admision):
    datos = {}
    for field in InformeTecnico._meta.fields:
        autogen = field.primary_key or field.auto_created
        if autogen or getattr(field, "auto_now", False) or field.has_default():
            continue
        if getattr(field, "auto_now_add", False) or field.null:
            continue
        if not isinstance(field, models.ForeignKey):
            datos[field.name] = _valor(field)
    datos.update(admision=admision, tipo="base", estado="Iniciado")
    return InformeTecnico.objects.create(**datos)


@pytest.fixture(name="admision")
def admision_fixture():
    comedor = Comedor.objects.create(nombre="Comedor Detalle AD03")
    return Admision.objects.create(
        comedor=comedor,
        tipo="incorporacion",
        num_expediente="EX-2026-000000001- -APN-DGD#MCH",
        convenio_numero=4,
        vigente_pwa=True,
    )


def _url(admision, comedor_pk=None):
    return f"{API}{comedor_pk or admision.comedor_id}/{admision.pk}/detalle/"


def test_detail_projects_the_native_context(admision):
    web = _cliente(_usuario("lector_det", "comedores.view_comedor"))

    respuesta = web.get(_url(admision))

    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["id"] == admision.pk
    assert datos["comedor"] == {
        "id": admision.comedor_id,
        "nombre": "Comedor Detalle AD03",
    }
    assert datos["activa"] is True
    assert datos["admision"]["tipo"] == "Incorporación"
    assert datos["admision"]["convenio_numero"] == 4
    assert datos["admision"]["num_expediente"] == admision.num_expediente
    assert datos["admision"]["vigente_pwa"] is True
    assert datos["admision"]["estado_legales"] == "-"
    assert datos["dupla"] is None
    assert datos["documentos"] == []
    assert datos["informe_tecnico"] is None
    assert datos["rendicion_final"] is None
    assert datos["historial_estados"]["page"]["is_paginated"] is False
    assert datos["puede_forzar_cierre"] is False
    assert datos["puede_editar_convenio_numero"] is False
    assert datos["messages"] == []


def test_close_button_is_for_superusers_and_the_coordinator_group_while_active(
    admision,
):
    root = _cliente(_usuario("root_det", superuser=True))
    coord = _cliente(
        _usuario(
            "coord_det", "comedores.view_comedor", grupo="Coordinador Equipo Tecnico"
        )
    )

    assert root.get(_url(admision)).json()["puede_forzar_cierre"] is True
    assert coord.get(_url(admision)).json()["puede_forzar_cierre"] is True
    Admision.objects.filter(pk=admision.pk).update(
        activa=False, motivo_forzar_cierre="Cierre de prueba"
    )
    datos = root.get(_url(admision)).json()
    assert datos["puede_forzar_cierre"] is False
    assert datos["admision"]["motivo_cierre"] == "Cierre de prueba"
    assert datos["admision"]["fecha_cierre"] != "-"


def test_state_history_is_paginated_by_ten_with_its_own_parameter(admision):
    for numero in range(12):
        HistorialEstadosAdmision.objects.create(
            admision=admision, estado_anterior="a", estado_nuevo=f"n{numero}"
        )
    web = _cliente(_usuario("root_hist", superuser=True))

    primera = web.get(_url(admision)).json()["historial_estados"]
    segunda = web.get(
        _url(admision) + "?historial_estados_page=2&historial_page=1"
    ).json()["historial_estados"]

    assert primera["headers"] == ["Fecha", "Estado nuevo", "Estado anterior", "Usuario"]
    assert primera["page"]["param"] == "historial_estados_page"
    assert primera["page"]["next"] == 2
    assert segunda["page"]["number"] == 2
    assert "historial_page=1&" in segunda["page"]["query_without_page"]
    assert len(primera["rows"]) == 10


def test_complementary_reports_are_projected(admision):
    InformeComplementario.objects.create(
        admision=admision,
        informe_tecnico=_informe(admision),
        observaciones_legales="Falta firma",
    )
    web = _cliente(_usuario("root_comp", superuser=True))

    filas = web.get(_url(admision)).json()["complementarios"]

    assert len(filas) == 1
    assert filas[0]["observaciones"] == "Falta firma"
    assert (filas[0]["pdf"], filas[0]["pdf_final"], filas[0]["word_final"]) == (
        None,
        None,
        None,
    )


def test_access_and_lookups_are_the_native_ones(admision):
    url = _url(admision)
    assert Client().get(url).status_code in (401, 403)
    assert _cliente(_usuario("sin_permiso_det")).get(url).status_code == 403
    for permiso in (
        "comedores.view_comedor",
        "admisiones.view_admision",
        "acompanamientos.view_informacionrelevante",
    ):
        web = _cliente(_usuario(f"u_det_{permiso.split('.')[1]}", permiso))
        assert web.get(url).status_code == 200, permiso
    root = _cliente(_usuario("root_404", superuser=True))
    otro = Comedor.objects.create(nombre="Otro")
    assert root.get(_url(admision, otro.pk)).status_code == 404
    assert root.get(f"{API}{admision.comedor_id}/999999/detalle/").status_code == 404
    assert root.post(url, {}).status_code == 405
    # No per-object scope: a plain reader sees any admision, as the native view does.
    assert (
        _cliente(_usuario("lector_global", "admisiones.view_admision"))
        .get(url)
        .status_code
        == 200
    )


INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)


@pytest.fixture(name="preview")
def preview_fixture(tmp_path):
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    module = types.ModuleType("detalle_preview_test_urls")
    module.urlpatterns = seguimiento_preview_patterns(tmp_path) + list(
        monolith_patterns
    )
    with override_settings(ROOT_URLCONF=module):
        yield


@pytest.mark.usefixtures("preview")
def test_preview_serves_the_index_after_the_native_guards(admision):
    url = f"/comedores/{admision.comedor_id}/admision/{admision.pk}/detalle/"
    web = _cliente(_usuario("lector_prev_det", "comedores.view_comedor"))

    respuesta = web.get(url)

    assert respuesta.status_code == 200
    assert '/comedores/react/assets/app-1.js"' in respuesta.content.decode()
    assert Client().get(url).status_code in (302, 403)
    assert _cliente(_usuario("sin_permiso_prev_det")).get(url).status_code == 403
    assert web.get(url.replace(str(admision.comedor_id), "99999", 1)).status_code == 404
    assert (
        web.post(url, {"forzar_cierre": "1", "motivo_forzar_cierre": "x"}).status_code
        == 302
    )
