"""Web API (G1 v1) of the Duplas list and detail: ``/api/web/comedores/duplas/``.

Read-only projection of ``DuplaListView`` / ``DuplaDetailView`` for the React
screens. The monolith tests go through ``config.settings_all`` (policy
evaluated locally); the runtime tests switch to ``SISOC_BACKEND="comedores"``
with the real runtime URLconf, where only a request the core signed reaches
the view. Every comparison is against the native HTML view itself.
"""

import json
from datetime import timedelta

import pytest
from django.conf import settings
from django.contrib import messages
from django.contrib.messages.storage.session import SessionStorage
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.test import Client, RequestFactory, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from core import web_gate
from duplas.dupla_filter_config import get_filters_ui_config
from duplas.models import Dupla

ROOT = "/api/web/comedores/duplas/"
WRITES = ("INSERT", "UPDATE", "DELETE")

pytestmark = pytest.mark.django_db


def _ready(user):
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    return user


def _role(user, codename):
    permission, _ = Permission.objects.get_or_create(
        content_type=ContentType.objects.get_for_model(Group),
        codename=codename,
        defaults={"name": codename},
    )
    user.user_permissions.add(permission)
    return User.objects.get(pk=user.pk)


def _user(username, first="", last="", *roles):
    user = _ready(User.objects.create_user(username, first_name=first, last_name=last))
    for role in roles:
        user = _role(user, role)
    return user


@pytest.fixture(name="admin")
def admin_fixture():
    return _user("admin_duplas", "Ada", "Admin", "role_admin")


@pytest.fixture(name="web")
def web_fixture(admin):
    client = Client()
    client.force_login(admin)
    return client


@pytest.fixture(name="equipo")
def equipo_fixture():
    """Twelve duplas: M2M técnicos, coordinator on some, fixed creation dates."""
    tecnicos = [
        _user("tec_a", "Tina", "Alvarez"),
        _user("tec_b", "Tomas", "Benitez"),
        _user("tec_c"),
    ]
    abogados = [_user("abo_a", "Laura", "Paz"), _user("abo_b", "", "")]
    coordinador = _user("coord_a", "Carla", "Coria")
    base = timezone.now() - timedelta(days=30)
    duplas = []
    for numero in range(12):
        dupla = Dupla.objects.create(
            nombre=f"Equipo {numero:02d}",
            estado="Activo" if numero % 3 else "Inactivo",
            abogado=abogados[numero % 2],
            coordinador=coordinador if numero % 4 == 0 else None,
        )
        # Same date for a pair, so the secondary order (nombre) matters too.
        Dupla.objects.filter(pk=dupla.pk).update(
            fecha=base + timedelta(days=numero // 2)
        )
        dupla.tecnico.set(tecnicos[: 1 + numero % 3])
        duplas.append(dupla)
    return {"tecnicos": tecnicos, "abogados": abogados, "coordinador": coordinador}


def _native(client, params=None):
    respuesta = client.get(reverse("dupla_list"), params or {})
    assert respuesta.status_code == 200
    return respuesta.context


def _nombres(data):
    return [fila["cells"][0] for fila in data["results"]]


def _filters(*items):
    return {"filters": json.dumps({"logic": "AND", "items": list(items)})}


def test_list_projects_the_native_rows_columns_and_frame(web, equipo):
    respuesta = web.get(ROOT)

    assert respuesta.status_code == 200
    assert respuesta["Cache-Control"] == "private, no-store"
    data = respuesta.json()
    native = _native(web)
    assert _nombres(data) == [d.nombre for d in native["duplas"]]
    assert len(data["results"]) == 10
    assert [h["title"] for h in data["headers"]] == [
        "Nombre",
        "Coordinador",
        "Tecnico/s",
        "Abogado",
        "Estado",
    ]
    assert all(h["sortable"] for h in data["headers"])
    assert data["headers"][1]["sort_key"] == "coordinador_nombre"
    por_nombre = {fila["cells"][0]: fila for fila in data["results"]}
    assert por_nombre["Equipo 11"]["cells"] == [
        "Equipo 11",
        "Sin asignar",
        "Alvarez Tina, Benitez Tomas, tec_c",
        "abo_b",
        "Activo",
    ]
    assert por_nombre["Equipo 08"]["cells"] == [
        "Equipo 08",
        "Coria Carla",
        "Alvarez Tina, Benitez Tomas, tec_c",
        "Paz Laura",
        "Activo",
    ]
    assert por_nombre["Equipo 09"]["cells"] == [
        "Equipo 09",
        "Sin asignar",
        "Alvarez Tina",
        "abo_b",
        "Inactivo",
    ]
    dupla = Dupla.objects.get(nombre="Equipo 08")
    assert por_nombre["Equipo 08"]["actions"] == [
        {
            "label": "Editar",
            "url": f"/equipo-tecnico/{dupla.pk}/editar/",
            "type": "editar",
            "icon": "edit",
        },
        {
            "label": "Eliminar",
            "url": f"/equipo-tecnico/{dupla.pk}/eliminar/",
            "type": "eliminar",
            "icon": "trash-alt",
        },
    ]
    assert data["breadcrumb"] == [
        {"text": "Equipos técnicos", "url": "/equipo-tecnico/"},
        {"text": "Listar", "url": None},
    ]
    assert data["filters_config"] == get_filters_ui_config()
    assert data["favorites"] == {
        "section": "duplas",
        "url": reverse("filtros_favoritos"),
        "detail_url_template": reverse("detalle_filtro_favorito", kwargs={"pk": 0}),
    }
    assert data["urls"] == {
        "list": "/equipo-tecnico/",
        "reset": "/equipo-tecnico/",
        "add": "/equipo-tecnico/crear/",
        "export": "/equipo-tecnico/exportar/",
    }
    assert data["columns"] == json.loads(json.dumps(native["column_config"]))
    assert data["page"] == {
        "is_paginated": True,
        "number": 1,
        "count": 12,
        "previous": None,
        "next": 2,
        "range": [1, 2],
        "query_without_page": "",
    }
    assert data["messages"] == []


def test_order_is_newest_first_then_by_name(web, equipo):
    nombres = _nombres(web.get(ROOT).json()) + _nombres(
        web.get(ROOT, {"page": 2}).json()
    )

    assert nombres == [
        "Equipo 10",
        "Equipo 11",
        "Equipo 08",
        "Equipo 09",
        "Equipo 06",
        "Equipo 07",
        "Equipo 04",
        "Equipo 05",
        "Equipo 02",
        "Equipo 03",
        "Equipo 00",
        "Equipo 01",
    ]


@pytest.mark.parametrize(
    "items",
    [
        [{"field": "nombre", "op": "contains", "value": "equipo 0"}],
        [{"field": "nombre", "op": "ncontains", "value": "1"}],
        [{"field": "nombre", "op": "eq", "value": "Equipo 03"}],
        [{"field": "estado", "op": "ne", "value": "Activo"}],
        [{"field": "coordinador", "op": "empty"}],
        [{"field": "tecnico", "op": "contains", "value": "T"}],
        [{"field": "tecnico_apellido", "op": "eq", "value": "Benitez"}],
        [{"field": "abogado_apellido", "op": "contains", "value": "paz"}],
        [{"field": "coordinador_apellido", "op": "contains", "value": "Cor"}],
        [
            {"field": "tecnico", "op": "contains", "value": "T"},
            {"field": "estado", "op": "eq", "value": "Activo"},
        ],
        [{"field": "nombre", "op": "gt", "value": "x"}],
    ],
)
def test_filters_match_the_native_list_exactly(web, equipo, items):
    params = _filters(*items)
    data = web.get(ROOT, params).json()
    native = _native(web, params)

    assert _nombres(data) == [d.nombre for d in native["duplas"]]
    assert data["page"]["count"] == native["page_obj"].paginator.count
    # M2M filters stay distinct, like the native queryset.
    assert len(set(_nombres(data))) == len(_nombres(data))


def test_pagination_keeps_the_query_and_rejects_an_invalid_page(web, equipo):
    params = {"page": "2", "busqueda": "x", "filters": '{"logic":"AND","items":[]}'}

    respuesta = web.get(ROOT, params)

    assert respuesta.status_code == 200
    page = respuesta.json()["page"]
    assert page["number"] == 2
    assert page["previous"] == 1
    assert page["next"] is None
    assert page["query_without_page"] == (
        "filters=%7B%22logic%22%3A%22AND%22%2C%22items%22%3A%5B%5D%7D&"
    )
    for invalida in ("9", "x"):
        assert web.get(ROOT, {"page": invalida}).status_code == 404
        assert web.get(reverse("dupla_list"), {"page": invalida}).status_code == 404


def test_empty_result_is_one_page_with_zero_count(web):
    data = web.get(ROOT).json()

    assert data["results"] == []
    assert data["page"]["is_paginated"] is False
    assert data["page"]["count"] == 0


def test_column_preferences_follow_the_native_state(web, equipo):
    guardado = web.post(
        reverse("column_preferences"),
        data=json.dumps(
            {"list_key": "duplas_list", "columns": ["nombre", "fecha", "id"]}
        ),
        content_type="application/json",
    )
    assert guardado.status_code == 200

    data = web.get(ROOT).json()
    native = _native(web)

    assert [h["title"] for h in data["headers"]] == ["Nombre", "Fecha", "ID"]
    assert data["columns"]["active"] == ["nombre", "fecha", "id"]
    dupla = native["duplas"][0]
    assert data["results"][0]["cells"] == [
        dupla.nombre,
        str(dupla.fecha),
        str(dupla.pk),
    ]


@override_settings(
    MESSAGE_STORAGE="django.contrib.messages.storage.session.SessionStorage"
)
def test_queued_messages_are_delivered_once(web, equipo):
    session = web.session
    request = RequestFactory().get("/")
    request.session = session
    storage = SessionStorage(request)
    storage.add(messages.SUCCESS, "Equipo técnico creado correctamente.")
    storage.update(None)
    session.save()

    primera = web.get(ROOT).json()["messages"]
    segunda = web.get(ROOT).json()["messages"]

    assert primera == [
        {"message": "Equipo técnico creado correctamente.", "level": "success"}
    ]
    assert segunda == []


def test_detail_projects_the_native_card(web, equipo):
    con = Dupla.objects.get(nombre="Equipo 08")
    sin = Dupla.objects.get(nombre="Equipo 09")

    data = web.get(f"{ROOT}{con.pk}/").json()
    vacio = web.get(f"{ROOT}{sin.pk}/").json()

    assert data == {
        "id": con.pk,
        "nombre": "Equipo 08",
        "estado": "Activo",
        "tecnicos": "Alvarez Tina, Benitez Tomas, tec_c",
        "abogado": "Laura Paz",
        "coordinador": "Carla Coria",
        "fecha": timezone.localtime(con.fecha).strftime("%d/%m/%Y %H:%M"),
        "urls": {
            "list": "/equipo-tecnico/",
            "edit": f"/equipo-tecnico/{con.pk}/editar/",
            "delete": f"/equipo-tecnico/{con.pk}/eliminar/",
        },
        "messages": [],
    }
    assert vacio["coordinador"] is None
    assert vacio["abogado"] == "abo_b"
    native = web.get(reverse("dupla_detalle", args=[con.pk]))
    assert data["fecha"] in native.content.decode()


def test_detail_of_a_missing_or_soft_deleted_equipo_is_404(web, admin, equipo):
    dupla = Dupla.objects.get(nombre="Equipo 05")
    dupla.delete(user=admin, cascade=True)

    for pk in (dupla.pk, 999999):
        assert web.get(f"{ROOT}{pk}/").status_code == 404
        assert web.get(reverse("dupla_detalle", args=[pk])).status_code == 404


def test_reads_never_write(web, equipo):
    dupla = Dupla.objects.first()

    with CaptureQueriesContext(connection) as queries:
        assert (
            web.get(
                ROOT, _filters({"field": "tecnico", "op": "contains", "value": "T"})
            ).status_code
            == 200
        )
        assert web.get(f"{ROOT}{dupla.pk}/").status_code == 200

    escrituras = [
        q["sql"] for q in queries if q["sql"].lstrip().upper().startswith(WRITES)
    ]
    assert escrituras == []


def test_only_get_is_served(web, equipo):
    dupla = Dupla.objects.first()
    for url in (ROOT, f"{ROOT}{dupla.pk}/"):
        for metodo in ("post", "put", "patch", "delete"):
            assert getattr(web, metodo)(url).status_code == 405, (url, metodo)
    assert Dupla.objects.count() == 12


def test_anonymous_gets_401_json(client, equipo):
    dupla = Dupla.objects.first()
    for url in (ROOT, f"{ROOT}{dupla.pk}/"):
        respuesta = client.get(url)
        assert respuesta.status_code == 401
        assert respuesta.json() == {"detail": web_gate.DETAIL_UNAUTHENTICATED}


def test_role_admin_is_required_and_export_role_does_not_open_the_list(client, equipo):
    dupla = Dupla.objects.first()
    sin_rol = _user("sin_rol")
    solo_csv = _user("solo_csv", "", "", "role_exportar_a_csv")

    for usuario in (sin_rol, solo_csv):
        client.force_login(usuario)
        for url in (ROOT, f"{ROOT}{dupla.pk}/"):
            respuesta = client.get(url)
            assert respuesta.status_code == 403, (usuario.username, url)
            assert "state" not in respuesta.json()
        assert client.get(reverse("dupla_list")).status_code == 403

    # The CSV keeps its own ANY rule (role_admin or role_exportar_a_csv).
    client.force_login(solo_csv)
    csv = client.get(reverse("dupla_exportar"))
    assert csv.status_code == 200
    assert "listado_duplas.csv" in csv["Content-Disposition"] or csv[
        "Content-Type"
    ].startswith("text/csv")


def test_superuser_keeps_the_native_bypass(client, equipo):
    superuser = _ready(User.objects.create_superuser("super_duplas", password="x"))
    client.force_login(superuser)

    data = client.get(ROOT).json()

    assert data["page"]["count"] == 12
    assert data["can_export"] is True


def test_export_button_follows_the_search_bar_rule(client, admin, equipo):
    client.force_login(admin)
    assert client.get(ROOT).json()["can_export"] is False
    native = client.get(reverse("dupla_list")).content.decode()
    assert "btn-export-csv" not in native

    ambos = _role(admin, "role_exportar_a_csv")
    client.force_login(ambos)
    assert client.get(ROOT).json()["can_export"] is True
    assert "btn-export-csv" in client.get(reverse("dupla_list")).content.decode()


def test_csv_export_stays_native_and_has_no_web_api_route(client, web, admin, equipo):
    assert web.get(f"{ROOT}exportar/").status_code == 404
    # Native today: the URL accepts ANY role, but ``CSVExportMixin`` also
    # requires ``role_exportar_a_csv``; the migration keeps both unchanged.
    assert web.get(reverse("dupla_exportar")).status_code == 403

    client.force_login(_role(admin, "role_exportar_a_csv"))
    csv = client.get(reverse("dupla_exportar"))
    assert csv.status_code == 200
    assert csv["Content-Type"].startswith("text/csv")


def test_pending_web_requirement_is_reported_and_a_forged_header_is_ignored(
    web, admin, equipo
):
    admin.profile.must_change_password = True
    admin.profile.save()
    falso = web_gate.sign(
        audience="comedores",
        user_pk=admin.pk,
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


def test_admindocs_head_does_not_bypass_the_web_api(client, equipo):
    staff = _ready(User.objects.create_user("staff_duplas", is_staff=True))
    client.force_login(staff)
    dupla = Dupla.objects.first()

    for url in (ROOT, f"{ROOT}{dupla.pk}/"):
        respuesta = client.head(url)
        assert respuesta.status_code == 403, url
        assert "X-View" not in respuesta


# --- Runtime: only the core's signed attestation reaches the view -----------


@pytest.fixture(name="runtime")
def runtime_fixture():
    with override_settings(
        SISOC_BACKEND="comedores",
        ROOT_URLCONF="comedores_runtime.urls",
        SISOC_BACKENDS={},
        INTERNAL_IPS=[],
    ):
        yield


def _signed(user, client, *, target=ROOT, method="GET", now=None):
    return web_gate.sign(
        audience="comedores",
        user_pk=user.pk,
        session_key=client.cookies[settings.SESSION_COOKIE_NAME].value,
        method=method,
        target=target,
        now=now,
    )


@pytest.mark.usefixtures("runtime")
def test_runtime_serves_a_signed_request(web, admin, equipo):
    target = ROOT + "?page=2"

    respuesta = web.get(
        target, RAW_URI=target, HTTP_X_SISOC_WEB_GATE=_signed(admin, web, target=target)
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["page"]["number"] == 2
    assert respuesta["Cache-Control"] == "private, no-store"


@pytest.mark.usefixtures("runtime")
def test_runtime_rejects_missing_tampered_and_expired_attestations(web, admin, equipo):
    valido = _signed(admin, web)
    for token in (
        None,
        valido[:-2] + ("xx" if not valido.endswith("xx") else "yy"),
        _signed(admin, web, now=timezone.now().timestamp() - 61),
        _signed(admin, web, target=ROOT + "1/"),
        _signed(admin, web, method="POST"),
    ):
        extra = {"RAW_URI": ROOT}
        if token is not None:
            extra["HTTP_X_SISOC_WEB_GATE"] = token
        assert web.get(ROOT, **extra).status_code == 403

    assert web.get(ROOT, RAW_URI=ROOT, HTTP_X_SISOC_WEB_GATE=valido).status_code == 200


@pytest.mark.usefixtures("runtime")
def test_runtime_still_applies_the_owner_permission(client, equipo):
    sin_rol = _user("sin_rol_runtime")
    client.force_login(sin_rol)

    respuesta = client.get(
        ROOT, RAW_URI=ROOT, HTTP_X_SISOC_WEB_GATE=_signed(sin_rol, client)
    )

    assert respuesta.status_code == 403
    assert respuesta.json() != {"detail": web_gate.DETAIL_REJECTED}


@pytest.mark.usefixtures("runtime")
def test_runtime_anonymous_gets_401(client):
    respuesta = client.get(ROOT, RAW_URI=ROOT)

    assert respuesta.status_code == 401
    assert respuesta.json() == {"detail": web_gate.DETAIL_UNAUTHENTICATED}


def test_comedores_publishes_its_web_api_prefix():
    from config.backends import (  # pylint: disable=import-outside-toplevel
        load_backends_registry,
    )

    prefijos = load_backends_registry()["comedores"]["url_prefixes"]

    assert web_gate.web_api_prefix("comedores") in prefijos
