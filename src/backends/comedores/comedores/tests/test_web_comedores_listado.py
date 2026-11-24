"""Web API (G1 v1) of the comedor list: ``/api/web/comedores/comedores/`` (CO07.01).

The endpoint runs the native ``ComedorListView``; these tests compare its JSON with
what ``comedor_list.html`` shows and check that reading never writes.
"""

import json

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.test import Client

from comedores.models import Comedor, Referente
from core import web_gate

ROOT = "/api/web/comedores/comedores/"
LISTA = "/comedores/listar"

pytestmark = pytest.mark.django_db


def _ready(user):
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    return user


def _lector(username, codename="view_comedor"):
    usuario = _ready(get_user_model().objects.create_user(username, password="x"))
    usuario.user_permissions.add(Permission.objects.get(codename=codename))
    client = Client()
    client.force_login(usuario)
    return client


@pytest.fixture(name="web")
def web_fixture():
    return _lector("lector_listado_comedores")


@pytest.fixture(name="comedor")
def comedor_fixture():
    referente = Referente.objects.create(nombre="Ana", apellido="Pérez", celular="1155")
    return Comedor.objects.create(
        nombre="Comedor Norte",
        calle="Belgrano",
        numero=120,
        barrio="Centro",
        referente=referente,
    )


def test_list_projects_the_native_default_columns(web, comedor):
    datos = web.get(ROOT).json()

    assert [h["key"] for h in datos["headers"]] == [
        "nombre",
        "tipo",
        "mes_ejecucion",
        "ubicacion",
        "direccion",
        "referente",
        "validacion",
    ]
    assert [(h["title"], h["sortable"]) for h in datos["headers"]][:2] == [
        ("Nombre", True),
        ("Tipo", False),
    ]
    fila = datos["results"][0]
    assert fila["id"] == comedor.pk
    assert fila["urls"] == {
        "detalle": f"/comedores/{comedor.pk}",
        "editar": f"/comedores/{comedor.pk}/editar",
        "eliminar": f"/comedores/{comedor.pk}/eliminar",
    }
    celdas = {c["key"]: c for c in fila["cells"]}
    assert celdas["nombre"]["text"] == "Comedor Norte"
    assert celdas["tipo"]["text"] == "Sin información"
    assert celdas["mes_ejecucion"]["text"] == "-"
    assert celdas["ubicacion"]["lines"] == [
        "Sin provincia",
        "Sin municipio / Sin localidad",
        "Centro",
    ]
    assert celdas["direccion"]["text"] == "Belgrano 120"
    assert celdas["referente"]["text"] == "Ana Pérez"
    assert celdas["validacion"] == {
        "key": "validacion",
        "value": "Pendiente",
        "date": None,
    }
    assert datos["urls"] == {
        "list": LISTA,
        "reset": LISTA,
        "add": "/comedores/crear",
        "export": "/comedores/exportar",
    }
    assert datos["breadcrumb"] == [
        {"text": "Espacios Comunitarios", "url": LISTA},
        {"text": "Listar", "url": None},
    ]
    assert datos["can_export"] is False
    assert datos["messages"] == []


def test_list_pages_by_window_without_a_total(web):
    Comedor.objects.all().delete()
    for numero in range(11):
        Comedor.objects.create(nombre=f"Comedor {numero:02d}")

    pagina_1 = web.get(ROOT).json()
    pagina_2 = web.get(ROOT, {"page": "2", "filters": "[]"}).json()

    assert len(pagina_1["results"]) == 10
    assert pagina_1["page"] == {
        "is_paginated": True,
        "number": 1,
        "previous": None,
        "next": 2,
        "range": [1, 2, "…"],
        "query_without_page": "",
    }
    assert len(pagina_2["results"]) == 1
    assert pagina_2["page"]["previous"] == 1
    assert pagina_2["page"]["next"] is None
    assert pagina_2["page"]["query_without_page"] == "filters=%5B%5D&"
    assert "count" not in pagina_2["page"]


def test_advanced_filters_are_the_native_ones(web):
    Comedor.objects.all().delete()
    Comedor.objects.create(nombre="Norte")
    Comedor.objects.create(nombre="Sur")
    filtros = {
        "logic": "AND",
        "items": [{"field": "nombre", "op": "contains", "value": "Sur"}],
    }

    datos = web.get(ROOT, {"filters": json.dumps(filtros)}).json()

    assert [f["nombre"] for f in datos["results"]] == ["Sur"]


def test_a_search_without_results_is_an_empty_unpaginated_page(web, comedor):
    filtros = {
        "logic": "AND",
        "items": [{"field": "nombre", "op": "contains", "value": "zzzz"}],
    }

    respuesta = web.get(ROOT, {"filters": json.dumps(filtros)})

    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["results"] == []
    assert datos["page"]["is_paginated"] is False
    assert datos["page"]["range"] == []


def test_export_button_follows_the_native_rule(comedor):
    sin_csv = _lector("lector_sin_csv")
    con_csv = _lector("lector_con_csv")
    con_csv_user = get_user_model().objects.get(username="lector_con_csv")
    permiso, _ = Permission.objects.get_or_create(
        content_type=ContentType.objects.get_for_model(Group),
        codename="role_exportar_a_csv",
        defaults={"name": "Exportar a csv"},
    )
    con_csv_user.user_permissions.add(permiso)
    admin = Client()
    admin.force_login(
        _ready(get_user_model().objects.create_superuser("admin_listado", password="x"))
    )

    assert sin_csv.get(ROOT).json()["can_export"] is False
    assert con_csv.get(ROOT).json()["can_export"] is True
    assert admin.get(ROOT).json()["can_export"] is True


def test_reading_the_list_writes_nothing(web, comedor):
    antes = list(Comedor.objects.values())

    web.get(ROOT)

    assert list(Comedor.objects.values()) == antes


def test_only_get_is_served(web, comedor):
    for metodo in ("post", "put", "delete"):
        assert getattr(web, metodo)(ROOT).status_code == 405, metodo
    assert Comedor.objects.filter(pk=comedor.pk).exists()


def test_anonymous_gets_401_json(client):
    respuesta = client.get(ROOT)

    assert respuesta.status_code == 401
    assert respuesta.json() == {"detail": web_gate.DETAIL_UNAUTHENTICATED}


def test_user_without_any_listing_permission_gets_403(client, comedor):
    client.force_login(
        _ready(
            get_user_model().objects.create_user("sin_permiso_listado", password="x")
        )
    )

    assert client.get(ROOT).status_code == 403
    assert client.get(LISTA).status_code == 403


@pytest.mark.parametrize("codename", ["view_admision", "view_informacionrelevante"])
def test_any_of_the_three_native_permissions_is_enough(codename, comedor):
    assert _lector(f"lector_{codename}", codename).get(ROOT).status_code == 200


def test_pending_web_requirement_is_reported_and_a_forged_header_is_ignored(comedor):
    usuario = get_user_model().objects.create_superuser(
        "pendiente_listado", password="x"
    )
    usuario.profile.acceso_web = True
    usuario.profile.must_change_password = True
    usuario.profile.save()
    client = Client()
    client.force_login(usuario)
    falso = web_gate.sign(
        audience="comedores",
        user_pk=usuario.pk,
        session_key=client.cookies["sessionid"].value,
        method="GET",
        target=ROOT,
    )

    respuesta = client.get(ROOT, HTTP_X_SISOC_WEB_GATE=falso, RAW_URI=ROOT)

    assert respuesta.status_code == 403
    assert respuesta.json()["state"] == "password_change_required"
