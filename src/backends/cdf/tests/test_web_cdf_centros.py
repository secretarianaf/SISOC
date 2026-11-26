"""Web API (G1 v1) of the CDF centre list, detail and users panel (CDF04.01, #2805).

Read-only projection of ``CentroListView`` / ``CentroDetailView`` for the React
screens. The monolith tests go through ``config.settings_all`` (policy
evaluated locally); the runtime tests switch to ``SISOC_BACKEND="cdf"`` with
the real runtime URLconf, where only a request the core signed reaches the
view. Comparisons are against the native HTML view itself.
"""

import json
from datetime import time

import pytest
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.contrib.messages.storage.session import SessionStorage
from django.test import Client, RequestFactory, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from centrodefamilia.models import (
    AccesoCDF,
    Actividad,
    ActividadCentro,
    CabalArchivo,
    Categoria,
    Centro,
    InformeCabalRegistro,
)
from core import web_gate
from core.constants import UserGroups
from core.models import Localidad, Municipio, Provincia
from users.models import Profile

ROOT = "/api/web/cdf/centros/"
WRITES = ("INSERT", "UPDATE", "DELETE")

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _grupo_cdf_referente(db):
    Group.objects.get_or_create(name=UserGroups.CDF_REFERENTE_CENTRO)


def _ready(user):
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    return User.objects.get(pk=user.pk)


def _perm(user, app_model, codename):
    permission = Permission.objects.get(
        content_type=ContentType.objects.get_for_model(app_model), codename=codename
    )
    user.user_permissions.add(permission)
    return User.objects.get(pk=user.pk)


def _role(user, codename):
    permission, _ = Permission.objects.get_or_create(
        content_type=ContentType.objects.get_for_model(Group),
        codename=codename,
        defaults={"name": codename},
    )
    user.user_permissions.add(permission)
    return User.objects.get(pk=user.pk)


def _user(username, *roles, view=True, first="", last=""):
    user = _ready(User.objects.create_user(username, first_name=first, last_name=last))
    if view:
        user = _perm(user, Centro, "view_centro")
    for role in roles:
        user = _role(user, role)
    return user


def _centro(nombre, provincia=None, **extra):
    datos = {
        "nombre": nombre,
        "provincia": provincia,
        "tipo": "adherido",
        "codigo": extra.pop("codigo", nombre[:20]),
        "domicilio_actividad": "Domicilio sintético",
        "telefono": "011-1",
        "celular": "15-1",
        "correo": "centro@example.com",
        "nombre_referente": "Rita",
        "apellido_referente": "Ejemplo",
        "telefono_referente": "011-2",
        "correo_referente": "rita@example.com",
    }
    datos.update(extra)
    return Centro.objects.create(**datos)


@pytest.fixture(name="provincia")
def provincia_fixture():
    return Provincia.objects.create(nombre="Provincia Sintética")


@pytest.fixture(name="sse")
def sse_fixture():
    return _user("sse_cdf", "role_cdf_sse", first="Sara", last="Sse")


@pytest.fixture(name="web")
def web_fixture(sse):
    client = Client()
    client.force_login(sse)
    return client


@pytest.fixture(name="red")
def red_fixture(provincia):
    """Twelve centres (one FARO) with distinct codes, newest id last."""
    faro = _centro("Faro Central", provincia, tipo="faro", codigo="F-001")
    centros = [faro] + [
        _centro(
            f"Centro {numero:02d}",
            provincia,
            codigo=f"12{numero:02d}",
            faro_asociado=faro,
            activo=numero % 4 != 0,
        )
        for numero in range(11)
    ]
    return centros


def _login(user):
    client = Client()
    client.force_login(user)
    return client


def _native_list(client, params=None):
    respuesta = client.get(reverse("centro_list"), params or {})
    assert respuesta.status_code == 200
    return respuesta.context


def _ids(data):
    return [fila["id"] for fila in data["results"]]


# --- List ---------------------------------------------------------------------


def test_list_projects_the_native_nocount_page(web, red):
    respuesta = web.get(ROOT)

    assert respuesta.status_code == 200
    assert respuesta["Cache-Control"] == "private, no-store"
    assert "Cookie" in respuesta["Vary"]
    data = respuesta.json()
    native = _native_list(web)
    assert _ids(data) == [centro.pk for centro in native["centros"]]
    assert _ids(data) == sorted(_ids(data), reverse=True)
    assert data["count"] is None and data["pages"] is None
    assert data["page"] == 1 and data["page_size"] == 10
    assert data["has_next"] is True and data["has_previous"] is False
    assert data["page_range"] == list(native["page_range"]) == [1, 2, "..."]
    assert data["is_paginated"] is True
    assert data["filters"] == {"busqueda": "", "filters": ""}
    assert data["can_add"] is True
    assert data["can_delete"] is False
    assert data["filters_config"] == native["filters_config"]
    assert data["favorites"]["section"] == native["seccion_filtros_favoritos"]
    assert data["urls"] == {
        "list": "/centrodefamilia/centros/",
        "add": "/centrodefamilia/centros/nuevo/",
        "actividad_create": reverse("actividad_create_sola"),
        "informecabal": reverse("informecabal_list"),
    }
    fila = data["results"][0]
    centro = Centro.objects.get(pk=fila["id"])
    assert fila == {
        "id": centro.pk,
        "nombre": centro.nombre,
        "tipo": "adherido",
        "tipo_display": "Adherido",
        "calle": "None",
        "telefono": "011-1",
        "celular": "15-1",
        "activo": centro.activo,
        "urls": {
            "detail": f"/centrodefamilia/centros/{centro.pk}/",
            "edit": f"/centrodefamilia/centros/{centro.pk}/editar/",
            "delete": f"/centrodefamilia/centros/{centro.pk}/eliminar/",
        },
    }
    faro = next(
        f for f in web.get(ROOT, {"page": "2"}).json()["results"] if f["tipo"] == "faro"
    )
    assert faro["tipo_display"] == "faro"


def test_nocount_envelope_never_reports_a_total(web, red):
    for params in ({}, {"page": "2"}, {"busqueda": "zzz"}):
        data = web.get(ROOT, params).json()
        assert data["count"] is None, params
        assert data["pages"] is None, params


@pytest.mark.parametrize(
    ("page", "expected", "has_next"),
    [
        ("0", 1, True),
        ("-3", 1, True),
        ("last", 1, True),
        ("abc", 1, True),
        ("2", 2, False),
        ("999", 2, False),
    ],
)
def test_page_rules_follow_the_nocount_paginator(web, red, page, expected, has_next):
    data = web.get(ROOT, {"page": page}).json()

    native = _native_list(web, {"page": page})
    assert data["page"] == native["page_obj"].number == expected
    assert data["has_next"] is has_next
    assert _ids(data) == [centro.pk for centro in native["centros"]]


def test_zero_results_is_an_empty_first_page(web):
    data = web.get(ROOT).json()

    assert data["results"] == [] and data["page"] == 1
    assert data["is_paginated"] is False and data["page_range"] == [1]


def test_search_matches_code_prefix_or_id_and_text_by_name(web, red):
    numeric = web.get(ROOT, {"busqueda": " 12 "}).json()
    assert _ids(numeric) == [
        c.pk for c in _native_list(web, {"busqueda": " 12 "})["centros"]
    ]
    assert set(_ids(numeric)) >= {c.pk for c in red if c.codigo.startswith("12")} - set(
        _ids(web.get(ROOT, {"busqueda": "12", "page": "2"}).json())
    )
    por_id = {"busqueda": str(red[0].pk)}
    paginas = [web.get(ROOT, {**por_id, "page": n}).json() for n in ("1", "2")]
    assert red[0].pk in _ids(paginas[0]) + _ids(paginas[1])
    text = web.get(ROOT, {"busqueda": "faro"}).json()
    assert _ids(text) == [red[0].pk]


def test_advanced_filters_match_the_native_list(web, red):
    params = {
        "filters": json.dumps(
            {
                "logic": "AND",
                "items": [{"field": "activo", "op": "eq", "value": "false"}],
            }
        )
    }
    data = web.get(ROOT, params).json()

    assert _ids(data) == [c.pk for c in _native_list(web, params)["centros"]]
    assert data["results"] and all(fila["activo"] is False for fila in data["results"])
    assert data["filters"]["filters"] == params["filters"]


def test_pagination_prefix_keeps_busqueda_first_and_drops_page(web, red):
    data = web.get(ROOT, {"page": "2", "filters": '{"a":1}', "busqueda": "1 2"}).json()

    assert data["query_prefix"] == "busqueda=1%202&filters=%7B%22a%22%3A1%7D&"


def test_delete_button_follows_the_model_permission(red, provincia):
    usuario = _perm(_user("con_baja", "role_cdf_sse"), Centro, "delete_centro")
    client = _login(usuario)

    assert client.get(ROOT).json()["can_delete"] is True
    assert "btn-eliminar" in client.get(reverse("centro_list")).content.decode()


@override_settings(
    MESSAGE_STORAGE="django.contrib.messages.storage.session.SessionStorage"
)
def test_queued_messages_are_delivered_once(web, red):
    session = web.session
    request = RequestFactory().get("/")
    request.session = session
    storage = SessionStorage(request)
    storage.add(messages.SUCCESS, "Centro creado exitosamente.")
    storage.update(None)
    session.save()

    primera = web.get(ROOT).json()["messages"]
    segunda = web.get(ROOT).json()["messages"]

    assert primera == [{"message": "Centro creado exitosamente.", "level": "success"}]
    assert segunda == []


# --- Scope per actor (#2805 casos) ----------------------------------------------


def test_active_access_scopes_list_detail_and_users(red, provincia):
    a, b = red[1], red[2]
    referente = _user("ref_acceso", first="Rosa", last="Ref")
    AccesoCDF.objects.create(user=referente, centro=a, activo=True)
    otro = _user("otro_acceso")
    AccesoCDF.objects.create(user=otro, centro=a, activo=True)
    client = _login(referente)

    assert _ids(client.get(ROOT).json()) == [a.pk]
    assert client.get(f"{ROOT}{a.pk}/").status_code == 200
    assert client.get(f"{ROOT}{b.pk}/").status_code == 403
    assert client.get(reverse("centro_detail", args=[b.pk])).status_code == 403
    usuarios = client.get(f"{ROOT}{a.pk}/usuarios/")
    assert usuarios.status_code == 200
    assert [fila["username"] for fila in usuarios.json()["results"]] == ["ref_acceso"]


def test_history_without_active_access_lists_nothing_but_fk_opens_detail(red):
    c = red[3]
    referente = _user("ref_historial", "role_referentecentro")
    AccesoCDF.objects.create(user=referente, centro=red[1], activo=False)
    Centro.objects.filter(pk=c.pk).update(referente=referente)
    client = _login(referente)

    assert client.get(ROOT).json()["results"] == []
    assert client.get(f"{ROOT}{c.pk}/").status_code == 200


def test_legacy_referente_lists_by_fk_and_has_no_users_panel(red):
    c = red[4]
    legacy = _user("ref_legacy", "role_referentecentro")
    Centro.objects.filter(pk=c.pk).update(referente=legacy)
    client = _login(legacy)

    assert _ids(client.get(ROOT).json()) == [c.pk]
    detail = client.get(f"{ROOT}{c.pk}/").json()
    assert detail["puede_ver_usuarios"] is False
    assert client.get(f"{ROOT}{c.pk}/usuarios/").status_code == 403


def test_view_centro_without_role_lists_nothing_and_is_denied_the_detail(red):
    client = _login(_user("solo_permiso"))

    assert client.get(ROOT).json()["results"] == []
    assert client.get(f"{ROOT}{red[1].pk}/").status_code == 403


def test_territorial_delegator_without_quota_sees_detail_without_generar(
    red, provincia
):
    centro = red[1]
    actor = _user("prov_cdf")
    profile = Profile.objects.get(user=actor)
    profile.es_usuario_provincial = True
    profile.provincia = provincia
    profile.save()
    profile.grupos_asignables.add(
        Group.objects.get(name=UserGroups.CDF_REFERENTE_CENTRO)
    )
    client = _login(actor)
    con_cupo = client.get(f"{ROOT}{centro.pk}/").json()
    assert con_cupo["acciones"]["generar_usuario_url"] == (
        f"/centrodefamilia/centros/{centro.pk}/generar-usuario/"
    )
    for numero in range(AccesoCDF.LIMITE_USUARIOS_POR_CENTRO):
        AccesoCDF.objects.create(user=_user(f"cupo_{numero}"), centro=centro)

    respuesta = client.get(f"{ROOT}{centro.pk}/")

    assert respuesta.status_code == 200
    assert respuesta.json()["acciones"]["generar_usuario_url"] is None
    assert client.get(f"{ROOT}{centro.pk}/usuarios/").status_code == 403


def test_without_view_centro_all_three_are_403_and_missing_is_404(red, web):
    client = _login(_user("sin_view", "role_cdf_sse", view=False))
    for url in (ROOT, f"{ROOT}{red[1].pk}/", f"{ROOT}{red[1].pk}/usuarios/"):
        respuesta = client.get(url)
        assert respuesta.status_code == 403, url
        assert "state" not in respuesta.json()
    assert client.get(reverse("centro_list")).status_code == 403
    for url in (f"{ROOT}999999/", f"{ROOT}999999/usuarios/"):
        assert web.get(url).status_code == 404, url


def test_soft_deleted_centre_is_404(web, red):
    centro = red[5]
    centro.delete()

    assert web.get(f"{ROOT}{centro.pk}/").status_code == 404
    assert web.get(reverse("centro_detail", args=[centro.pk])).status_code == 404


def test_superuser_users_panel_lists_every_access_with_cr1_fields_only(red):
    centro = red[1]
    admin = _ready(User.objects.create_superuser("super_cdf", password="x"))
    activo = _user("b_activo", first="Bea", last="Uno")
    activo.email = "bea@example.com"
    activo.save()
    Profile.objects.filter(user=activo).update(temporary_password_plaintext="Temp-123")
    baja = _user("a_baja")
    AccesoCDF.objects.create(user=activo, centro=centro, activo=True)
    AccesoCDF.objects.create(user=baja, centro=centro, activo=False)

    respuesta = _login(admin).get(f"{ROOT}{centro.pk}/usuarios/")

    assert respuesta["Cache-Control"] == "private, no-store"
    assert respuesta.json() == {
        "results": [
            {
                "username": "b_activo",
                "nombre_completo": "Bea Uno",
                "email": "bea@example.com",
                "activo": True,
                "contrasena_temporal": "Temp-123",
            },
            {
                "username": "a_baja",
                "nombre_completo": None,
                "email": None,
                "activo": False,
                "contrasena_temporal": None,
            },
        ]
    }


# --- Detail ---------------------------------------------------------------------


@pytest.fixture(name="ficha")
def ficha_fixture(provincia, red, sse):
    centro = red[1]
    municipio = Municipio.objects.create(nombre="Muni Uno", provincia=provincia)
    localidad = Localidad.objects.create(nombre="Villa Ñandú", municipio=municipio)
    Centro.objects.filter(pk=centro.pk).update(
        calle="Av. Siempre Viva", numero=742, municipio=municipio, localidad=localidad
    )
    categoria = Categoria.objects.create(nombre="Deportes")
    otra_categoria = Categoria.objects.create(nombre="Arte")
    actividades = []
    for indice, (nombre, estado) in enumerate(
        [("Fútbol", "en_curso"), ("Vóley", "planificada"), ("Ajedrez", "finalizada")]
        + [(f"Taller {n}", "en_curso") for n in range(4)]
    ):
        actividad = Actividad.objects.create(
            nombre=nombre, categoria=categoria if indice % 2 else otra_categoria
        )
        actividades.append(
            ActividadCentro.objects.create(
                centro=centro,
                actividad=actividad,
                cantidad_personas=10 + indice,
                horariosdesde=time(9, 30),
                horarioshasta=None if indice == 1 else time(11, 0),
                precio=150 if indice == 0 else None,
                estado=estado,
            )
        )
    ActividadCentro.objects.create(
        centro=red[2],
        actividad=Actividad.objects.create(nombre="Canto", categoria=categoria),
        cantidad_personas=5,
        horariosdesde=time(18, 0),
        precio=0,
    )
    archivo = CabalArchivo.objects.create(
        archivo="informes_cabal/x.xlsx", nombre_original="cabal.xlsx", usuario=sse
    )
    InformeCabalRegistro.objects.create(
        archivo=archivo,
        centro=centro,
        nro_tarjeta="1",
        nro_auto="1",
        mti="1",
        nro_comercio="1",
    )
    return Centro.objects.get(pk=centro.pk)


def test_detail_projects_the_native_context(web, ficha):
    respuesta = web.get(f"{ROOT}{ficha.pk}/")

    assert respuesta.status_code == 200
    assert respuesta["Cache-Control"] == "private, no-store"
    data = respuesta.json()
    native = web.get(reverse("centro_detail", args=[ficha.pk])).context
    assert data["centro"]["nombre"] == ficha.nombre
    assert data["centro"]["localidad"] == "Villa Ñandú"
    assert data["centro"]["numero"] == "742"
    assert data["centro"]["sitio_web"] is None
    assert data["mapa"] == (
        "https://maps.google.com/maps?q=Av.%20Siempre%20Viva+742,+Villa%20%C3%91and%C3%BA,"
        f"+Muni%20Uno,+{'Provincia%20Sint%C3%A9tica'}&output=embed"
    )
    metricas = native["metricas"]
    for clave in ("categorias", "actividades", "inscriptos", "interacciones", "mixtas"):
        assert data["metricas"][clave] == metricas[clave], clave
    assert data["metricas"]["asistentes"] == native["asistentes"]
    assert data["metricas"]["total_recaudado"] == str(native["total_recaudado"])
    assert data["metricas"]["centros_faro"] is None
    curso = data["actividades_curso"]
    assert [fila["id"] for fila in curso["results"]] == [
        a.pk for a in native["actividades_curso_paginadas"]
    ]
    assert curso["pages"] == 2 and curso["page_range"] == [1, 2] and curso["next"] == 2
    segunda = web.get(f"{ROOT}{ficha.pk}/", {"page_actividades_curso": "2"}).json()
    fila = next(
        f for f in segunda["actividades_curso"]["results"] if f["actividad"] == "Vóley"
    )
    assert fila["horariosdesde"] == "09:30" and fila["horarioshasta"] == "None"
    otras = data["actividades_otras"]["results"]
    assert [f["actividad"] for f in otras] == ["Canto"]
    assert otras[0]["precio"] is None and otras[0]["cantidad_personas"] == "5"
    assert data["cabal"]["archivos"][0]["nombre_original"] == "cabal.xlsx"
    assert data["cabal"]["ultimo"]["usuario"] == "Sara Sse"
    assert data["cabal"]["archivos"][0]["url"] == reverse(
        "informecabal_archivo_centro_detail",
        args=[ficha.pk, data["cabal"]["archivos"][0]["id"]],
    )
    assert data["acciones"]["agregar_adherido_url"] is None
    assert data["adheridos"] == [] and data["observaciones"] == []
    assert data["puede_ver_usuarios"] is False
    assert "usuarios" not in data and "contrasena_temporal" not in json.dumps(data)


def test_detail_map_prefers_valid_coordinates(web, ficha):
    Centro.objects.filter(pk=ficha.pk).update(
        latitud="-34.603722", longitud="-58.381592"
    )

    data = web.get(f"{ROOT}{ficha.pk}/").json()

    assert data["mapa"] == (
        "https://maps.google.com/maps?q=-34.603722,-58.381592&output=embed"
    )


def test_detail_faro_offers_adherido_and_no_amount(web, red):
    faro = red[0]

    data = web.get(f"{ROOT}{faro.pk}/").json()

    assert data["acciones"]["agregar_adherido_url"] == (
        f"/centrodefamilia/centros/nuevo/?faro={faro.pk}"
    )
    assert data["metricas"]["total_recaudado"] is None
    assert data["mapa"] is None


def test_en_curso_search_changes_only_the_filtered_metrics(web, ficha):
    base = web.get(f"{ROOT}{ficha.pk}/").json()["metricas"]
    data = web.get(
        f"{ROOT}{ficha.pk}/", {"search_actividades_curso": " FÚTBOL "}
    ).json()

    assert data["metricas"]["actividades"] == 1 != base["actividades"]
    assert data["metricas"]["total_recaudado"] == "0"
    assert data["metricas"]["categorias"] == base["categorias"]
    assert data["metricas"]["inscriptos"] == base["inscriptos"]
    assert data["search"]["actividades_curso"] == " FÚTBOL "
    assert data["links"]["curso_prefix"] == (
        "?search_actividades_curso=%20F%C3%9ATBOL%20&page_actividades_curso="
    )


def test_todas_tab_flag_and_its_raw_link_suffix(web, ficha):
    data = web.get(
        f"{ROOT}{ficha.pk}/", {"page_act": "x", "search_actividades": "a&b"}
    ).json()

    assert data["search"]["todas_activa"] is True
    assert data["actividades_otras"]["number"] == 1
    assert data["links"]["todas_suffix"] == "&search_actividades=a&b"
    assert web.get(f"{ROOT}{ficha.pk}/").json()["search"]["todas_activa"] is False


def test_curso_page_out_of_range_is_the_last_page(web, ficha):
    data = web.get(f"{ROOT}{ficha.pk}/", {"page_actividades_curso": "99"}).json()

    assert data["actividades_curso"]["number"] == 2
    assert data["actividades_curso"]["previous"] == 1


def test_reads_never_write(web, ficha):
    with CaptureQueriesContext(connection) as queries:
        for url in (ROOT, f"{ROOT}{ficha.pk}/", f"{ROOT}{ficha.pk}/usuarios/"):
            web.get(url)
    escrituras = [
        q["sql"]
        for q in queries.captured_queries
        if q["sql"].lstrip().upper().startswith(WRITES)
        and "django_session" not in q["sql"]
    ]
    assert escrituras == []


def test_only_get_is_served(web, ficha):
    for url in (ROOT, f"{ROOT}{ficha.pk}/", f"{ROOT}{ficha.pk}/usuarios/"):
        for metodo in ("post", "put", "patch", "delete"):
            assert getattr(web, metodo)(url).status_code == 405, (url, metodo)
    assert Centro.objects.filter(pk=ficha.pk, activo=ficha.activo).exists()


# --- G1 -------------------------------------------------------------------------


def test_anonymous_gets_401_json(client, red):
    for url in (ROOT, f"{ROOT}{red[1].pk}/", f"{ROOT}{red[1].pk}/usuarios/"):
        respuesta = client.get(url)
        assert respuesta.status_code == 401
        assert respuesta.json() == {"detail": web_gate.DETAIL_UNAUTHENTICATED}


def test_pending_web_requirement_is_reported_and_a_forged_header_is_ignored(
    web, sse, red
):
    sse.profile.must_change_password = True
    sse.profile.save()
    falso = web_gate.sign(
        audience="cdf",
        user_pk=sse.pk,
        session_key=web.cookies[settings.SESSION_COOKIE_NAME].value,
        method="GET",
        target=ROOT,
    )

    respuesta = web.get(ROOT, HTTP_X_SISOC_WEB_GATE=falso, RAW_URI=ROOT)

    assert respuesta.status_code == 403
    assert respuesta.json() == {
        "detail": web_gate.DETAIL_REQUIREMENT,
        "state": "password_change_required",
        "required_action_url": "/password/first-change/",
    }


def test_admindocs_head_does_not_bypass_the_web_api(client, red):
    client.force_login(_ready(User.objects.create_user("staff_cdf", is_staff=True)))

    for url in (ROOT, f"{ROOT}{red[1].pk}/", f"{ROOT}{red[1].pk}/usuarios/"):
        respuesta = client.head(url)
        assert respuesta.status_code == 403, url
        assert "X-View" not in respuesta


@pytest.fixture(name="runtime")
def runtime_fixture():
    with override_settings(
        SISOC_BACKEND="cdf",
        ROOT_URLCONF="cdf_runtime.urls",
        SISOC_BACKENDS={},
        INTERNAL_IPS=[],
    ):
        yield


def _signed(user, client, *, target=ROOT, method="GET", now=None):
    return web_gate.sign(
        audience="cdf",
        user_pk=user.pk,
        session_key=client.cookies[settings.SESSION_COOKIE_NAME].value,
        method=method,
        target=target,
        now=now,
    )


@pytest.mark.usefixtures("runtime")
def test_runtime_serves_a_signed_request(web, sse, red):
    target = ROOT + "?page=2"

    respuesta = web.get(
        target, RAW_URI=target, HTTP_X_SISOC_WEB_GATE=_signed(sse, web, target=target)
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["page"] == 2
    assert respuesta["Cache-Control"] == "private, no-store"


@pytest.mark.usefixtures("runtime")
def test_runtime_rejects_missing_tampered_and_expired_attestations(web, sse, red):
    valido = _signed(sse, web)
    for token in (
        None,
        valido[:-2] + ("xx" if not valido.endswith("xx") else "yy"),
        _signed(sse, web, now=timezone.now().timestamp() - 61),
        _signed(sse, web, target=ROOT + "1/"),
        _signed(sse, web, method="POST"),
    ):
        extra = {"RAW_URI": ROOT}
        if token is not None:
            extra["HTTP_X_SISOC_WEB_GATE"] = token
        assert web.get(ROOT, **extra).status_code == 403

    assert web.get(ROOT, RAW_URI=ROOT, HTTP_X_SISOC_WEB_GATE=valido).status_code == 200


@pytest.mark.usefixtures("runtime")
def test_runtime_still_applies_the_native_permission(client, red):
    sin_permiso = _user("sin_permiso_runtime", view=False)
    client.force_login(sin_permiso)

    respuesta = client.get(
        ROOT, RAW_URI=ROOT, HTTP_X_SISOC_WEB_GATE=_signed(sin_permiso, client)
    )

    assert respuesta.status_code == 403
    assert respuesta.json() != {"detail": web_gate.DETAIL_REJECTED}


@pytest.mark.usefixtures("runtime")
def test_runtime_anonymous_gets_401(client):
    respuesta = client.get(ROOT, RAW_URI=ROOT)

    assert respuesta.status_code == 401
    assert respuesta.json() == {"detail": web_gate.DETAIL_UNAUTHENTICATED}


def test_cdf_publishes_its_web_api_prefix():
    from config.backends import (  # pylint: disable=import-outside-toplevel
        load_backends_registry,
    )

    prefijos = load_backends_registry()["cdf"]["url_prefixes"]

    assert web_gate.web_api_prefix("cdf") in prefijos
