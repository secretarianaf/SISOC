"""Web API (G1 v1) of the DataCalle operativos back office (DC01.01-DC01.03, #2785).

``/api/web/dispositivos/datacalle/`` projects the native views of
``datacalle/views.py`` for the React screens. Every behaviour is compared with
the native HTML route itself (same data, same user): order, filters, scope,
permissions, form errors, persisted effects (including the soft-delete
cascade) and the queued messages. The token API of the field app is only read,
to prove that changes made from the web API reach it exactly as before.
"""

import datetime

import pytest
from django.conf import settings
from django.contrib.auth.models import Permission, User
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from core import web_gate
from core.models import Localidad, Municipio, Provincia
from datacalle.models import Encuesta, Relevamiento
from dispositivos.models import Dispositivo
from users.models import ProfileTerritorialScope, RelevadorCalleProvincia

ROOT = "/api/web/dispositivos/datacalle/"
LIST = ROOT + "relevamientos/"
NATIVE = "/datacalle/relevamientos/"
TODOS = (
    "datacalle.view_relevamiento",
    "datacalle.add_relevamiento",
    "datacalle.change_relevamiento",
    "datacalle.delete_relevamiento",
    "datacalle.view_encuesta",
)

pytestmark = pytest.mark.django_db


def _user(username, *perms, provincial=False, scopes=(), **names):
    user = User.objects.create_user(username, **names)
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.es_usuario_provincial = provincial
    profile.save()
    for provincia in scopes:
        ProfileTerritorialScope.objects.create(profile=profile, provincia=provincia)
    for code in perms:
        app_label, codename = code.split(".")
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label=app_label, codename=codename)
        )
    return User.objects.get(pk=user.pk)


def _entrevistador(provincia, username, first="", last="", dni=""):
    user = User.objects.create_user(username, first_name=first, last_name=last)
    user.profile.es_relevador_calle = True
    user.profile.datacalle_rol = "entrevistador"
    user.profile.dni = dni
    user.profile.save()
    RelevadorCalleProvincia.objects.create(profile=user.profile, provincia=provincia)
    return user


def _login(user, **kwargs):
    client = Client(**kwargs)
    client.force_login(user)
    return client


def _relevamiento(provincia, denominacion, inicio=15, equipo=(), **extra):
    datos = {
        "denominacion": denominacion,
        "provincia": provincia,
        "fase": Relevamiento.Fase.ESPACIO_PUBLICO,
        "area_operativa": "Plaza",
        "fecha_inicio": datetime.date(2026, 9, inicio),
        "fecha_fin": datetime.date(2026, 9, inicio + 2),
    }
    datos.update(extra)
    relevamiento = Relevamiento.objects.create(**datos)
    relevamiento.equipo.add(*equipo)
    return relevamiento


def _ids(response):
    return [fila["id"] for fila in response.json()["results"]]


def _native_ids(response):
    return [str(r.pk) for r in response.context["relevamientos"]]


@pytest.fixture(name="geo")
def geo_fixture():
    cba = Provincia.objects.create(nombre="Córdoba")
    salta = Provincia.objects.create(nombre="Salta")
    capital = Municipio.objects.create(nombre="Capital", provincia=cba)
    rio = Municipio.objects.create(nombre="Río Cuarto", provincia=cba)
    return {
        "cba": cba,
        "salta": salta,
        "capital": capital,
        "rio": rio,
        "salta_capital": Municipio.objects.create(nombre="Salta", provincia=salta),
        "centro": Localidad.objects.create(nombre="Centro", municipio=capital),
        "alberdi": Localidad.objects.create(nombre="Alberdi", municipio=capital),
        "banda": Localidad.objects.create(nombre="Banda Norte", municipio=rio),
    }


@pytest.fixture(name="admin")
def admin_fixture():
    return _user("gestion", *TODOS, first_name="Gestora", last_name="Prueba")


@pytest.fixture(name="web")
def web_fixture(admin):
    return _login(admin)


@pytest.fixture(name="equipo")
def equipo_fixture(geo):
    return {
        "ana": _entrevistador(geo["cba"], "ana.campo", "Ana", "Campo", "30111222"),
        "beto": _entrevistador(geo["cba"], "beto", "Beto", "Ruiz", ""),
        "sal": _entrevistador(geo["salta"], "entrev_salta", "Sol", "Norte", "40"),
    }


def _dispositivo(provincia, nombre):
    return Dispositivo.objects.create(
        nombre_institucion=nombre,
        tipo_gestion="estatal",
        cuit_institucion="20123456789",
        provincia=provincia,
        municipio=Municipio.objects.filter(provincia=provincia).first(),
        calle="Calle",
        altura="1",
        telefono_prefijo="221",
        telefono_numero="1",
        responsable_nombre_completo="Ana",
        responsable_dni="12345678",
        tipo_dispositivo="refugio",
        modalidad_funcionamiento="permanente",
        capacidad_total_plazas="0_15",
    )


# --- DC01.01 list ------------------------------------------------------------


def test_list_is_the_native_page_with_the_same_rows(web, geo, equipo):
    for i in range(17):
        _relevamiento(
            geo["cba"] if i % 2 else geo["salta"], f"Operativo {i:02d}", inicio=1 + i
        )
    zonas = _relevamiento(
        geo["cba"],
        "Zonas",
        inicio=25,
        municipio=geo["capital"],
        equipo=[equipo["ana"], equipo["beto"]],
        modalidad_papel=True,
        fecha_fin=datetime.date(2026, 9, 25),
    )
    zonas.localidades.add(geo["centro"], geo["alberdi"])

    for page in ("", "?page=2"):
        api, native = web.get(LIST + page), web.get(NATIVE + page)
        assert api.status_code == native.status_code == 200
        assert _ids(api) == _native_ids(native)
    body = web.get(LIST).json()
    assert (body["count"], body["page"], body["page_size"], body["pages"]) == (
        18,
        1,
        15,
        2,
    )
    assert (body["is_paginated"], body["has_next"], body["has_previous"]) == (
        True,
        True,
        False,
    )
    assert body["page_range"] == [1, 2]
    fila = next(f for f in body["results"] if f["denominacion"] == "Zonas")
    assert fila == {
        "id": str(zonas.pk),
        "denominacion": "Zonas",
        "fase_display": "Espacio público",
        "lugar": "Plaza",
        "modalidad_papel": True,
        "provincia": "Córdoba",
        "zonas": ", ".join(l.nombre for l in zonas.localidades.all()),
        "fecha_inicio": "25/09/26",
        "fecha_fin": "25/09/26",
        "dias": 1,
        "equipo": 2,
        "estado": "planificado",
        "estado_display": "Planificado",
        "urls": {
            "detail": f"{NATIVE}{zonas.pk}/",
            "edit": f"{NATIVE}{zonas.pk}/editar/",
        },
    }
    assert body["add_url"] == reverse("datacalle_relevamientos_crear")
    assert body["can_change"] is True
    assert body["estados"] == [
        {"value": v, "label": l} for v, l in Relevamiento.Estado.choices
    ]
    assert body["fases"] == [
        {"value": v, "label": l} for v, l in Relevamiento.Fase.choices
    ]


def test_list_row_place_is_the_device_for_a_shelter_and_zones_fall_back(web, geo):
    refugio = _dispositivo(geo["cba"], "Refugio Norte")
    _relevamiento(
        geo["cba"],
        "Alojamiento",
        fase=Relevamiento.Fase.DISPOSITIVO_ALOJAMIENTO,
        area_operativa="",
        dispositivo=refugio,
        municipio=geo["rio"],
    )
    _relevamiento(geo["cba"], "Sin zonas", area_operativa="")
    filas = {f["denominacion"]: f for f in web.get(LIST).json()["results"]}

    assert (filas["Alojamiento"]["lugar"], filas["Alojamiento"]["zonas"]) == (
        "Refugio Norte",
        "Río Cuarto",
    )
    assert (filas["Sin zonas"]["lugar"], filas["Sin zonas"]["zonas"]) == ("", "")
    assert filas["Sin zonas"]["dias"] == 3


def test_list_scope_is_the_full_province_scope(geo):
    _relevamiento(geo["cba"], "En Córdoba")
    _relevamiento(geo["salta"], "En Salta")
    casos = {
        "superusuario": User.objects.create_superuser("root"),
        "no_territorial": _user("nacional", "datacalle.view_relevamiento"),
        "provincial": _user(
            "prov", "datacalle.view_relevamiento", provincial=True, scopes=[geo["cba"]]
        ),
        "sin_alcance": _user("vacio", "datacalle.view_relevamiento", provincial=True),
    }
    esperado = {
        "superusuario": 2,
        "no_territorial": 2,
        "provincial": 1,
        "sin_alcance": 0,
    }
    for nombre, user in casos.items():
        client = _login(user)
        api, native = client.get(LIST), client.get(NATIVE)
        assert api.json()["count"] == esperado[nombre], nombre
        assert _ids(api) == _native_ids(native), nombre
        assert api.json()["resumen"] == native.context["resumen"], nombre


def test_list_filters_match_the_native_filters(web, geo, equipo):
    plaza = _relevamiento(geo["cba"], "Operativo plaza", equipo=[equipo["ana"]])
    plaza.localidades.add(geo["centro"])
    _relevamiento(
        geo["salta"],
        "Refugio salteño",
        fase=Relevamiento.Fase.DISPOSITIVO_ALOJAMIENTO,
        area_operativa="",
        dispositivo=_dispositivo(geo["salta"], "Refugio"),
        estado=Relevamiento.Estado.FINALIZADO,
    )
    _relevamiento(
        geo["cba"], "Costanera", area_operativa="Costanera sur", equipo=[equipo["beto"]]
    )
    queries = [
        "?estado=finalizado",
        "?estado=desconocido",
        "?fase=espacio_publico",
        "?fase=otra",
        "?busqueda=plaza",
        "?busqueda=%20costanera%20sur%20",
        "?busqueda=salta",
        "?busqueda=centro",
        "?busqueda=Ana",
        "?busqueda=ruiz",
        "?busqueda=beto",
        "?busqueda=30111",
        "?busqueda=zzz",
        "?estado=planificado&fase=espacio_publico&busqueda=o",
    ]
    for query in queries:
        api, native = web.get(LIST + query), web.get(NATIVE + query)
        assert _ids(api) == _native_ids(native), query
        assert api.json()["resumen"] == native.context["resumen"], query
    assert web.get(LIST + "?estado=desconocido").json()["count"] == 3
    assert web.get(LIST + "?busqueda=30111").json()["count"] == 1
    filtrado = web.get(LIST + "?estado=finalizado").json()
    assert filtrado["count"] == 1
    # The summary counts the whole scope, never the filtered page (native quirk).
    assert filtrado["resumen"]["total"] == 3
    assert filtrado["filters"] == {"busqueda": "", "estado": "finalizado", "fase": ""}


def test_list_pagination_links_keep_filters_but_not_the_search(web, geo):
    for i in range(16):
        _relevamiento(geo["cba"], f"Op {i}", inicio=1 + i)

    body = web.get(LIST + "?busqueda=Op&estado=planificado&page=2").json()

    assert body["query_prefix"] == "estado=planificado&"
    assert body["page"] == 2


def test_list_invalid_page_is_404_with_the_message(web, geo):
    _relevamiento(geo["cba"], "Único")

    respuesta = web.get(LIST + "?page=9")

    assert respuesta.status_code == 404
    assert respuesta.json() == {"detail": "Página no válida."}
    assert web.get(NATIVE + "?page=9").status_code == 404


def test_list_actions_follow_permissions(geo):
    _relevamiento(geo["cba"], "Solo lectura")
    body = _login(_user("lector", "datacalle.view_relevamiento")).get(LIST).json()

    assert body["add_url"] is None
    assert body["can_change"] is False


# --- DC01.01 detail ----------------------------------------------------------


def test_detail_projects_the_native_page(web, geo, equipo, admin):
    relevamiento = _relevamiento(
        geo["cba"],
        "Operativo invierno",
        municipio=geo["capital"],
        equipo=[equipo["ana"], equipo["beto"]],
        observaciones="Línea uno\nLínea dos",
        creado_por=admin,
        estado=Relevamiento.Estado.FINALIZADO,
        fecha_cierre=timezone.make_aware(datetime.datetime(2026, 9, 20, 18, 30)),
        cerrado_por=equipo["beto"],
        lat=-31.4,
        lon=-64.18,
        observacion_asentamiento=["codigo_inexistente"],
        otra_observacion="Sin novedades",
    )
    relevamiento.localidades.add(geo["centro"])
    for i in range(52):
        Encuesta.objects.create(
            relevamiento=relevamiento,
            estado=Encuesta.Estado.COMPLETA if i % 2 else Encuesta.Estado.RECHAZADA,
            codigo_entrevistado=f"C{i:02d}",
            fecha_inicio=timezone.make_aware(datetime.datetime(2026, 9, 16, 10, i)),
            variante="adolescente" if i == 51 else "completo",
        )
    url = f"{NATIVE}{relevamiento.pk}/"
    native = web.get(url)
    body = web.get(f"{LIST}{relevamiento.pk}/").json()

    assert body["denominacion"] == "Operativo invierno"
    assert (body["estado"], body["estado_display"]) == ("finalizado", "Finalizado")
    assert (body["provincia"], body["municipio"], body["zonas"]) == (
        "Córdoba",
        "Capital",
        "Centro",
    )
    assert (body["fecha_inicio"], body["fecha_fin"], body["dias"]) == (
        "15/09/2026",
        "17/09/2026",
        3,
    )
    assert (body["fase"], body["fase_display"], body["lugar"]) == (
        "espacio_publico",
        "Espacio público",
        "Plaza",
    )
    assert body["localidades"] == ["Centro"]
    assert body["modalidad_papel"] is False
    assert body["creado_por"] == "Gestora Prueba"
    assert body["equipo"] == [
        {"iniciales": "AC", "nombre": "Ana Campo", "dni": "30111222"},
        {"iniciales": "BR", "nombre": "Beto Ruiz", "dni": ""},
    ]
    assert body["observaciones"] == "Línea uno\nLínea dos"
    assert body["cierre"] == {
        "fecha": "20/09/2026 18:30",
        "por": "Beto Ruiz",
        "gps": "-31,4, -64,18",
        "observacion_asentamiento": list(native.context["observacion_asentamiento"]),
        "otra_observacion": "Sin novedades",
    }
    assert body["cierre"]["gps"] in native.content.decode()
    assert body["resumen_casos"] == native.context["resumen_casos"]
    assert [c["id"] for c in body["casos"]] == [
        str(c.pk) for c in native.context["encuestas"]
    ]
    assert len(body["casos"]) == 50
    primero = body["casos"][0]
    assert primero == {
        "id": primero["id"],
        "codigo": "C51",
        "persona": "",
        "lugar": "",
        "sin_entrevista_por_franja": False,
        "estado": "completa",
        "estado_display": "Completa",
        "es_formulario_menores": True,
        "cargado": "16/09/26 10:51",
        "url": reverse("datacalle_casos_detalle", args=[primero["id"]]),
    }
    assert body["breadcrumb"] == [
        {"text": "Relevamientos", "url": NATIVE},
        {"text": "Operativo invierno", "url": None},
    ]
    assert (body["can_change"], body["can_close"], body["can_delete"]) == (
        True,
        False,
        True,
    )
    assert body["urls"] == {
        "list": NATIVE,
        "edit": f"{url}editar/",
        "close": f"{LIST}{relevamiento.pk}/cerrar/",
        "delete": f"{url}eliminar/",
    }


def test_detail_open_and_empty_operativo(web, geo):
    relevamiento = _relevamiento(geo["cba"], "Vacío", lat=0, lon=0)
    body = web.get(f"{LIST}{relevamiento.pk}/").json()

    assert body["cierre"] is None
    assert (body["equipo"], body["casos"], body["localidades"]) == ([], [], [])
    assert (body["creado_por"], body["municipio"], body["observaciones"]) == (
        None,
        None,
        "",
    )
    assert body["can_close"] is True


def test_detail_gps_zero_shows_as_empty_like_the_template(web, geo):
    relevamiento = _relevamiento(
        geo["cba"],
        "Cerrado en cero",
        fecha_cierre=timezone.now(),
        lat=0.0,
        lon=-64.0,
    )
    cierre = web.get(f"{LIST}{relevamiento.pk}/").json()["cierre"]

    assert cierre["gps"] is None
    assert cierre["por"] is None
    assert cierre["observacion_asentamiento"] == []


def test_detail_out_of_scope_or_unknown_is_404(geo):
    ajeno = _relevamiento(geo["salta"], "Ajeno")
    client = _login(
        _user(
            "prov", "datacalle.view_relevamiento", provincial=True, scopes=[geo["cba"]]
        )
    )

    assert client.get(f"{LIST}{ajeno.pk}/").status_code == 404
    assert client.get(f"{NATIVE}{ajeno.pk}/").status_code == 404
    assert client.get(f"{LIST}123/").status_code == 404
    assert client.get(f"{LIST}00000000-0000-0000-0000-000000000000/").status_code == 404


def test_detail_actions_follow_permissions_and_state(geo):
    relevamiento = _relevamiento(geo["cba"], "Abierto")
    lector = _login(_user("lector", "datacalle.view_relevamiento"))
    body = lector.get(f"{LIST}{relevamiento.pk}/").json()

    assert (body["can_change"], body["can_close"], body["can_delete"]) == (
        False,
        False,
        False,
    )


# --- Permissions and methods ----------------------------------------------


def _endpoints(pk):
    return [
        ("get", LIST, "view"),
        ("get", f"{LIST}{pk}/", "view"),
        ("get", ROOT + "opciones/dispositivos/", "view"),
        ("get", ROOT + "opciones/relevadores/", "view"),
        ("get", LIST + "formulario/", "add"),
        ("post", LIST + "crear/", "add"),
        ("get", f"{LIST}{pk}/formulario/", "change"),
        ("post", f"{LIST}{pk}/editar/", "change"),
        ("post", f"{LIST}{pk}/cerrar/", "change"),
        ("get", f"{LIST}{pk}/eliminar/", "delete"),
        ("post", f"{LIST}{pk}/eliminar/", "delete"),
    ]


def test_each_endpoint_requires_its_native_permission(geo):
    relevamiento = _relevamiento(geo["cba"], "Protegido")
    sin_nada = _login(_user("nada"))
    for accion in ("view", "add", "change", "delete"):
        solo = _login(_user(f"solo_{accion}", f"datacalle.{accion}_relevamiento"))
        for method, url, requerido in _endpoints(relevamiento.pk):
            assert getattr(sin_nada, method)(url).status_code == 403, url
            esperado = 403 if requerido != accion else None
            status = getattr(solo, method)(url).status_code
            if esperado:
                assert status == 403, (accion, url)
            else:
                assert status != 403, (accion, url)


def test_methods_are_the_native_ones(web, geo):
    relevamiento = _relevamiento(geo["cba"], "Métodos")

    assert web.get(f"{LIST}{relevamiento.pk}/cerrar/").status_code == 405
    assert web.get(f"{NATIVE}{relevamiento.pk}/cerrar/").status_code == 405
    assert web.get(LIST + "crear/").status_code == 405
    assert web.get(f"{LIST}{relevamiento.pk}/editar/").status_code == 405
    assert web.post(LIST).status_code == 405


def test_writes_need_csrf(admin, geo):
    relevamiento = _relevamiento(geo["cba"], "Csrf")
    client = _login(admin, enforce_csrf_checks=True)

    assert client.post(f"{LIST}{relevamiento.pk}/cerrar/").status_code == 403
    assert Relevamiento.objects.get(pk=relevamiento.pk).estado == "planificado"


# --- DC01.02 form ------------------------------------------------------------


def _datos(geo, team, **extra):
    datos = {
        "denominacion": "Operativo invierno",
        "provincia": geo["cba"].id,
        "fase": Relevamiento.Fase.ESPACIO_PUBLICO,
        "area_operativa": "Plaza San Martín",
        "fecha_inicio": "2026-09-15",
        "fecha_fin": "2026-09-19",
        "equipo": [u.id for u in team],
    }
    datos.update(extra)
    return {k: v for k, v in datos.items() if v is not None}


def test_create_schema_is_the_native_form(web, geo, equipo):
    body = web.get(LIST + "formulario/").json()
    campos = {f["name"]: f for f in body["fields"]}

    assert [f["name"] for f in body["fields"]] == [
        "denominacion",
        "provincia",
        "municipio",
        "localidades",
        "fase",
        "area_operativa",
        "dispositivo",
        "fecha_inicio",
        "fecha_fin",
        "modalidad_papel",
        "equipo",
        "observaciones",
    ]
    assert body["titulo"] == "Planificar relevamiento"
    assert campos["denominacion"] == {
        "name": "denominacion",
        "label": "Denominación",
        "required": True,
        "disabled": False,
        "widget": "text",
        "help_text": "Nombre con el que el equipo identifica el operativo.",
        "value": "",
        "attrs": {"maxlength": "255"},
    }
    assert campos["provincia"]["choices"] == [
        {"value": "", "label": "---------"},
        {"value": str(geo["cba"].id), "label": "Córdoba"},
        {"value": str(geo["salta"].id), "label": "Salta"},
    ]
    assert campos["municipio"]["choices"] == [{"value": "", "label": "---------"}]
    assert campos["localidades"]["choices"] == []
    assert campos["equipo"]["choices"] == []
    assert campos["fase"]["choices"][1:] == [
        {"value": v, "label": l} for v, l in Relevamiento.Fase.choices
    ]
    assert (
        campos["area_operativa"]["label"],
        campos["area_operativa"]["required"],
    ) == (
        "Área operativa",
        False,
    )
    assert campos["fecha_inicio"]["widget"] == "date"
    assert (
        campos["modalidad_papel"]["widget"],
        campos["modalidad_papel"]["value"],
    ) == (
        "checkbox",
        False,
    )
    assert (
        campos["equipo"]["widget"]
        == campos["localidades"]["widget"]
        == "selectmultiple"
    )
    assert campos["observaciones"]["attrs"] == {"cols": "40", "rows": "3"}
    assert body["can_add_dispositivo"] is False
    assert body["urls"] == {
        "cancel": NATIVE,
        "add_dispositivo": "/dispositivos/crear",
        "municipios": reverse("ajax_load_municipios"),
        "localidades": reverse("ajax_load_localidades"),
        "dispositivos": ROOT + "opciones/dispositivos/",
        "relevadores": ROOT + "opciones/relevadores/",
    }
    assert body["errors"] == {} and body["non_field_errors"] == []


def test_single_province_is_fixed_and_a_posted_other_province_is_ignored(geo, equipo):
    coordinador = _user(
        "coord",
        "datacalle.add_relevamiento",
        "datacalle.view_relevamiento",
        "dispositivos.add_dispositivo",
        provincial=True,
        scopes=[geo["cba"]],
    )
    client = _login(coordinador)
    body = client.get(LIST + "formulario/").json()
    provincia = next(f for f in body["fields"] if f["name"] == "provincia")

    assert provincia["disabled"] is True
    assert provincia["value"] == str(geo["cba"].id)
    assert provincia["help_text"] == "Tu alcance territorial es esta provincia."
    assert body["can_add_dispositivo"] is True
    equipo_campo = next(f for f in body["fields"] if f["name"] == "equipo")
    assert [c["label"] for c in equipo_campo["choices"]] == [
        "Ana Campo (30111222)",
        "Beto Ruiz",
    ]

    respuesta = client.post(
        LIST + "crear/", _datos(geo, [equipo["ana"]], provincia=geo["salta"].id)
    )

    assert respuesta.status_code == 201
    creado = Relevamiento.objects.get(pk=respuesta.json()["id"])
    assert creado.provincia == geo["cba"]


def test_create_saves_like_the_native_form_without_a_message(web, admin, geo, equipo):
    respuesta = web.post(
        LIST + "crear/",
        _datos(
            geo,
            [equipo["ana"], equipo["beto"]],
            municipio=geo["capital"].id,
            localidades=[geo["centro"].id],
            modalidad_papel="on",
            observaciones="Nota",
        ),
    )

    assert respuesta.status_code == 201
    creado = Relevamiento.objects.get(pk=respuesta.json()["id"])
    assert respuesta.json()["url"] == f"{NATIVE}{creado.pk}/"
    assert creado.creado_por == admin
    assert set(creado.equipo.all()) == {equipo["ana"], equipo["beto"]}
    assert list(creado.localidades.all()) == [geo["centro"]]
    assert (creado.modalidad_papel, creado.observaciones, creado.estado) == (
        True,
        "Nota",
        "planificado",
    )
    native = web.post(
        NATIVE + "crear/", _datos(geo, [equipo["ana"]], denominacion="Nativo")
    )
    assert native.status_code == 302
    nativo = Relevamiento.objects.get(denominacion="Nativo")
    assert native["Location"] == f"{NATIVE}{nativo.pk}/"
    assert web.get(LIST).json()["messages"] == []


ESCENARIOS = {
    "equipo_vacio": (
        {"equipo": []},
        "equipo",
        "Elegí al menos un entrevistador para el equipo.",
    ),
    "fechas": (
        {"fecha_inicio": "2026-09-19", "fecha_fin": "2026-09-15"},
        "fecha_fin",
        "La fecha de fin no puede ser anterior a la de inicio.",
    ),
    "sin_area": (
        {"area_operativa": ""},
        "area_operativa",
        "Indicá el área operativa del espacio público.",
    ),
    "sin_dispositivo": (
        {"fase": Relevamiento.Fase.DISPOSITIVO_ALOJAMIENTO, "area_operativa": ""},
        "dispositivo",
        "Elegí el dispositivo de alojamiento.",
    ),
    "sin_denominacion": ({"denominacion": ""}, "denominacion", None),
    "equipo_de_otra_provincia": ({"equipo": "sal"}, "equipo", None),
    "localidad_de_otro_municipio": (
        {"municipio": "capital", "localidades": "banda"},
        "localidades",
        None,
    ),
    "municipio_de_otra_provincia": ({"municipio": "salta_capital"}, "municipio", None),
}


@pytest.mark.parametrize("escenario", sorted(ESCENARIOS))
def test_create_errors_are_the_native_ones(web, geo, equipo, escenario):
    cambios, campo, mensaje = ESCENARIOS[escenario]
    cambios = dict(cambios)
    if cambios.get("equipo") == "sal":
        cambios["equipo"] = [equipo["sal"].id]
    for key in ("municipio", "localidades"):
        if key in cambios:
            cambios[key] = geo[cambios[key]].id
    datos = _datos(geo, [equipo["ana"]], **cambios)

    native = web.post(NATIVE + "crear/", datos)
    api = web.post(LIST + "crear/", datos)

    assert native.status_code == 200
    assert api.status_code == 400
    assert api.json()["errors"] == native.context["form"].errors.get_json_data()
    assert campo in api.json()["errors"]
    if mensaje:
        assert api.json()["errors"][campo][0]["message"] == mensaje
    assert not Relevamiento.objects.exists()


def test_400_keeps_the_bound_values_and_the_cascade(web, geo, equipo):
    datos = _datos(
        geo,
        [equipo["ana"]],
        denominacion="",
        municipio=geo["capital"].id,
        localidades=[geo["alberdi"].id],
        modalidad_papel="on",
    )
    body = web.post(LIST + "crear/", datos).json()
    campos = {f["name"]: f for f in body["fields"]}

    assert campos["municipio"]["value"] == str(geo["capital"].id)
    assert [c["label"] for c in campos["municipio"]["choices"]] == [
        "---------",
        "Capital",
        "Río Cuarto",
    ]
    assert [c["label"] for c in campos["localidades"]["choices"]] == [
        "Alberdi",
        "Centro",
    ]
    assert campos["localidades"]["value"] == [str(geo["alberdi"].id)]
    assert campos["equipo"]["value"] == [str(equipo["ana"].id)]
    assert campos["modalidad_papel"]["value"] is True
    assert campos["fecha_inicio"]["value"] == "2026-09-15"
    assert body["errors"]["denominacion"][0]["code"] == "required"


def test_phase_clears_the_place_field_that_does_not_apply(web, geo, equipo):
    refugio = _dispositivo(geo["cba"], "Refugio")
    web.post(
        LIST + "crear/",
        _datos(geo, [equipo["ana"]], denominacion="A", dispositivo=refugio.id),
    )
    web.post(
        LIST + "crear/",
        _datos(
            geo,
            [equipo["ana"]],
            denominacion="B",
            fase=Relevamiento.Fase.DISPOSITIVO_ALOJAMIENTO,
            dispositivo=refugio.id,
        ),
    )

    publico = Relevamiento.objects.get(denominacion="A")
    alojamiento = Relevamiento.objects.get(denominacion="B")
    assert (publico.dispositivo, publico.area_operativa) == (None, "Plaza San Martín")
    assert (alojamiento.dispositivo, alojamiento.area_operativa) == (refugio, "")


def _app_ids(user):
    token, _ = Token.objects.get_or_create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    data = client.get(reverse("api-datacalle-relevamientos-list")).json()
    rows = data["results"] if isinstance(data, dict) else data
    return [row["id"] for row in rows]


def test_edit_keeps_the_author_and_moves_the_task_between_interviewers(
    web, geo, equipo
):
    autor = _user("autor")
    relevamiento = _relevamiento(
        geo["cba"], "Editable", equipo=[equipo["ana"]], creado_por=autor
    )
    assert _app_ids(equipo["ana"]) == [str(relevamiento.pk)]
    assert _app_ids(equipo["beto"]) == []
    antes = Relevamiento.objects.get(pk=relevamiento.pk).updated_at

    respuesta = web.post(
        f"{LIST}{relevamiento.pk}/editar/",
        _datos(geo, [equipo["beto"]], denominacion="Editado"),
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "id": str(relevamiento.pk),
        "url": f"{NATIVE}{relevamiento.pk}/",
    }
    editado = Relevamiento.objects.get(pk=relevamiento.pk)
    assert (editado.denominacion, editado.creado_por) == ("Editado", autor)
    assert editado.updated_at > antes
    assert _app_ids(equipo["ana"]) == []
    assert _app_ids(equipo["beto"]) == [str(relevamiento.pk)]
    assert web.get(LIST).json()["messages"] == []


def test_edit_schema_has_the_saved_values(web, geo, equipo):
    relevamiento = _relevamiento(
        geo["cba"],
        "Guardado",
        municipio=geo["capital"],
        equipo=[equipo["beto"]],
        modalidad_papel=True,
    )
    relevamiento.localidades.add(geo["centro"])
    body = web.get(f"{LIST}{relevamiento.pk}/formulario/").json()
    valores = {f["name"]: f["value"] for f in body["fields"]}

    assert body["titulo"] == "Editar relevamiento"
    assert valores == {
        "denominacion": "Guardado",
        "provincia": str(geo["cba"].id),
        "municipio": str(geo["capital"].id),
        "localidades": [str(geo["centro"].id)],
        "fase": "espacio_publico",
        "area_operativa": "Plaza",
        "dispositivo": "",
        "fecha_inicio": "2026-09-15",
        "fecha_fin": "2026-09-17",
        "modalidad_papel": True,
        "equipo": [str(equipo["beto"].id)],
        "observaciones": "",
    }


def test_edit_out_of_scope_is_404(geo, equipo):
    ajeno = _relevamiento(geo["salta"], "Ajeno")
    client = _login(
        _user(
            "prov",
            "datacalle.change_relevamiento",
            provincial=True,
            scopes=[geo["cba"]],
        )
    )

    assert client.get(f"{LIST}{ajeno.pk}/formulario/").status_code == 404
    assert (
        client.post(
            f"{LIST}{ajeno.pk}/editar/", _datos(geo, [equipo["ana"]])
        ).status_code
        == 404
    )
    assert client.post(f"{LIST}{ajeno.pk}/cerrar/").status_code == 404
    assert Relevamiento.objects.get(pk=ajeno.pk).denominacion == "Ajeno"


def test_lookups_are_the_native_bodies(web, geo, equipo):
    _dispositivo(geo["cba"], "Refugio B")
    _dispositivo(geo["cba"], "Refugio A")
    _dispositivo(geo["salta"], "Refugio Salta")
    for kind, native_name in (
        ("dispositivos", "datacalle_ajax_dispositivos"),
        ("relevadores", "datacalle_ajax_relevadores"),
    ):
        for query in (f"?provincia_id={geo['cba'].id}", "", "?provincia_id=x"):
            api = web.get(f"{ROOT}opciones/{kind}/{query}")
            native = web.get(reverse(native_name) + query)
            assert api.status_code == 200
            assert api.json() == native.json(), (kind, query)
    nombres = [
        d["nombre"]
        for d in web.get(
            f"{ROOT}opciones/dispositivos/?provincia_id={geo['cba'].id}"
        ).json()
    ]
    assert nombres == ["Refugio A", "Refugio B"]
    assert web.get(f"{ROOT}opciones/relevadores/").json() == []


# --- DC01.03 close -----------------------------------------------------------


def test_close_then_close_again_is_idempotent(web, admin, geo):
    relevamiento = _relevamiento(geo["cba"], "Para cerrar")
    url = f"{LIST}{relevamiento.pk}/cerrar/"

    primero = web.post(url)

    assert primero.status_code == 200
    assert primero.json() == {
        "cerrado_ahora": True,
        "message": "El relevamiento quedó cerrado.",
        "level": "success",
        "url": f"{NATIVE}{relevamiento.pk}/",
    }
    cerrado = Relevamiento.objects.get(pk=relevamiento.pk)
    assert (cerrado.estado, cerrado.cerrado_por) == ("finalizado", admin)
    assert cerrado.fecha_cierre is not None
    detalle = web.get(f"{LIST}{relevamiento.pk}/").json()
    assert detalle["messages"] == [
        {"message": "El relevamiento quedó cerrado.", "level": "success"}
    ]
    assert detalle["can_close"] is False

    otro = _login(
        _user("otro", "datacalle.change_relevamiento", "datacalle.view_relevamiento")
    )
    segundo = otro.post(url)

    assert segundo.json() == {
        "cerrado_ahora": False,
        "message": "El relevamiento ya estaba cerrado.",
        "level": "info",
        "url": f"{NATIVE}{relevamiento.pk}/",
    }
    igual = Relevamiento.objects.get(pk=relevamiento.pk)
    assert (igual.fecha_cierre, igual.cerrado_por, igual.updated_at) == (
        cerrado.fecha_cierre,
        admin,
        cerrado.updated_at,
    )
    assert otro.get(f"{LIST}{relevamiento.pk}/").json()["messages"] == [
        {"message": "El relevamiento ya estaba cerrado.", "level": "info"}
    ]


def test_close_matches_the_native_messages(web, geo):
    nativo = _relevamiento(geo["cba"], "Nativo")
    for _ in range(2):
        respuesta = web.post(f"{NATIVE}{nativo.pk}/cerrar/", follow=True)
        nativos = [(str(m), m.level_tag) for m in respuesta.context["messages"]]
        assert len(nativos) == 1
    assert nativos == [("El relevamiento ya estaba cerrado.", "info")]


def test_close_does_not_need_the_datacalle_coordinator_role(geo):
    relevamiento = _relevamiento(geo["cba"], "Sin rol")
    user = _user("sin_rol", "datacalle.change_relevamiento")
    assert user.profile.datacalle_rol in ("", None)

    respuesta = _login(user).post(f"{LIST}{relevamiento.pk}/cerrar/")

    assert respuesta.status_code == 200
    assert Relevamiento.objects.get(pk=relevamiento.pk).estado == "finalizado"


# --- DC01.02 delete ----------------------------------------------------------


def test_delete_confirmation_is_the_native_one(web, geo):
    relevamiento = _relevamiento(geo["cba"], "A borrar")

    body = web.get(f"{LIST}{relevamiento.pk}/eliminar/").json()

    assert body == {
        "id": str(relevamiento.pk),
        "denominacion": "A borrar",
        "urls": {"cancel": f"{NATIVE}{relevamiento.pk}/"},
        "messages": [],
    }


def test_delete_is_the_native_soft_delete_including_its_cases(web, geo, equipo):
    por_api = _relevamiento(geo["cba"], "Por API", equipo=[equipo["ana"]])
    por_html = _relevamiento(geo["cba"], "Por HTML", equipo=[equipo["ana"]])
    for relevamiento in (por_api, por_html):
        for codigo in ("X1", "X2"):
            Encuesta.objects.create(
                relevamiento=relevamiento, estado="completa", codigo_entrevistado=codigo
            )
    assert len(_app_ids(equipo["ana"])) == 2

    respuesta = web.post(f"{LIST}{por_api.pk}/eliminar/")
    native = web.post(f"{NATIVE}{por_html.pk}/eliminar/")

    assert respuesta.status_code == 200
    assert respuesta.json() == {"url": NATIVE}
    assert native.status_code == 302 and native["Location"] == NATIVE

    def estado(relevamiento):
        fila = Relevamiento.all_objects.get(pk=relevamiento.pk)
        casos = Encuesta.all_objects.filter(relevamiento_id=relevamiento.pk)
        return (
            fila.deleted_at is not None,
            sorted((c.codigo_entrevistado, c.deleted_at is not None) for c in casos),
            Encuesta.objects.filter(relevamiento_id=relevamiento.pk).count(),
        )

    assert estado(por_api) == estado(por_html)
    # Observed native effect: the cascade soft-deletes the cases too.
    assert estado(por_api) == (True, [("X1", True), ("X2", True)], 0)
    assert Relevamiento.objects.filter(pk__in=[por_api.pk, por_html.pk]).count() == 0
    assert web.get(LIST).json()["count"] == 0
    assert _app_ids(equipo["ana"]) == []
    assert web.get(f"{LIST}{por_api.pk}/").status_code == 404
    assert web.get(LIST).json()["messages"] == []


# --- G1 runtime ------------------------------------------------------------


@pytest.fixture(name="runtime")
def runtime_fixture():
    with override_settings(
        SISOC_BACKEND="dispositivos",
        ROOT_URLCONF="dispositivos_runtime.urls",
        SISOC_BACKENDS={},
        INTERNAL_IPS=[],
    ):
        yield


def _signed(user, client, *, target, method="GET", now=None):
    return web_gate.sign(
        audience="dispositivos",
        user_pk=user.pk,
        session_key=client.cookies[settings.SESSION_COOKIE_NAME].value,
        method=method,
        target=target,
        now=now,
    )


@pytest.mark.usefixtures("runtime")
def test_runtime_serves_only_signed_requests(web, admin, geo):
    relevamiento = _relevamiento(geo["cba"], "Runtime")
    target = f"{LIST}{relevamiento.pk}/"

    valido = web.get(
        target, RAW_URI=target, HTTP_X_SISOC_WEB_GATE=_signed(admin, web, target=target)
    )

    assert valido.status_code == 200
    assert valido["Cache-Control"] == "private, no-store"
    for token in (
        None,
        _signed(admin, web, target=LIST),
        _signed(admin, web, target=target, now=timezone.now().timestamp() - 61),
    ):
        extra = {"RAW_URI": target}
        if token:
            extra["HTTP_X_SISOC_WEB_GATE"] = token
        assert web.get(target, **extra).status_code == 403


@pytest.mark.usefixtures("runtime")
def test_runtime_signed_close_still_checks_csrf_and_permission(admin, geo):
    relevamiento = _relevamiento(geo["cba"], "Runtime POST")
    target = f"{LIST}{relevamiento.pk}/cerrar/"
    client = _login(admin, enforce_csrf_checks=True)
    client.get(
        f"{LIST}{relevamiento.pk}/",
        RAW_URI=f"{LIST}{relevamiento.pk}/",
        HTTP_X_SISOC_WEB_GATE=_signed(
            admin, client, target=f"{LIST}{relevamiento.pk}/"
        ),
    )
    firma = _signed(admin, client, target=target, method="POST")

    sin_csrf = client.post(target, RAW_URI=target, HTTP_X_SISOC_WEB_GATE=firma)
    assert sin_csrf.status_code == 403
    assert Relevamiento.objects.get(pk=relevamiento.pk).estado == "planificado"

    client.cookies[settings.CSRF_COOKIE_NAME] = "a" * 32
    con_csrf = client.post(
        target, RAW_URI=target, HTTP_X_SISOC_WEB_GATE=firma, HTTP_X_CSRFTOKEN="a" * 32
    )
    assert con_csrf.status_code == 200
    assert Relevamiento.objects.get(pk=relevamiento.pk).estado == "finalizado"

    lector = _user("lector_rt", "datacalle.view_relevamiento")
    lector_client = _login(lector)
    respuesta = lector_client.post(
        target,
        RAW_URI=target,
        HTTP_X_SISOC_WEB_GATE=_signed(
            lector, lector_client, target=target, method="POST"
        ),
    )
    assert respuesta.status_code == 403
    assert respuesta.json() != {"detail": web_gate.DETAIL_REJECTED}


@pytest.mark.usefixtures("runtime")
def test_runtime_anonymous_gets_401(client):
    assert client.get(LIST, RAW_URI=LIST).status_code == 401
