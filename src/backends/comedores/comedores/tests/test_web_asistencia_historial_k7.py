"""Web API (G1 v1) of the nómina attendance history: ``/api/web/comedores/comedores/`` (CO01).

The endpoint runs the native ``NominaAsistenciaHistorialView``; these tests compare the
JSON with what ``nomina_asistencia_historial.html`` shows, check the native guards
(permission, scope, admission of the comedor) and that reading never writes.
"""

from datetime import date, datetime, timezone

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.base import ContentFile
from django.test import Client

from admisiones.models.admisiones import Admision
from ciudadanos.models import Ciudadano, Sexo
from comedores.models import Comedor, Nomina
from pwa.models import NominaDestinatariosDocumentoPWA, RegistroAsistenciaNominaPWA

pytestmark = pytest.mark.django_db


def _ready(user):
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    return user


def _client(username, *codenames):
    usuario = _ready(get_user_model().objects.create_user(username, password="x"))
    for codename in codenames:
        usuario.user_permissions.add(Permission.objects.get(codename=codename))
    client = Client()
    client.force_login(usuario)
    return client


@pytest.fixture(name="web")
def web_fixture():
    return _client("lector_asistencia_k7", "view_nomina")


def _url(comedor, admision):
    return (
        f"/api/web/comedores/comedores/{comedor.pk}/admision/{admision.pk}"
        "/nomina/asistencia/"
    )


def _registro(nomina, periodo, cuando, actor=None):
    registro = RegistroAsistenciaNominaPWA.objects.create(
        nomina=nomina, periodo_referencia=periodo, tomado_por=actor
    )
    # ``fecha_toma_asistencia`` is ``auto_now_add``: pin it to a known instant.
    RegistroAsistenciaNominaPWA.objects.filter(pk=registro.pk).update(
        fecha_toma_asistencia=cuando
    )
    return registro


@pytest.fixture(name="escenario")
def escenario_fixture():
    sexo = Sexo.objects.get_or_create(sexo="Femenino")[0]
    comedor = Comedor.objects.create(nombre="Comedor Asistencia")
    admision = Admision.objects.create(comedor=comedor)
    ana = Ciudadano.objects.create(
        nombre="Ana",
        apellido="Gómez",
        documento="30111222",
        sexo=sexo,
        fecha_nacimiento=date(2015, 1, 1),
    )
    beto = Ciudadano.objects.create(
        nombre="Beto",
        apellido="Alvarez",
        documento="30111333",
        fecha_nacimiento=date(2014, 1, 1),
    )
    n_ana = Nomina.objects.create(admision=admision, ciudadano=ana, estado="activo")
    n_beto = Nomina.objects.create(admision=admision, ciudadano=beto, estado="activo")
    actor = get_user_model().objects.create_user("tomadora_k7")
    octubre = date(2026, 10, 1)
    septiembre = date(2026, 9, 1)
    cuando = datetime(2026, 10, 26, 15, 30, tzinfo=timezone.utc)
    reg_ana = _registro(n_ana, octubre, cuando, actor)
    _registro(n_beto, octubre, cuando)
    _registro(n_ana, septiembre, cuando)
    return {
        "comedor": comedor,
        "admision": admision,
        "ana": ana,
        "octubre": octubre,
        "reg_ana": reg_ana,
    }


def _json(web, url, **params):
    respuesta = web.get(url, params)
    assert respuesta.status_code == 200, respuesta.content[:400]
    return respuesta.json()


def test_period_list_matches_the_native_template(web, escenario):
    datos = _json(web, _url(escenario["comedor"], escenario["admision"]))

    assert datos["comedor"] == {
        "id": escenario["comedor"].pk,
        "nombre": "Comedor Asistencia",
    }
    assert datos["periodo"] is None
    assert datos["asistentes"] == []
    assert [(p["label"], p["iso"], p["total"]) for p in datos["periodos"]] == [
        ("10/2026", "2026-10-01", "2"),
        ("09/2026", "2026-09-01", "1"),
    ]
    assert all(p["documento_url"] is None for p in datos["periodos"])
    comedor, admision = escenario["comedor"], escenario["admision"]
    assert datos["urls"] == {
        "comedores": "/comedores/listar",
        "comedor": f"/comedores/{comedor.pk}",
        "nomina": f"/comedores/{comedor.pk}/admision/{admision.pk}/nomina/",
        "historial": f"/comedores/{comedor.pk}/admision/{admision.pk}/nomina/asistencia/",
    }


def test_selected_period_lists_attendees_with_native_formats(web, escenario):
    url = _url(escenario["comedor"], escenario["admision"])
    datos = _json(web, url, periodo="2026-10-15")

    assert datos["periodo"] == {"label": "10/2026", "total": "2"}
    # Native order: apellido, nombre, id (A sorts before G).
    assert [(a["apellido"], a["nombre"]) for a in datos["asistentes"]] == [
        ("Alvarez", "Beto"),
        ("Gómez", "Ana"),
    ]
    alvarez, gomez = datos["asistentes"]
    assert gomez["documento"] == "30111222"
    assert gomez["genero"] == "Femenino"
    assert gomez["tomada_por"] == "tomadora_k7"
    assert gomez["tomada_el"] == "26/10/2026 12:30"
    assert gomez["ciudadano_url"] == f"/ciudadanos/ver/{escenario['ana'].pk}"
    assert alvarez["genero"] == "-"
    assert alvarez["tomada_por"] == "-"
    assert datos["periodos"][0]["label"] == "10/2026"


def test_invalid_period_falls_back_to_the_list(web, escenario):
    datos = _json(
        web, _url(escenario["comedor"], escenario["admision"]), periodo="no-es-fecha"
    )

    assert datos["periodo"] is None
    assert len(datos["periodos"]) == 2


def test_latest_document_is_linked_as_a_file_url(web, escenario):
    documento = NominaDestinatariosDocumentoPWA(
        comedor=escenario["comedor"],
        periodo_referencia=escenario["octubre"],
        version=1,
    )
    documento.archivo.save("nomina.pdf", ContentFile(b"%PDF-1.4"), save=True)

    datos = _json(web, _url(escenario["comedor"], escenario["admision"]))

    octubre, septiembre = datos["periodos"]
    assert octubre["documento_url"] == documento.archivo.url
    assert septiembre["documento_url"] is None


def test_guards_are_the_native_ones(web, escenario):
    comedor, admision = escenario["comedor"], escenario["admision"]
    sin_permiso = _client("sin_permiso_asistencia_k7")
    ajena = Admision.objects.create(comedor=Comedor.objects.create(nombre="Otro"))

    assert Client().get(_url(comedor, admision)).status_code in (401, 403)
    assert sin_permiso.get(_url(comedor, admision)).status_code == 403
    assert web.get(_url(Comedor(pk=999999), admision)).status_code == 404
    assert web.get(_url(comedor, ajena)).status_code == 404


def test_post_is_not_allowed_and_nothing_is_written(web, escenario):
    antes = RegistroAsistenciaNominaPWA.objects.count()

    respuesta = web.post(_url(escenario["comedor"], escenario["admision"]), {})

    assert respuesta.status_code in (403, 405)
    assert RegistroAsistenciaNominaPWA.objects.count() == antes
    assert NominaDestinatariosDocumentoPWA.objects.count() == 0


def test_other_admission_rows_and_deleted_nominas_stay_out(web, escenario):
    comedor, admision = escenario["comedor"], escenario["admision"]
    otra = Admision.objects.create(comedor=comedor)
    ciudadano = Ciudadano.objects.create(
        nombre="Zoe", apellido="Zeta", documento="30999888"
    )
    ajena = Nomina.objects.create(admision=otra, ciudadano=ciudadano, estado="activo")
    baja = Nomina.objects.create(
        admision=admision, ciudadano=ciudadano, estado="activo"
    )
    cuando = datetime(2026, 10, 2, 10, 0, tzinfo=timezone.utc)
    _registro(ajena, escenario["octubre"], cuando)
    _registro(baja, escenario["octubre"], cuando)
    baja.delete()

    datos = _json(web, _url(comedor, admision), periodo="2026-10-01")

    assert datos["periodo"]["total"] == "2"
    assert "Zeta" not in [a["apellido"] for a in datos["asistentes"]]
