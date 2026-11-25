"""Web API (G1 v1) of the comedor nómina read: ``/api/web/comedores/comedores/`` (CO01).

The endpoints run the native ``NominaDetailView`` / ``NominaDirectaDetailView``; these
tests compare the JSON with what ``nomina_detail.html`` shows, check the native guards
(permission, scope, admission of the comedor) and that reading never writes.
"""

from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client

from admisiones.models.admisiones import Admision
from ciudadanos.models import Ciudadano, Sexo
from comedores.models import Comedor, Nomina, Programas

pytestmark = pytest.mark.django_db


def _ready(user):
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    return user


def _client(username, *codenames, superuser=False):
    usuario = _ready(get_user_model().objects.create_user(username, password="x"))
    for codename in codenames:
        usuario.user_permissions.add(Permission.objects.get(codename=codename))
    if superuser:
        usuario.is_superuser = True
        usuario.save()
    client = Client()
    client.force_login(usuario)
    return client


@pytest.fixture(name="web")
def web_fixture():
    return _client("lector_nomina_lectura", "view_nomina")


@pytest.fixture(name="sexos")
def sexos_fixture():
    return {
        nombre: Sexo.objects.get_or_create(sexo=nombre)[0]
        for nombre in ("Masculino", "Femenino")
    }


def _persona(sexos, documento, nombre="Ana", apellido="Gómez", sexo="Femenino"):
    return Ciudadano.objects.create(
        nombre=nombre,
        apellido=apellido,
        documento=documento,
        sexo=sexos[sexo],
        fecha_nacimiento=date(2015, 1, 1),
    )


def _json(web, url, **params):
    respuesta = web.get(url, params)
    assert respuesta.status_code == 200, respuesta.content[:400]
    return respuesta.json()


def _url_admision(comedor, admision):
    return f"/api/web/comedores/comedores/{comedor.pk}/admision/{admision.pk}/nomina/"


def _url_directa(comedor):
    return f"/api/web/comedores/comedores/{comedor.pk}/nomina/"


@pytest.fixture(name="programa_directo")
def programa_directo_fixture():
    return Programas.objects.create(
        nombre="Programa de nómina directa", usa_admision_para_nomina=False
    )


@pytest.fixture(name="directa")
def directa_fixture(sexos, programa_directo):
    comedor = Comedor.objects.create(
        nombre="Comedor Directo", programa=programa_directo
    )
    Nomina.objects.create(
        comedor=comedor, ciudadano=_persona(sexos, "30111222"), estado="activo"
    )
    Nomina.objects.create(
        comedor=comedor,
        ciudadano=_persona(sexos, "30111333", "Beto", "Ruiz", "Masculino"),
        estado="espera",
    )
    return comedor


@pytest.fixture(name="admision")
def admision_fixture(sexos):
    comedor = Comedor.objects.create(nombre="Comedor Admision")
    admision = Admision.objects.create(comedor=comedor)
    Nomina.objects.create(
        admision=admision, ciudadano=_persona(sexos, "30222111"), estado="activo"
    )
    return comedor, admision


def test_direct_nomina_projects_the_native_context(web, directa):
    datos = _json(web, _url_directa(directa))

    assert datos["comedor"]["nombre"] == "Comedor Directo"
    assert datos["comedor"]["provincia"] is None
    assert datos["header"] == {"inicio": "-", "fin": "-", "plazo": "-"}
    assert datos["stats"]["asistentes"] == "1"
    assert datos["stats"]["espera"] == "1"
    assert datos["stats"]["baja"] == "0"
    assert datos["stats"]["hombres"] == "0"
    assert datos["stats"]["mujeres"] == "1"
    assert datos["tabs"] is None
    assert datos["tab"] == "todas"
    assert datos["dni"] == ""
    assert datos["can_view_ciudadano"] is False
    assert datos["estados"] == [
        ["activo", "Activo"],
        ["espera", "En espera"],
        ["baja", "Baja"],
    ]
    assert datos["urls"]["historial"] is None
    assert datos["urls"]["crear"] == f"/comedores/{directa.pk}/nomina/crear/"
    assert datos["urls"]["lista"] == f"/comedores/{directa.pk}/nomina/"
    assert datos["page"]["has_other_pages"] is False
    assert datos["page"]["count"] == 2
    assert {r["documento"] for r in datos["rows"]} == {"30111222", "30111333"}
    fila = next(r for r in datos["rows"] if r["documento"] == "30111222")
    registro = Nomina.objects.get(ciudadano__documento="30111222")
    assert fila["id"] == registro.pk
    assert fila["nombre"] == "Ana"
    assert fila["apellido"] == "Gómez"
    assert fila["sexo"] == "Femenino"
    assert fila["estado"] == "activo"
    assert fila["estado_label"] == "Activo"
    assert fila["derivar_nombre"] == "Ana Gómez"
    assert fila["fecha"] == registro.fecha.astimezone().strftime("%d/%m/%Y")
    assert fila["urls"] == {
        "ciudadano": f"/ciudadanos/ver/{registro.ciudadano_id}",
        "cambiar_estado": f"/comedores/nomina/{registro.pk}/cambiar-estado/",
        "derivar": f"/comedores/nomina/{registro.pk}/derivar/",
        "borrar": f"/comedores/{directa.pk}/nomina/{registro.pk}/eliminar/",
    }
    assert [c["nombre"] for c in datos["comedores_para_derivar"]] == []


def test_admission_nomina_has_history_and_admission_urls(web, admision):
    comedor, adm = admision

    datos = _json(web, _url_admision(comedor, adm))

    assert datos["urls"]["historial"] == (
        f"/comedores/{comedor.pk}/admision/{adm.pk}/nomina/asistencia/"
    )
    assert datos["urls"]["crear"] == (
        f"/comedores/{comedor.pk}/admision/{adm.pk}/nomina/crear/"
    )
    assert (
        datos["urls"]["lista"] == f"/comedores/{comedor.pk}/admision/{adm.pk}/nomina/"
    )
    fila = datos["rows"][0]
    assert fila["urls"]["borrar"] == (
        f"/comedores/{comedor.pk}/admision/{adm.pk}/nomina/{fila['id']}/eliminar/"
    )
    assert datos["stats"]["asistentes"] == "1"


def test_dni_filter_and_page_come_from_the_native_view(web, directa):
    datos = _json(web, _url_directa(directa), dni="30111333")

    assert datos["dni"] == "30111333"
    assert [r["documento"] for r in datos["rows"]] == ["30111333"]
    # Metrics are global, not computed from the filtered page.
    assert datos["stats"]["asistentes"] == "1"
    assert datos["stats"]["espera"] == "1"


def test_view_ciudadano_permission_changes_the_links_flag(directa):
    web = _client("lector_nomina_ciudadano", "view_nomina", "view_ciudadano")

    assert _json(web, _url_directa(directa))["can_view_ciudadano"] is True


def test_destinations_exclude_the_origin_and_are_scoped(programa_directo):
    origen = Comedor.objects.create(nombre="Origen", programa=programa_directo)
    Comedor.objects.create(nombre="Destino Beta", programa=programa_directo)
    Comedor.objects.create(nombre="Destino Alfa", programa=programa_directo)
    # Admission-based comedor without an active admission cannot receive.
    Comedor.objects.create(nombre="Sin admision activa")
    web = _client("super_nomina_lectura", "view_nomina", superuser=True)

    datos = _json(web, _url_directa(origen))

    assert [c["nombre"] for c in datos["comedores_para_derivar"]] == [
        "Destino Alfa",
        "Destino Beta",
    ]


def test_guards_are_the_native_ones(web, directa, admision):
    comedor, adm = admision
    sin_permiso = _client("sin_permiso_nomina_lectura", "view_comedor")

    assert Client().get(_url_directa(directa)).status_code in (401, 403)
    assert sin_permiso.get(_url_directa(directa)).status_code == 403
    assert web.get("/api/web/comedores/comedores/999999/nomina/").status_code == 404
    # The admission must belong to the comedor of the URL.
    assert web.get(_url_admision(directa, adm)).status_code == 404
    assert web.get(_url_admision(comedor, adm)).status_code == 200


def test_post_is_not_allowed_and_nothing_is_written(web, directa):
    antes = list(Nomina.objects.values_list("pk", "estado", "deleted_at"))

    assert web.post(_url_directa(directa), {"estado": "baja"}).status_code in (403, 405)
    web.get(_url_directa(directa))

    assert list(Nomina.objects.values_list("pk", "estado", "deleted_at")) == antes


def test_pnud_comedor_exposes_the_native_tabs(web, sexos):
    comedor = Comedor.objects.create(
        nombre="Comedor PNUD",
        programa=Programas.objects.create(
            nombre="Programa PNUD", usa_admision_para_nomina=False
        ),
    )
    Nomina.objects.create(
        comedor=comedor, ciudadano=_persona(sexos, "30555111"), estado="activo"
    )

    datos = _json(web, _url_directa(comedor), tab="actividades")

    assert datos["tabs"] == [
        {"key": "alimentaria", "label": "Alimentaria", "active": False},
        {"key": "actividades", "label": "Actividades", "active": True},
        {"key": "todas", "label": "Todas", "active": False},
    ]
    assert datos["tab"] == "actividades"
    # Nobody has the activities flag: the tab shows no row, as the native one.
    assert datos["rows"] == []


def test_pagination_has_pages_of_one_hundred(web, programa_directo, sexos):
    comedor = Comedor.objects.create(nombre="Comedor Grande", programa=programa_directo)
    for numero in range(101):
        Nomina.objects.create(
            comedor=comedor,
            ciudadano=_persona(sexos, f"40{numero:06d}", apellido=f"Ap{numero:03d}"),
            estado="activo",
        )

    primera = _json(web, _url_directa(comedor))
    segunda = _json(web, _url_directa(comedor), page=2)

    assert len(primera["rows"]) == 100
    assert primera["page"] == {
        "has_other_pages": True,
        "number": 1,
        "num_pages": 2,
        "count": 101,
        "start": 1,
        "end": 100,
        "previous": None,
        "next": 2,
    }
    assert len(segunda["rows"]) == 1
    assert segunda["page"]["previous"] == 1
    assert segunda["page"]["next"] is None
    # The native page builder serves the last page for a page past the end.
    assert _json(web, _url_directa(comedor), page=9)["page"]["number"] == 2
