"""Web API (G1 v1) of the comedor "Agregar a Nómina" screen (CO01).

``/api/web/comedores/nomina-crear/`` runs the native ``NominaCreateView`` and
``NominaDirectaCreateView``: scoped lookups, citizen search, RENAPER lookup, the three forms
and the writes. A rejected request must write nothing.
"""

from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client

from admisiones.models.admisiones import Admision
from ciudadanos.models import Ciudadano, Sexo
from comedores.models import Comedor, Nomina, Programas
from comedores.services.comedor_service import ComedorService

ROOT = "/api/web/comedores/nomina-crear/"

pytestmark = pytest.mark.django_db


def _usuario(nombre, *codenames):
    usuario = get_user_model().objects.create_user(nombre, password="x")
    profile = usuario.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    for codename in codenames:
        usuario.user_permissions.add(Permission.objects.get(codename=codename))
    return usuario


def _cliente(usuario, **kwargs):
    client = Client(**kwargs)
    client.force_login(usuario)
    return client


@pytest.fixture(name="web")
def web_fixture():
    return _cliente(_usuario("gestor_nomina_crear", "add_nomina"))


@pytest.fixture(name="sexo")
def sexo_fixture():
    return Sexo.objects.get_or_create(sexo="Femenino")[0]


@pytest.fixture(name="directa")
def directa_fixture():
    programa = Programas.objects.create(
        nombre="Programa directo crear", usa_admision_para_nomina=False
    )
    return Comedor.objects.create(nombre="Comedor Directo Crear", programa=programa)


@pytest.fixture(name="con_admision")
def con_admision_fixture():
    comedor = Comedor.objects.create(nombre="Comedor Admision Crear")
    return comedor, Admision.objects.create(comedor=comedor)


@pytest.fixture(name="persona")
def persona_fixture(sexo):
    return Ciudadano.objects.create(
        nombre="Ana",
        apellido="Gómez",
        documento="30111222",
        sexo=sexo,
        fecha_nacimiento=date(2015, 1, 1),
    )


def _directa(comedor):
    return f"{ROOT}{comedor.pk}/"


def _admision(comedor, admision):
    return f"{ROOT}{comedor.pk}/admision/{admision.pk}/"


def _nominas(comedor):
    return Nomina.objects.filter(comedor=comedor).count()


def test_search_lists_the_matches_and_the_forms_like_the_native_page(
    web, directa, persona
):
    datos = web.get(_directa(directa), {"query": "30111222"}).json()

    assert datos["comedor"] == {
        "id": directa.pk,
        "nombre": "Comedor Directo Crear",
        "url": f"/comedores/{directa.pk}",
    }
    assert datos["query"] == "30111222"
    assert [c["documento"] for c in datos["ciudadanos"]] == ["30111222"]
    assert datos["ciudadanos"][0]["revision"] is False
    assert datos["show_form"] is False
    assert datos["mode"] == "con_dni"
    assert datos["pnud"] is False
    assert datos["cupo"] is None
    assert {f["name"] for f in datos["form_ciudadano"]["fields"]} >= {
        "apellido",
        "nombre",
        "documento",
        "fecha_nacimiento",
    }
    assert "motivo_sin_dni" in {f["name"] for f in datos["form_sin_dni"]["fields"]}
    assert [f["name"] for f in datos["form_extra"]["fields"]] == [
        "estado",
        "observaciones",
    ]
    assert [e["value"] for e in datos["estados"]] == ["activo", "espera", "baja"]
    assert len(datos["modal_fields"]) == 3
    assert datos["messages"] == []


def test_no_match_asks_renaper_and_preloads_the_form(web, directa, monkeypatch):
    monkeypatch.setattr(
        ComedorService,
        "obtener_datos_ciudadano_desde_renaper",
        staticmethod(
            lambda dni: {
                "success": True,
                "message": "Datos obtenidos de RENAPER.",
                "data": {"apellido": "Soto", "nombre": "Eva", "documento": dni},
            }
        ),
    )

    datos = web.get(_directa(directa), {"query": "40999888"}).json()

    assert datos["ciudadanos"] == []
    assert datos["show_form"] is True
    assert datos["renaper"] is True
    campos = {f["name"]: f for f in datos["form_ciudadano"]["fields"]}
    assert campos["apellido"]["value"] == "Soto"
    assert datos["messages"] == [
        {"message": "Datos obtenidos de RENAPER.", "tags": "info"}
    ]


def test_post_adds_an_existing_citizen_to_the_direct_nomina(web, directa, persona):
    respuesta = web.post(
        _directa(directa),
        {"ciudadano_id": persona.pk, "estado": "activo", "observaciones": "Nota"},
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "ok": True,
        "redirect": f"/comedores/{directa.pk}/nomina/",
    }
    nomina = Nomina.objects.get(comedor=directa)
    assert nomina.ciudadano_id == persona.pk
    assert nomina.observaciones == "Nota"
    mensajes = web.get(_directa(directa)).json()["messages"]
    assert [m["tags"] for m in mensajes] == ["success"]


def test_post_creates_a_citizen_and_adds_it_to_the_admission_nomina(
    web, con_admision, sexo
):
    comedor, admision = con_admision

    respuesta = web.post(
        _admision(comedor, admision),
        {
            "modo_creacion": "con_dni",
            "apellido": "Ruiz",
            "nombre": "Beto",
            "fecha_nacimiento": "2010-02-03",
            "tipo_documento": "DNI",
            "documento": "41222333",
            "sexo": sexo.pk,
            "estado": "espera",
            "observaciones": "",
        },
    )

    assert respuesta.status_code == 200, respuesta.content[:400]
    assert respuesta.json()["redirect"] == (
        f"/comedores/{comedor.pk}/admision/{admision.pk}/nomina/"
    )
    assert Nomina.objects.get(admision=admision).estado == "espera"
    assert Ciudadano.objects.filter(documento="41222333").exists()


def test_post_without_dni_creates_the_exceptional_citizen(web, directa, sexo):
    respuesta = web.post(
        _directa(directa),
        {
            "modo_creacion": "sin_dni",
            "apellido": "Sin",
            "nombre": "Documento",
            "fecha_nacimiento": "2012-04-05",
            "sexo": sexo.pk,
            "motivo_sin_dni": "",
            "estado": "activo",
        },
    )

    assert respuesta.status_code == 400
    datos = respuesta.json()
    assert datos["mode"] == "sin_dni"
    errores = {f["name"]: f["errors"] for f in datos["form_sin_dni"]["fields"]}
    assert errores["motivo_sin_dni"]
    assert _nominas(directa) == 0


def test_an_invalid_post_returns_the_bound_forms_and_writes_nothing(web, directa):
    respuesta = web.post(
        _directa(directa),
        {"modo_creacion": "con_dni", "apellido": "", "estado": "activo"},
    )

    assert respuesta.status_code == 400
    datos = respuesta.json()
    assert datos["show_form"] is True
    assert {f["name"] for f in datos["form_ciudadano"]["fields"] if f["errors"]}
    assert datos["messages"] == [
        {"message": "Revise los datos marcados en el formulario.", "tags": "warning"}
    ]
    assert _nominas(directa) == 0
    assert not Ciudadano.objects.exists()


def test_native_permission_scope_and_methods_decide_first(
    web, directa, con_admision, persona
):
    comedor, admision = con_admision
    otra = Admision.objects.create(comedor=Comedor.objects.create(nombre="Otra"))
    sin_permiso = _cliente(_usuario("sin_permiso_nomina_crear"))

    assert Client().get(_directa(directa)).status_code in (401, 403)
    assert sin_permiso.get(_directa(directa)).status_code == 403
    assert (
        sin_permiso.post(_directa(directa), {"ciudadano_id": persona.pk}).status_code
        == 403
    )
    # A direct nómina of a comedor that needs an admission, and a foreign admission: 404.
    assert web.get(_directa(comedor)).status_code == 404
    assert web.get(_admision(comedor, otra)).status_code == 404
    assert (
        web.post(_admision(comedor, otra), {"ciudadano_id": persona.pk}).status_code
        == 404
    )
    assert web.get(f"{ROOT}999999/").status_code == 404
    assert web.delete(_directa(directa)).status_code == 405
    assert (
        web.post(_directa(directa), "{}", content_type="application/json").status_code
        == 415
    )
    assert Nomina.objects.count() == 0
    assert admision.pk != otra.pk


def test_post_requires_the_csrf_token(directa, persona):
    client = _cliente(
        _usuario("csrf_nomina_crear", "add_nomina"), enforce_csrf_checks=True
    )

    assert (
        client.post(_directa(directa), {"ciudadano_id": persona.pk}).status_code == 403
    )
    assert _nominas(directa) == 0
