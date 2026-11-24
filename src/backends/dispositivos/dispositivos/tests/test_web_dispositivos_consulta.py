"""Web API (G1 v1) of the Dispositivos list, detail, map and location (DS01.01, DS02.01).

Read-only projection of ``DispositivoListView`` / ``DispositivoDetailView`` /
``DispositivoMapView`` for the React screens. Monolith tests go through
``config.settings_all`` (policy evaluated locally); runtime tests switch to
``SISOC_BACKEND="dispositivos"`` with the real runtime URLconf, where only a
request the core signed reaches the view. Comparisons are against the native
HTML views themselves; Georef is always mocked.
"""

import json

import pytest
from django.conf import settings
from django.contrib.auth.models import Permission, User
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone

from core import web_gate
from core.models import Municipio, Provincia
from dispositivos.models import Dispositivo
from dispositivos.views import build_detalle_secciones
from users.models import ProfileTerritorialScope

ROOT = "/api/web/dispositivos/"
LIST = ROOT + "listado/"
ALL_PERMS = (
    "view_dispositivo",
    "ver_mapa_dispositivo",
    "add_dispositivo",
    "change_dispositivo",
    "delete_dispositivo",
)

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _clean_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture(autouse=True)
def _no_georef(monkeypatch):
    """Georef is never reached; a test that needs a result mocks it explicitly."""

    def _forbidden(**kwargs):
        raise AssertionError(f"unexpected Georef call {kwargs}")

    monkeypatch.setattr("dispositivos.services.locate_address", _forbidden)


def _user(username, *perms, provincial=False, scopes=()):
    user = User.objects.create_user(username)
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.es_usuario_provincial = provincial
    profile.save()
    for scope in scopes:
        ProfileTerritorialScope.objects.create(profile=profile, **scope)
    user.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="dispositivos", codename__in=perms
        )
    )
    return User.objects.get(pk=user.pk)


def _login(user):
    client = Client()
    client.force_login(user)
    return client


def _dispositivo(provincia, municipio, indice, **extra):
    datos = {
        "nombre_institucion": f"Dispositivo {indice:02d}",
        "tipo_gestion": "estatal",
        "cuit_institucion": f"20{indice:09d}",
        "provincia": provincia,
        "municipio": municipio,
        "calle": f"Calle {indice}",
        "altura": "100",
        "telefono_prefijo": "221",
        "telefono_numero": "9876543",
        "responsable_nombre_completo": "Ana Lopez",
        "responsable_dni": f"{indice:08d}",
        "tipo_dispositivo": "refugio" if indice % 2 else "centro_dia",
        "modalidad_funcionamiento": "permanente",
        "capacidad_total_plazas": "0_15",
    }
    datos.update(extra)
    return Dispositivo.objects.create(**datos)


@pytest.fixture(name="geo")
def geo_fixture():
    pa = Provincia.objects.create(nombre="Buenos Aires")
    pb = Provincia.objects.create(nombre="Cordoba")
    ma = Municipio.objects.create(nombre="La Plata", provincia=pa)
    ma2 = Municipio.objects.create(nombre="Quilmes", provincia=pa)
    mb = Municipio.objects.create(nombre="Capital", provincia=pb)
    return {"pa": pa, "pb": pb, "ma": ma, "ma2": ma2, "mb": mb}


@pytest.fixture(name="red")
def red_fixture(geo):
    """Twenty devices across two provinces and three municipalities."""
    places = [(geo["pa"], geo["ma"]), (geo["pa"], geo["ma2"]), (geo["pb"], geo["mb"])]
    return [_dispositivo(*places[i % 3], i) for i in range(20)]


@pytest.fixture(name="admin")
def admin_fixture():
    return _user("disp_admin", *ALL_PERMS)


@pytest.fixture(name="web")
def web_fixture(admin):
    return _login(admin)


def _native_ids(client, name, params=None):
    respuesta = client.get(reverse(name), params or {})
    assert respuesta.status_code == 200
    return [d.pk for d in respuesta.context["dispositivos"]]


def _ids(data):
    return [fila["id"] for fila in data["results"]]


# --- List -----------------------------------------------------------------------


def test_list_projects_the_native_page(web, red):
    respuesta = web.get(LIST)

    assert respuesta.status_code == 200
    assert respuesta["Cache-Control"] == "private, no-store"
    assert "Cookie" in respuesta["Vary"]
    data = respuesta.json()
    assert _ids(data) == _native_ids(web, "dispositivos_listar")
    assert len(data["results"]) == 15
    assert (data["count"], data["page"], data["page_size"], data["pages"]) == (
        20,
        1,
        15,
        2,
    )
    assert data["is_paginated"] is True and data["has_next"] is True
    assert data["page_range"] == [1, 2]
    assert data["titulo"] == "Buscar Dispositivos"
    assert data["add_url"] == "/dispositivos/crear"
    assert data["map_url"] == "/dispositivos/mapa/"
    assert data["can_change"] is True and data["can_delete"] is True
    fila = next(f for f in data["results"] if f["id"] == red[18].pk)
    assert fila == {
        "id": red[18].pk,
        "nombre_institucion": "Dispositivo 18",
        "tipo_dispositivo_display": red[18].get_tipo_dispositivo_display(),
        "provincia": "Buenos Aires",
        "municipio": "La Plata",
        "urls": {
            "detail": f"/dispositivos/{red[18].pk}/",
            "edit": f"/dispositivos/{red[18].pk}/editar",
            "delete": f"/dispositivos/{red[18].pk}/eliminar",
        },
    }
    assert data["filters_config"]["fields"][0]["name"] == "nombre_institucion"


def test_list_page_two_search_and_filters_match_the_native_view(web, red):
    filtros = [
        {"logic": "AND", "items": [{"field": "provincia", "op": op, "value": v}]}
        for op, v in (
            ("contains", "Bue"),
            ("ncontains", "Bue"),
            ("eq", "Cordoba"),
            ("ne", "Cordoba"),
        )
    ] + [
        {"items": [{"field": "tipo_dispositivo", "op": op, "value": "refugio"}]}
        for op in ("eq", "ne")
    ]
    casos = [{"page": "2"}, {"busqueda": "  quilmes "}, {"busqueda": "refugio"}]
    casos += [{"filters": json.dumps(f)} for f in filtros]
    casos.append(
        {"filters": json.dumps({"items": [{"field": "provincia", "op": "empty"}]})}
    )
    for params in casos:
        data = web.get(LIST, params).json()
        assert _ids(data) == _native_ids(web, "dispositivos_listar", params), params


def test_list_pagination_prefix_keeps_the_native_links(web, red):
    data = web.get(
        LIST, {"busqueda": "Dispositivo", "filters": '{"a": 1}', "page": "1"}
    )

    # ``components/pagination.html`` without ``query``: busqueda is dropped.
    assert data.json()["query_prefix"] == "filters=%7B%22a%22%3A%201%7D&"


def test_list_invalid_page_is_404(web, red):
    for page in ("9", "x"):
        respuesta = web.get(LIST, {"page": page})
        assert respuesta.status_code == 404
        assert respuesta.json() == {"detail": "Página no válida."}
        assert (
            web.get(reverse("dispositivos_listar"), {"page": page}).status_code == 404
        )


def test_list_scope_matches_the_native_view_per_role(geo, red):
    roles = [
        _user("super"),
        _user("noterr", "view_dispositivo"),
        _user(
            "prov",
            "view_dispositivo",
            provincial=True,
            scopes=[{"provincia": geo["pa"]}],
        ),
        _user(
            "muni",
            "view_dispositivo",
            provincial=True,
            scopes=[{"provincia": geo["pa"], "municipio": geo["ma2"]}],
        ),
        _user("sinalcance", "view_dispositivo", provincial=True),
    ]
    root = User.objects.get(username="super")
    root.is_superuser = True
    root.save()
    esperados = {}
    for user in roles:
        client = _login(User.objects.get(pk=user.pk))
        ids = []
        for page in (1, 2):
            data = client.get(LIST, {"page": page})
            if data.status_code == 404:
                break
            ids += _ids(data.json())
            assert _ids(data.json()) == _native_ids(
                client, "dispositivos_listar", {"page": page}
            )
        esperados[user.username] = ids
    assert len(esperados["super"]) == 20 and len(esperados["noterr"]) == 20
    assert {
        d.provincia_id for d in Dispositivo.objects.filter(pk__in=esperados["prov"])
    } == {geo["pa"].pk}
    assert {
        d.municipio_id for d in Dispositivo.objects.filter(pk__in=esperados["muni"])
    } == {geo["ma2"].pk}
    assert esperados["sinalcance"] == []


def test_list_actions_follow_permissions(red):
    solo_ver = _login(_user("solo_ver", "view_dispositivo"))
    data = solo_ver.get(LIST).json()
    assert data["add_url"] is None and data["map_url"] is None
    assert data["can_change"] is False and data["can_delete"] is False
    con_mapa = _login(_user("con_mapa", "view_dispositivo", "ver_mapa_dispositivo"))
    data = con_mapa.get(LIST, {"busqueda": "x", "page": "1"}).json()
    assert data["map_url"] == "/dispositivos/mapa/?busqueda=x"
    opciones = con_mapa.get(ROOT + "options/", {"busqueda": "x"}).json()
    assert opciones["map_url"] == "/dispositivos/mapa/?busqueda=x"
    assert opciones["titulo"] == "Buscar Dispositivos"
    assert "results" not in opciones


def test_list_without_results(web, geo):
    data = web.get(LIST).json()

    assert data["results"] == [] and data["count"] == 0
    assert data["is_paginated"] is False


# --- Permissions --------------------------------------------------------------


def test_endpoints_require_the_native_permissions(red):
    pk = red[0].pk
    sin_view = _login(_user("sin_view", "ver_mapa_dispositivo", "change_dispositivo"))
    for url in (
        LIST,
        ROOT + "options/",
        f"{ROOT}{pk}/",
        ROOT + "mapa/",
        f"{ROOT}{pk}/ubicacion/",
    ):
        assert sin_view.get(url).status_code == 403, url
    solo_view = _login(_user("solo_view", "view_dispositivo"))
    assert solo_view.get(LIST).status_code == 200
    assert solo_view.get(f"{ROOT}{pk}/").status_code == 200
    for url in (ROOT + "mapa/", f"{ROOT}{pk}/ubicacion/"):
        assert solo_view.get(url).status_code == 403, url
        assert solo_view.get(url.replace("/api/web", "")).status_code == 403, url


def test_out_of_scope_and_missing_objects_are_404(geo, red, monkeypatch):
    monkeypatch.setattr(
        "dispositivos.services.locate_address", lambda **kw: {"status": "not_found"}
    )
    prov = _login(
        _user(
            "prov_b",
            "view_dispositivo",
            "ver_mapa_dispositivo",
            provincial=True,
            scopes=[{"provincia": geo["pb"]}],
        )
    )
    ajeno = next(d for d in red if d.provincia_id == geo["pa"].pk)
    for pk in (ajeno.pk, 999999):
        assert prov.get(f"{ROOT}{pk}/").status_code == 404
        assert prov.get(f"{ROOT}{pk}/ubicacion/").status_code == 404
        assert prov.get(reverse("dispositivos_detalle", args=[pk])).status_code == 404


def test_only_get_is_served(web, red):
    pk = red[0].pk
    for url in (
        LIST,
        ROOT + "options/",
        f"{ROOT}{pk}/",
        ROOT + "mapa/",
        f"{ROOT}{pk}/ubicacion/",
    ):
        for metodo in ("post", "put", "patch", "delete"):
            assert getattr(web, metodo)(url).status_code == 405, (url, metodo)
    assert Dispositivo.objects.count() == 20


# --- Detail -------------------------------------------------------------------


def test_native_detail_uses_the_extracted_sections(web, red):
    respuesta = web.get(reverse("dispositivos_detalle", args=[red[3].pk]))

    assert respuesta.context["detalle_secciones"] == build_detalle_secciones(red[3])
    assert len(respuesta.context["detalle_secciones"]) == 9


def test_detail_projects_the_native_legajo(web, geo, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    dispositivo = _dispositivo(
        geo["pa"],
        geo["ma"],
        7,
        latitud="-34.900000",
        longitud="-57.950000",
        dias_atencion=["lunes", "martes"],
        documentacion_dispositivo=SimpleUploadedFile("acta.pdf", b"%PDF-1"),
    )
    respuesta = web.get(f"{ROOT}{dispositivo.pk}/")

    assert respuesta.status_code == 200
    data = respuesta.json()
    nativo = web.get(reverse("dispositivos_detalle", args=[dispositivo.pk])).context
    assert data["nombre_institucion"] == "Dispositivo 07"
    assert data["meta"] == {
        "tipo": dispositivo.get_tipo_dispositivo_display(),
        "provincia": "Buenos Aires",
        "municipio": "La Plata",
        "actualizado": timezone.localtime(dispositivo.updated_at).strftime("%d/%m/%Y"),
    }
    assert data["breadcrumb"] == [
        {"text": "Dispositivos", "url": "/dispositivos/"},
        {"text": "Dispositivo 07", "url": None},
    ]
    assert data["show_map"] is True and data["mapa_query"] == nativo["mapa_query"]
    assert data["can_change"] is True
    assert data["edit_url"] == f"/dispositivos/{dispositivo.pk}/editar"
    secciones = nativo["detalle_secciones"]
    assert [s["titulo"] for s in data["detalle_secciones"]] == [
        s["titulo"] for s in secciones
    ]
    for propia, native in zip(data["detalle_secciones"], secciones):
        assert propia["icono"] == native["icono"]
        assert [i["label"] for i in propia["items"]] == [
            i["label"] for i in native["items"]
        ]
    items = {i["label"]: i for s in data["detalle_secciones"] for i in s["items"]}
    assert items["Nombre de la institución"]["value"] == "Dispositivo 07"
    assert items["Latitud"]["value"] == "-34,900000"
    assert items["Tipo de gestión - detalle"]["value"] == "-"
    assert items["Localidad"]["value"] == "-"
    assert items["Días de atención"]["kind"] == "list"
    assert items["Días de atención"]["value"] == ["Lunes", "Martes"]
    assert items["Observaciones adicionales"]["wide"] is True
    archivo = items["Documentación del dispositivo"]
    assert archivo["kind"] == "file" and archivo["value"]["name"] == "acta.pdf"
    assert archivo["value"]["url"] == dispositivo.documentacion_dispositivo.url
    assert items["Documentación adicional 1"]["value"] is None


def test_detail_without_map_permission_has_no_map_query(red):
    client = _login(_user("sin_mapa", "view_dispositivo"))
    data = client.get(f"{ROOT}{red[0].pk}/").json()

    assert data["show_map"] is False and data["mapa_query"] is None
    assert data["can_change"] is False


def test_list_consumes_pending_messages(web, red):
    respuesta = web.post(reverse("dispositivos_eliminar", args=[red[0].pk]))
    assert respuesta.status_code == 302

    data = web.get(LIST).json()
    assert data["messages"] == [
        {"message": "Dispositivo eliminado correctamente.", "level": "success"}
    ]
    assert web.get(LIST).json()["messages"] == []


# --- Map ----------------------------------------------------------------------


def test_map_projects_the_native_map_context(web, geo, red):
    _dispositivo(geo["pb"], geo["mb"], 50, latitud="-31.400000", longitud="-64.180000")
    params = {"busqueda": "Dispositivo", "dispositivo": str(red[2].pk)}
    respuesta = web.get(ROOT + "mapa/", params)

    assert respuesta.status_code == 200
    data = respuesta.json()
    nativo = web.get(reverse("dispositivos_mapa"), params).context
    assert [d["id"] for d in data["devices"]] == [
        d["id"] for d in nativo["map_devices"]
    ]
    for propio, native in zip(data["devices"], nativo["map_devices"]):
        esperado = {**native, "location_url": f"{ROOT}{native['id']}/ubicacion/"}
        assert {k: propio[k] for k in esperado} == esperado
    con_coordenadas = next(d for d in data["devices"] if d["name"] == "Dispositivo 50")
    assert con_coordenadas["location"] == {
        "status": "located",
        "lat": -31.4,
        "lon": -64.18,
    }
    assert con_coordenadas["street"] == "Calle 50 100"
    assert con_coordenadas["municipio"] == "Capital"
    assert data["provinces"] == [
        {"id": pk, "nombre": nombre} for pk, nombre in nativo["map_provinces"]
    ]
    assert data["initial_device"] == red[2].pk
    assert data["filters_config"] == nativo["filters_config"]
    assert data["filters_config"]["fields"][-1]["name"] == "estado_ubicacion"
    assert data["urls"] == {
        "list": "/dispositivos/mapa/",
        "reset": "/dispositivos/mapa/",
    }
    assert data["titulo"] == "Buscar Dispositivos"


def test_map_location_filters_and_initial_device(web, red):
    items = [
        {"field": "estado_ubicacion", "op": "eq", "value": "located"},
        {"field": "estado_ubicacion", "op": "contains", "value": "x"},
        {"field": "provincia", "op": "eq", "value": "Cordoba"},
    ]
    data = web.get(
        ROOT + "mapa/", {"filters": json.dumps({"items": items}), "dispositivo": "999"}
    ).json()
    assert data["location_filters"] == [items[0]]
    assert data["initial_device"] == ""
    # The engine ignores ``estado_ubicacion`` (client-side only): same queryset.
    solo_estado = json.dumps({"items": [items[0]]})
    assert (
        len(web.get(ROOT + "mapa/", {"filters": solo_estado}).json()["devices"]) == 20
    )
    for malo in ("{", "[1]", '{"items": 3}'):
        assert (
            web.get(ROOT + "mapa/", {"filters": malo}).json()["location_filters"] == []
        )


def test_map_provinces_come_from_the_scope_not_the_filter(web, red):
    data = web.get(ROOT + "mapa/", {"busqueda": "Cordoba"}).json()

    assert {d["province"] for d in data["devices"]} == {"Cordoba"}
    assert [p["nombre"] for p in data["provinces"]] == ["Buenos Aires", "Cordoba"]


# --- Location -----------------------------------------------------------------


def test_location_lookup_results_and_persistence(web, red, monkeypatch):
    device = red[0]
    url = f"{ROOT}{device.pk}/ubicacion/"
    llamadas = []

    def georef(status):
        def _locate(**kwargs):
            llamadas.append(kwargs)
            return (
                {"status": status, "lat": -34.9, "lon": -57.9}
                if status == "located"
                else {"status": status}
            )

        return _locate

    monkeypatch.setattr("dispositivos.services.locate_address", georef("unavailable"))
    respuesta = web.get(url)
    assert respuesta.status_code == 503 and respuesta.json() == {
        "status": "unavailable"
    }
    assert respuesta["Cache-Control"] == "private, no-store"
    device.refresh_from_db()
    assert device.ubicacion_georef == {}

    for status in ("ambiguous", "not_found"):
        cache.clear()
        Dispositivo.objects.filter(pk=device.pk).update(ubicacion_georef={})
        monkeypatch.setattr("dispositivos.services.locate_address", georef(status))
        respuesta = web.get(url)
        assert respuesta.status_code == 200 and respuesta.json() == {"status": status}

    cache.clear()
    Dispositivo.objects.filter(pk=device.pk).update(ubicacion_georef={})
    monkeypatch.setattr("dispositivos.services.locate_address", georef("located"))
    respuesta = web.get(url)
    assert respuesta.json() == {"status": "located", "lat": -34.9, "lon": -57.9}
    device.refresh_from_db()
    assert device.ubicacion_georef["result"]["status"] == "located"
    cantidad = len(llamadas)
    assert web.get(url).json()["status"] == "located"
    assert len(llamadas) == cantidad

    device.altura = "900"
    device.save()
    cache.clear()
    monkeypatch.setattr("dispositivos.services.locate_address", georef("not_found"))
    assert web.get(url).json() == {"status": "not_found"}


def test_location_with_explicit_coordinates_never_calls_georef(web, geo):
    device = _dispositivo(geo["pa"], geo["ma"], 1, latitud="-34.5", longitud="-58.5")

    respuesta = web.get(f"{ROOT}{device.pk}/ubicacion/")

    assert respuesta.json() == {"status": "located", "lat": -34.5, "lon": -58.5}


def test_location_matches_the_native_lookup(web, red, monkeypatch):
    monkeypatch.setattr(
        "dispositivos.services.locate_address", lambda **kw: {"status": "ambiguous"}
    )
    native = web.get(reverse("dispositivos_ubicacion", args=[red[0].pk]))
    propia = web.get(f"{ROOT}{red[0].pk}/ubicacion/")

    assert (propia.status_code, propia.json()) == (native.status_code, native.json())


# --- G1 -----------------------------------------------------------------------


def test_anonymous_gets_401_json(client, red):
    for url in (
        LIST,
        f"{ROOT}{red[0].pk}/",
        ROOT + "mapa/",
        f"{ROOT}{red[0].pk}/ubicacion/",
    ):
        respuesta = client.get(url)
        assert respuesta.status_code == 401
        assert respuesta.json() == {"detail": web_gate.DETAIL_UNAUTHENTICATED}


def test_pending_web_requirement_is_reported(web, admin, red):
    admin.profile.must_change_password = True
    admin.profile.save()

    respuesta = web.get(LIST)

    assert respuesta.status_code == 403
    assert respuesta.json()["state"] == "password_change_required"


def test_admindocs_head_does_not_bypass_the_web_api(client, red):
    staff = User.objects.create_user("staff_disp", is_staff=True)
    staff.profile.acceso_web = True
    staff.profile.must_change_password = False
    staff.profile.needs_profile_confirmation = False
    staff.profile.save()
    client.force_login(staff)

    for url in (
        LIST,
        ROOT + "options/",
        ROOT + "mapa/",
        f"{ROOT}{red[0].pk}/",
        f"{ROOT}{red[0].pk}/ubicacion/",
    ):
        respuesta = client.head(url)
        assert respuesta.status_code == 403, url
        assert "X-View" not in respuesta


@pytest.fixture(name="runtime")
def runtime_fixture():
    with override_settings(
        SISOC_BACKEND="dispositivos",
        ROOT_URLCONF="dispositivos_runtime.urls",
        SISOC_BACKENDS={},
        INTERNAL_IPS=[],
    ):
        yield


def _signed(user, client, *, target=LIST, method="GET", now=None):
    return web_gate.sign(
        audience="dispositivos",
        user_pk=user.pk,
        session_key=client.cookies[settings.SESSION_COOKIE_NAME].value,
        method=method,
        target=target,
        now=now,
    )


@pytest.mark.usefixtures("runtime")
def test_runtime_serves_a_signed_request(web, admin, red):
    target = LIST + "?page=2"

    respuesta = web.get(
        target, RAW_URI=target, HTTP_X_SISOC_WEB_GATE=_signed(admin, web, target=target)
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["page"] == 2
    assert respuesta["Cache-Control"] == "private, no-store"


@pytest.mark.usefixtures("runtime")
def test_runtime_rejects_missing_tampered_and_expired_attestations(web, admin, red):
    valido = _signed(admin, web)
    for token in (
        None,
        valido[:-2] + ("xx" if not valido.endswith("xx") else "yy"),
        _signed(admin, web, now=timezone.now().timestamp() - 61),
        _signed(admin, web, target=ROOT + "mapa/"),
    ):
        extra = {"RAW_URI": LIST}
        if token is not None:
            extra["HTTP_X_SISOC_WEB_GATE"] = token
        assert web.get(LIST, **extra).status_code == 403

    assert web.get(LIST, RAW_URI=LIST, HTTP_X_SISOC_WEB_GATE=valido).status_code == 200


@pytest.mark.usefixtures("runtime")
def test_runtime_still_applies_the_native_permission(client, red):
    solo_view = _user("solo_view_rt", "view_dispositivo")
    client.force_login(solo_view)
    target = ROOT + "mapa/"

    respuesta = client.get(
        target,
        RAW_URI=target,
        HTTP_X_SISOC_WEB_GATE=_signed(solo_view, client, target=target),
    )

    assert respuesta.status_code == 403
    assert respuesta.json() != {"detail": web_gate.DETAIL_REJECTED}


@pytest.mark.usefixtures("runtime")
def test_runtime_anonymous_gets_401(client):
    respuesta = client.get(LIST, RAW_URI=LIST)

    assert respuesta.status_code == 401


def test_the_vertical_root_is_not_an_endpoint(web):
    assert web.get(ROOT).status_code == 404


def test_dispositivos_publishes_its_web_api_prefix():
    from config.backends import (  # pylint: disable=import-outside-toplevel
        load_backends_registry,
    )

    prefijos = load_backends_registry()["dispositivos"]["url_prefixes"]

    assert web_gate.web_api_prefix("dispositivos") in prefijos
