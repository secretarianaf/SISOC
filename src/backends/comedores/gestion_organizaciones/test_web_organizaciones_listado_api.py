"""Web API (G1 v1) of the Organizaciones list (O05.01).

``/api/web/comedores/organizaciones/listado/`` runs the native
``OrganizacionListView``. The tests compare every projected value with the
native HTML page ``/organizaciones/listar`` and pin today's access: any of
``ORGANIZACION_DOCUMENTACION_PERMS``, the dupla scope for technicians and
lawyers, and the CSV kept as the native ``/organizaciones/exportar`` GET.
"""

import json
from html.parser import HTMLParser

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.test import Client, override_settings
from django.test.utils import CaptureQueriesContext

from comedores.models import Comedor
from core import web_gate
from duplas.models import Dupla
from organizaciones.models import Organizacion, SubtipoEntidad, TipoEntidad

API = "/api/web/comedores/organizaciones/listado/"
NATIVO = "/organizaciones/listar"
VIEW = "organizaciones.view_organizacion"

pytestmark = pytest.mark.django_db


def _ready(user):
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    return user


def _permiso(code):
    app, codename = code.split(".")
    if app == "auth":
        return Permission.objects.get_or_create(
            content_type=ContentType.objects.get_for_model(Group),
            codename=codename,
            defaults={"name": codename},
        )[0]
    return Permission.objects.get(content_type__app_label=app, codename=codename)


def _usuario(nombre, *codes, **extra):
    usuario = _ready(get_user_model().objects.create_user(nombre, **extra))
    for code in codes:
        usuario.user_permissions.add(_permiso(code))
    return usuario


def _client(usuario):
    client = Client()
    client.force_login(usuario)
    return client


@pytest.fixture(name="lector")
def lector_fixture():
    return _usuario("lector_org", VIEW)


@pytest.fixture(name="web")
def web_fixture(lector):
    return _client(lector)


class _Pagina(HTMLParser):
    """Native ``organizacion_list.html``: rows, links and pagination."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows, self.links, self.pages = [], [], []
        self.empty = None
        self._tbody = self._celda = self._link = self._page = None
        self._sort = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "tbody" and attrs.get("id") == "organizaciones-tbody":
            self._tbody = True
        elif self._tbody and tag == "tr":
            self.rows.append({"cells": [], "actions": []})
        elif self._tbody and tag == "td":
            datos = [v for k, v in attrs.items() if k.startswith("data-")]
            self._sort = datos[0] if datos else None
            self._celda = []
            if attrs.get("colspan"):
                self.rows.pop()
                self._sort = "EMPTY"
        elif self._tbody and tag == "a":
            self._link = {"url": attrs["href"], "class": attrs["class"], "text": []}
            self._link["title"] = attrs.get("title")
        elif tag == "a" and attrs.get("class") == "page-link":
            self._page = {"url": attrs["href"], "text": []}

    def handle_endtag(self, tag):
        if tag == "tbody":
            self._tbody = None
        elif tag == "a" and self._link is not None:
            self._link["text"] = " ".join("".join(self._link["text"]).split())
            self.links.append(self._link)
            self._link = None
        elif tag == "a" and self._page is not None:
            self.pages.append(("".join(self._page["text"]).strip(), self._page["url"]))
            self._page = None
        elif tag == "td" and self._celda is not None:
            texto = " ".join("".join(self._celda).split())
            if self._sort == "EMPTY":
                self.empty = texto
            else:
                self.rows[-1]["cells"].append({"text": texto, "sort": self._sort})
            self._celda = None

    def handle_data(self, data):
        if self._celda is not None:
            self._celda.append(data)
        if self._link is not None:
            self._link["text"].append(data)
        if self._page is not None:
            self._page["text"].append(data)


def _nativa(client, params=None):
    respuesta = client.get(NATIVO, params or {})
    assert respuesta.status_code == 200
    pagina = _Pagina()
    pagina.feed(respuesta.content.decode())
    return pagina, respuesta.content.decode()


def _organizaciones(cantidad=3):
    tipo = TipoEntidad.objects.create(nombre="Asociación civil")
    subtipo = SubtipoEntidad.objects.create(nombre="Mutual", tipo_entidad=tipo)
    completa = Organizacion.objects.create(
        nombre="Org <Norte>",
        cuit=20123456789,
        telefono=1144445555,
        email="norte@example.com",
        tipo_entidad=tipo,
        subtipo_entidad=subtipo,
    )
    Comedor.objects.create(nombre="Comedor Norte A", organizacion=completa)
    Comedor.objects.create(nombre="Comedor Norte B", organizacion=completa)
    vacia = Organizacion.objects.create(nombre="Org Vacía")
    extra = [
        Organizacion.objects.create(nombre=f"Org Extra {i:02d}", email=f"e{i}@x.org")
        for i in range(max(cantidad - 2, 0))
    ]
    return completa, vacia, extra


def _comparar(data, nativa):
    assert [r["cells"] for r in data["results"]] == [
        f["cells"][:7] for f in nativa.rows
    ]


def test_list_projects_the_native_rows_and_actions(web):
    completa, vacia, _ = _organizaciones()
    data = web.get(API).json()
    nativa, _ = _nativa(web)

    _comparar(data, nativa)
    assert [r["id"] for r in data["results"]][:2] == [
        Organizacion.objects.order_by("-id")[0].pk,
        Organizacion.objects.order_by("-id")[1].pk,
    ]
    norte = next(r for r in data["results"] if r["id"] == completa.pk)
    assert norte["cells"] == [
        {"text": "20123456789", "sort": "20123456789"},
        {"text": "Org <Norte>", "sort": "Org <Norte>"},
        {"text": "2", "sort": "2"},
        {"text": "Asociación civil", "sort": "Asociación civil"},
        {"text": "Mutual", "sort": "Mutual"},
        {"text": "1144445555", "sort": "1144445555"},
        {"text": "norte@example.com", "sort": "norte@example.com"},
    ]
    sin_datos = next(r for r in data["results"] if r["id"] == vacia.pk)
    assert [c["text"] for c in sin_datos["cells"]] == [
        "-",
        "Org Vacía",
        "0",
        "-",
        "-",
        "-",
        "-",
    ]
    assert [c["sort"] for c in sin_datos["cells"]] == ["", "Org Vacía", "0"] + [""] * 4
    assert norte["detail_url"] == f"/organizaciones/detalle/{completa.pk}"
    assert norte["actions"] == [
        {
            "label": "Ver",
            "url": f"/organizaciones/detalle/{completa.pk}",
            "class": "btn btn-primary link-handler",
            "title": "Ver detalle de la organización",
            "icon": "fas fa-eye",
        },
        {
            "label": "Editar",
            "url": f"/organizaciones/editar/{completa.pk}",
            "class": "btn btn-editar link-handler",
            "title": "Editar organización",
            "icon": "fas fa-edit",
        },
        {
            "label": "Eliminar",
            "url": f"/organizaciones/eliminar/{completa.pk}",
            "class": "btn btn-eliminar link-handler",
            "title": "Eliminar organización",
            "icon": "fas fa-trash-alt",
        },
    ]
    acciones_nativas = [
        (link["text"], link["url"], link["class"], link["title"])
        for link in nativa.links
        if link["url"].endswith(f"/{completa.pk}")
    ]
    assert acciones_nativas[1:] == [
        (a["label"], a["url"], a["class"], a["title"]) for a in norte["actions"]
    ]


def test_payload_carries_the_native_page_frame(web):
    data = web.get(API).json()

    assert data["breadcrumb"] == [
        {"text": "Organizaciones", "url": "/organizaciones/listar"},
        {"text": "Listar", "url": None},
    ]
    assert data["urls"] == {
        "list": "/organizaciones/listar",
        "reset": "/organizaciones/listar",
        "add": "/organizaciones/crear",
        "export": "/organizaciones/exportar",
    }
    assert data["favorites"] == {
        "section": "",
        "url": "/ajax/filtros-favoritos/",
        "detail_url_template": "/ajax/filtros-favoritos/0/",
    }
    assert data["can_add"] is True
    assert data["can_export"] is False
    assert data["results"] == []
    assert data["empty"] == "No hay organizaciones disponibles."
    nativa, html = _nativa(web)
    assert nativa.empty == data["empty"]
    assert "Exportar búsqueda" not in html
    names = [f["name"] for f in data["filters_config"]["fields"]]
    assert "nombre" in names and "codigo_de_proyecto" in names
    assert data["page"] == {
        "is_paginated": False,
        "number": 1,
        "previous": None,
        "next": None,
        "range": [],
        "query_prefix": "",
    }
    assert data["messages"] == []


def test_pagination_is_the_native_no_count_window(web):
    _organizaciones(cantidad=24)
    primera = web.get(API).json()
    assert len(primera["results"]) == 10
    assert primera["page"] == {
        "is_paginated": True,
        "number": 1,
        "previous": None,
        "next": 2,
        "range": [1, 2, "…"],
        "query_prefix": "",
    }
    params = {"busqueda": "Org", "filters": '{"items":[]}', "page": "3"}
    tercera = web.get(API, params).json()
    nativa, html = _nativa(web, params)
    _comparar(tercera, nativa)
    assert len(tercera["results"]) == 4
    assert tercera["page"]["range"] == [1, 2, 3]
    prefijo = tercera["page"]["query_prefix"]
    assert prefijo == "busqueda=Org&filters=%7B%22items%22%3A%5B%5D%7D&"
    assert ("2", f"?{prefijo}page=2") in nativa.pages
    assert "Se encontraron" not in html
    # Out of range: the native paginator falls back to the last non-empty page.
    fuera = web.get(API, {"page": "99"}).json()
    assert fuera["page"]["number"] == 3
    assert [r["id"] for r in fuera["results"]] == [
        r["id"] for r in web.get(API, {"page": "3"}).json()["results"]
    ]
    assert web.get(API, {"page": "x"}).json()["page"]["number"] == 1


@pytest.mark.parametrize(
    "params",
    [
        {"busqueda": "norte"},
        {"busqueda": "20123456789"},
        {"busqueda": "1144445555"},
        {
            "filters": json.dumps(
                {"items": [{"field": "nombre", "op": "contains", "value": "extra"}]}
            )
        },
        {
            "filters": json.dumps(
                {"items": [{"field": "comedor", "op": "contains", "value": "Norte"}]}
            )
        },
        {"filters": "{roto"},
    ],
)
def test_search_and_filters_are_the_native_queryset(web, params):
    _organizaciones(cantidad=5)
    data = web.get(API, params).json()
    nativa, _ = _nativa(web, params)
    _comparar(data, nativa)
    assert data["results"] or nativa.empty


def test_technicians_and_lawyers_see_only_their_dupla(client):
    completa, vacia, _ = _organizaciones()
    tecnico = _usuario("tecnico_org", "auth.role_tecnico_comedor")
    abogado = _usuario("abogado_org", "auth.role_abogado_dupla")
    dupla = Dupla.objects.create(nombre="D", estado="Activo", abogado=abogado)
    dupla.tecnico.add(tecnico)
    Comedor.objects.filter(organizacion=completa).update(dupla=dupla)
    for usuario in (tecnico, abogado):
        web = _client(usuario)
        data = web.get(API).json()
        nativa, html = _nativa(web)
        _comparar(data, nativa)
        assert [r["id"] for r in data["results"]] == [completa.pk]
        assert data["can_add"] is False
        assert [a["label"] for a in data["results"][0]["actions"]] == ["Ver"]
        assert 'href="/organizaciones/crear"' not in html
    assert vacia.pk not in [
        r["id"] for r in _client(tecnico).get(API).json()["results"]
    ]


def test_without_the_codes_both_answer_403(client):
    client.force_login(_usuario("sin_org"))
    assert client.get(API).status_code == 403
    assert client.get(NATIVO).status_code == 403


def test_export_button_follows_the_search_bar_rule(client):
    _organizaciones()
    exporta = _client(
        _usuario("exporta_org", "auth.role_tecnico_comedor", "auth.role_exportar_a_csv")
    )
    assert exporta.get(API).json()["can_export"] is True
    assert "Exportar búsqueda" in _nativa(exporta)[1]
    superuser = _client(_usuario("super_org", is_superuser=True, is_staff=True))
    assert superuser.get(API).json()["can_export"] is True
    # The CSV stays the native GET with its own double check.
    assert (
        _client(_usuario("view_org2", VIEW)).get("/organizaciones/exportar").status_code
        == 403
    )
    respuesta = exporta.get("/organizaciones/exportar", {"busqueda": "Norte"})
    assert respuesta.status_code == 200
    assert 'filename="exportacion_organizaciones_' in respuesta["Content-Disposition"]


def test_anonymous_gets_401_and_a_pending_requirement_403(client, lector):
    respuesta = client.get(API)
    assert respuesta.status_code == 401
    assert respuesta.json() == {"detail": web_gate.DETAIL_UNAUTHENTICATED}
    lector.profile.must_change_password = True
    lector.profile.save()
    client.force_login(lector)
    respuesta = client.get(API)
    assert respuesta.status_code == 403
    assert respuesta.json()["state"] == "password_change_required"


def test_read_only_get_without_writes(web):
    _organizaciones()
    for metodo in ("post", "put", "patch", "delete"):
        assert getattr(web, metodo)(API).status_code == 405, metodo
    with CaptureQueriesContext(connection) as consultas:
        assert web.get(API).status_code == 200
    escrituras = [
        q["sql"]
        for q in consultas.captured_queries
        if q["sql"].lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))
    ]
    assert escrituras == []


def test_pending_messages_are_consumed_like_the_native_page(web, lector):
    organizacion = Organizacion.objects.create(nombre="Para baja")
    # The native delete queues a success message and redirects to the list.
    baja = web.post(f"/organizaciones/eliminar/{organizacion.pk}")
    assert baja.status_code == 302

    assert web.get(API).json()["messages"] == [
        {
            "message": "La organización Para baja fue dada de baja correctamente.",
            "level": "success",
        }
    ]
    assert web.get(API).json()["messages"] == []


def test_admindocs_head_does_not_bypass_the_web_api(client):
    client.force_login(
        _ready(get_user_model().objects.create_user("staff_org", is_staff=True))
    )

    respuesta = client.head(API)

    assert respuesta.status_code == 403
    assert "X-View" not in respuesta


@pytest.fixture(name="runtime")
def runtime_fixture():
    with override_settings(
        SISOC_BACKEND="comedores",
        ROOT_URLCONF="comedores_runtime.urls",
        SISOC_BACKENDS={},
        INTERNAL_IPS=[],
    ):
        yield


@pytest.mark.usefixtures("runtime")
def test_runtime_serves_only_signed_reads(web, lector):
    firma = web_gate.sign(
        audience="comedores",
        user_pk=lector.pk,
        session_key=web.cookies[settings.SESSION_COOKIE_NAME].value,
        method="GET",
        target=API,
    )
    assert web.get(API, RAW_URI=API).status_code == 403
    assert web.get(API, RAW_URI=API, HTTP_X_SISOC_WEB_GATE=firma).status_code == 200
