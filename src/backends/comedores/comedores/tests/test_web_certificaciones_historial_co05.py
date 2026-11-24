"""Web API (G1 v1) of the monthly certifications history: ``/api/web/comedores/comedores/`` (CO05.01).

The endpoint runs the native ``CertificacionesPrestacionesHistorialView``; these tests
compare the JSON with what ``certificaciones_prestaciones_historial.html`` shows (rows,
filters, ordering, pages, links), check the native guards and that reading never writes.
"""

from datetime import date, datetime, timezone

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.base import ContentFile
from django.test import Client
from django.urls import reverse

from comedores.models import Comedor, PrestacionAlimentariaConformidad

pytestmark = pytest.mark.django_db


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
    return _client("lector_certificaciones_co05", "view_comedor")


def _url(comedor):
    return f"/api/web/comedores/comedores/{comedor.pk}/certificaciones-prestaciones/"


def _certificacion(comedor, periodo, conforme=True, usuario=None, pdf=False):
    item = PrestacionAlimentariaConformidad.objects.create(
        comedor=comedor, periodo=periodo, conforme=conforme, usuario=usuario
    )
    if pdf:
        item.certificacion_pdf.save("c.pdf", ContentFile(b"%PDF-1.4"), save=True)
    # ``creado`` is ``auto_now_add``: pin it to a known instant (UTC -> local on render).
    PrestacionAlimentariaConformidad.objects.filter(pk=item.pk).update(
        creado=datetime(2026, 10, 26, 15, 30, tzinfo=timezone.utc)
    )
    return item


@pytest.fixture(name="escenario")
def escenario_fixture():
    comedor = Comedor.objects.create(nombre="Comedor Certificaciones")
    ana = get_user_model().objects.create_user(
        "ana_cert_co05", first_name="Ana", last_name="Gómez"
    )
    solo = get_user_model().objects.create_user("solo_cert_co05")
    octubre = _certificacion(comedor, date(2026, 10, 1), True, ana, pdf=True)
    _certificacion(comedor, date(2026, 9, 1), False, solo)
    _certificacion(comedor, date(2026, 8, 1), True)
    _certificacion(Comedor.objects.create(nombre="Otro"), date(2026, 10, 1), True, ana)
    return {"comedor": comedor, "ana": ana, "solo": solo, "octubre": octubre}


def _json(web, comedor, **params):
    respuesta = web.get(_url(comedor), params)
    assert respuesta.status_code == 200, respuesta.content[:400]
    return respuesta.json()


def test_rows_match_the_native_template(web, escenario):
    comedor = escenario["comedor"]
    datos = _json(web, comedor)

    assert datos["comedor"] == {"id": comedor.pk, "nombre": "Comedor Certificaciones"}
    # Native order -periodo, -creado; other comedores' rows never appear.
    filas = datos["certificaciones"]
    assert [(c["periodo"], c["usuario"], c["conforme"]) for c in filas] == [
        ("10/2026", "Ana Gómez", True),
        ("09/2026", "solo_cert_co05", False),
        ("08/2026", "-", True),
    ]
    assert filas[0]["creado"] == "26/10/2026 12:30"
    assert filas[0]["pdf_url"] == reverse(
        "descargar_certificacion_prestaciones_web",
        args=[comedor.pk, escenario["octubre"].pk],
    )
    assert filas[1]["pdf_url"] is None
    assert datos["filtros"] == {"periodo": "", "usuario": "", "conforme": ""}
    # Native order: first name, last name, username (no first name sorts first).
    assert datos["generadores"] == [
        {"id": escenario["solo"].pk, "label": "solo_cert_co05"},
        {"id": escenario["ana"].pk, "label": "Ana Gómez"},
    ]
    assert datos["urls"] == {
        "comedores": "/comedores/listar",
        "comedor": f"/comedores/{comedor.pk}",
        "historial": f"/comedores/{comedor.pk}/certificaciones-prestaciones/",
    }
    assert datos["page"]["count"] == 3
    assert datos["page"]["is_paginated"] is False


def test_filters_follow_the_native_rules(web, escenario):
    comedor = escenario["comedor"]

    por_periodo = _json(web, comedor, periodo="2026-09")
    assert [c["periodo"] for c in por_periodo["certificaciones"]] == ["09/2026"]
    assert por_periodo["filtros"]["periodo"] == "2026-09"
    # An invalid period is ignored, like the native view.
    assert len(_json(web, comedor, periodo="basura")["certificaciones"]) == 3
    por_usuario = _json(web, comedor, usuario=str(escenario["ana"].pk))
    assert [c["usuario"] for c in por_usuario["certificaciones"]] == ["Ana Gómez"]
    assert len(_json(web, comedor, usuario="abc")["certificaciones"]) == 3
    no_conformes = _json(web, comedor, conforme="false")["certificaciones"]
    assert [c["conforme"] for c in no_conformes] == [False]
    assert len(_json(web, comedor, conforme="true")["certificaciones"]) == 2
    assert len(_json(web, comedor, conforme="otro")["certificaciones"]) == 3


def test_twenty_per_page_and_invalid_page_is_404(web, escenario):
    comedor = escenario["comedor"]
    for indice in range(20):
        _certificacion(comedor, date(2020 + indice // 12, indice % 12 + 1, 1))

    primera = _json(web, comedor)
    segunda = _json(web, comedor, page=2)

    assert len(primera["certificaciones"]) == 20
    assert len(segunda["certificaciones"]) == 3
    assert primera["page"]["count"] == 23
    assert primera["page"]["is_paginated"] is True
    assert primera["page"]["next"] == 2
    assert segunda["page"]["previous"] == 1
    assert web.get(_url(comedor), {"page": 9}).status_code == 404


def test_guards_are_the_native_ones(web, escenario):
    comedor = escenario["comedor"]
    sin_permiso = _client("sin_permiso_cert_co05")

    assert Client().get(_url(comedor)).status_code in (401, 403)
    assert sin_permiso.get(_url(comedor)).status_code == 403
    assert web.get(_url(Comedor(pk=999999))).status_code == 404


def test_post_is_not_allowed_and_nothing_is_written(web, escenario):
    comedor = escenario["comedor"]
    antes = PrestacionAlimentariaConformidad.objects.count()

    respuesta = web.post(_url(comedor), {"conforme": "true"})

    assert respuesta.status_code in (403, 405)
    assert PrestacionAlimentariaConformidad.objects.count() == antes
