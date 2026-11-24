"""Web API (G1 v1) of the global list of monthly rendiciones (RM01.01).

``/api/web/comedores/rendicioncuentasmensual/listado/`` runs the native
``RendicionCuentaMensualGlobalListView``. The tests compare every projected
value with the native HTML page and pin today's access: any of the five codes
of ``rendicioncuentasmensual/urls.py``, no object scope, and the CSV kept as
the native ``?export=csv`` GET.
"""

import json
from datetime import date
from html.parser import HTMLParser

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.template.defaultfilters import urlencode
from django.test import Client, RequestFactory, override_settings
from django.test.utils import CaptureQueriesContext

from comedores.models import Comedor
from core import web_gate
from organizaciones.models import Organizacion, ProyectoOrganizacion
from rendicioncuentasmensual.models import RendicionCuentaMensual
from rendicioncuentasmensual.views import RendicionCuentaMensualGlobalListView

API = "/api/web/comedores/rendicioncuentasmensual/listado/"
NATIVO = "/rendicioncuentasmensual/rendicioncuentasmensual/listado/"
CODES = [
    "rendicioncuentasmensual.view_rendicioncuentamensual",
    "rendicioncuentasmensual.manage_territorial_stage",
    "rendicioncuentasmensual.manage_auditoria_review_stage",
    "rendicioncuentasmensual.manage_auditoria_stage",
    "rendicioncuentasmensual.manage_regularizacion_stage",
]
R = RendicionCuentaMensual

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


def _client(usuario, **extra):
    client = Client(**extra)
    client.force_login(usuario)
    return client


@pytest.fixture(name="lector")
def lector_fixture():
    return _usuario("lector_rm", CODES[0])


@pytest.fixture(name="web")
def web_fixture(lector):
    return _client(lector)


class _Tabla(HTMLParser):
    """Rows of the native ``table-comedor-moderno``: text and badge per cell."""

    def __init__(self):
        super().__init__()
        self.headers, self.rows = [], []
        self._zona = self._celda = None
        self._badge = None
        self._href = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "table" and "table-comedor-moderno" in (attrs.get("class") or ""):
            self._zona = "table"
        elif self._zona and tag in ("thead", "tbody"):
            self._zona = tag
        elif self._zona == "tbody" and tag == "tr":
            self.rows.append([])
        elif self._zona in ("thead", "tbody") and tag in ("th", "td"):
            self._celda, self._badge, self._href = [], None, None
        elif self._celda is not None and tag == "span":
            self._badge = attrs.get("class")
        elif self._celda is not None and tag == "a":
            self._href = attrs.get("href")

    def handle_endtag(self, tag):
        if tag == "table" and self._zona:
            self._zona = None
        if tag not in ("th", "td") or self._celda is None:
            return
        texto = " ".join("".join(self._celda).split())
        if self._zona == "thead":
            self.headers.append(texto)
        else:
            self.rows[-1].append(
                {"text": texto, "badge": self._badge, "href": self._href}
            )
        self._celda = None

    def handle_data(self, data):
        if self._celda is not None:
            self._celda.append(data)


def _nativa(client, params=None):
    respuesta = client.get(NATIVO, params or {})
    assert respuesta.status_code == 200
    tabla = _Tabla()
    tabla.feed(respuesta.content.decode())
    return tabla


def _rendiciones():
    organizacion = Organizacion.objects.create(nombre="Org <Norte>")
    comedor = Comedor.objects.create(
        nombre="Comedor RM", organizacion=organizacion, codigo_de_proyecto="P-77"
    )
    completa = R.objects.create(
        comedor=comedor,
        mes=3,
        anio=2026,
        convenio="P01",
        numero_rendicion=2,
        periodo_inicio=date(2026, 3, 1),
        periodo_fin=date(2026, 3, 31),
        etapa_proceso=R.ETAPA_REVISION_DOCUMENTACION,
        subestado_proceso=R.SUBESTADO_PENDIENTE_CORRECCIONES,
    )
    proyecto = ProyectoOrganizacion.objects.create(
        organizacion=organizacion, codigo="PROY-RM"
    )
    sin_comedor = R.objects.create(
        proyecto=proyecto,
        mes=4,
        anio=2026,
        etapa_proceso=R.ETAPA_AUDITORIA,
        subestado_proceso=R.SUBESTADO_FINALIZADA,
    )
    sin_organizacion = R.objects.create(
        comedor=Comedor.objects.create(nombre="Sin org"), mes=5, anio=2025
    )
    return completa, sin_comedor, sin_organizacion


def _ids(data):
    return [fila["id"] for fila in data["results"]]


# --- Rows, headers and columns -------------------------------------------------


def test_list_projects_the_native_rows_cells_and_badges(web):
    completa, sin_comedor, sin_organizacion = _rendiciones()

    respuesta = web.get(API)

    assert respuesta.status_code == 200
    assert respuesta["Cache-Control"] == "private, no-store"
    data = respuesta.json()
    nativa = _nativa(web)
    assert data["headers"] == nativa.headers[:-1]
    assert nativa.headers[-1] == "Acciones"
    assert data["headers"] == [
        "Proyecto",
        "Organización",
        "Convenio",
        "Rendición",
        "Período",
        "Etapa",
        "Estado",
        "Última modificación",
    ]
    assert _ids(data) == [sin_organizacion.pk, sin_comedor.pk, completa.pk]
    for fila, celdas in zip(data["results"], nativa.rows):
        assert [{"text": c["text"], "badge": c["badge"]} for c in celdas[:-1]] == [
            {"text": c["text"], "badge": c["badge"]} for c in fila["cells"]
        ]
        assert celdas[-1]["href"] == fila["detail_url"]
    por_id = {fila["id"]: fila["cells"] for fila in data["results"]}
    assert [c["text"] for c in por_id[completa.pk]][:7] == [
        "P-77",
        "Org <Norte>",
        "P01",
        "2",
        "01/03/2026 - 31/03/2026",
        "Revisión Territorial",
        "Revisión Territorial pendiente de correcciones",
    ]
    assert por_id[completa.pk][5]["badge"] == "badge etapa-badge etapa-territorial"
    assert por_id[completa.pk][6]["badge"] == "badge-validacion no-validado"
    sin = [c["text"] for c in por_id[sin_comedor.pk]]
    assert sin[:5] == [
        "Sin proyecto",
        "Sin organización",
        "-",
        str(sin_comedor.pk),
        "4/2026",
    ]
    assert sin[6] == "Auditoría finalizada sin observaciones"
    assert por_id[sin_comedor.pk][6]["badge"] == "badge-validacion validado"
    assert por_id[sin_organizacion.pk][6]["badge"] == "badge-validacion pendiente"
    assert data["results"][0]["detail_url"] == (
        f"/rendicioncuentasmensual/rendicioncuentasmensual/detalle/{sin_organizacion.pk}/"
    )


def test_payload_carries_the_native_page_frame(web):
    data = web.get(API).json()

    assert data["breadcrumb"] == [
        {"text": "Organizaciones", "url": "/organizaciones/listar"},
        {"text": "Rendiciones", "url": None},
    ]
    assert data["urls"]["list"] == NATIVO
    assert data["urls"]["reset"] == NATIVO
    assert data["urls"]["nueva_auditoria"] == (
        "/rendicioncuentasmensual/rendicioncuentasmensual/auditoria/"
    )
    assert data["favorites"] == {
        "section": "rendiciones",
        "url": "/ajax/filtros-favoritos/",
        "detail_url_template": "/ajax/filtros-favoritos/0/",
    }
    campos = {f["name"]: f for f in data["filters_config"]["fields"]}
    assert data["filters_config"]["defaultField"] == "codigo_proyecto"
    assert campos["mes"]["input"] == {"min": "1", "max": "12"}
    assert campos["documento_adjunto"]["type"] == "boolean"
    assert len(campos["estado_proceso"]["choices"]) == 15
    assert data["columns"]["list_key"] == "rendiciones_global_list"
    assert data["columns"]["endpoint"] == "/ajax/columnas-preferencias/"
    disponibles = {c["key"]: c for c in data["columns"]["available"]}
    # The resolution keeps ``proyecto`` (``required_keys``), but the native modal
    # does not mark it: ``available`` carries ``required: False`` for every column.
    assert {c["required"] for c in disponibles.values()} == {False}
    assert "proyecto" in data["columns"]["active"]
    assert disponibles["territorial_asignado"]["active"] is False
    assert data["results"] == []
    assert data["page"]["count"] == 0
    assert data["messages"] == []


def test_list_applies_the_saved_column_preferences(web):
    completa, _sin_comedor, _sin_org = _rendiciones()
    guardado = web.post(
        "/ajax/columnas-preferencias/",
        data=json.dumps(
            {
                "list_key": "rendiciones_global_list",
                "columns": ["estado", "territorial_asignado", "convenio"],
            }
        ),
        content_type="application/json",
    )
    assert guardado.status_code == 200

    data = web.get(API).json()

    # ``proyecto`` is required: the native resolution adds it to the selection.
    assert data["headers"] == _nativa(web).headers[:-1]
    assert sorted(data["headers"]) == [
        "Convenio",
        "Estado",
        "Proyecto",
        "Territorial asignado",
    ]
    fila = next(f for f in data["results"] if f["id"] == completa.pk)
    celdas = dict(zip(data["headers"], (c["text"] for c in fila["cells"])))
    assert celdas["Convenio"] == "P01"
    assert celdas["Territorial asignado"] == "-"


# --- Filters ---------------------------------------------------------------------


def _filtros(*items):
    return {"filters": json.dumps({"logic": "AND", "items": list(items)})}


def _nativos(params):
    vista = RendicionCuentaMensualGlobalListView()
    vista.request = RequestFactory().get(NATIVO, params)
    return [r.pk for r in vista.get_queryset()]


@pytest.mark.parametrize(
    "items",
    [
        [{"field": "estado_proceso", "op": "eq", "value": "auditoria:finalizada"}],
        [{"field": "estado_proceso", "op": "ne", "value": "auditoria:finalizada"}],
        [{"field": "estado_proceso", "op": "eq", "value": "nada:otra"}],
        [{"field": "mes", "op": "eq", "value": "3"}],
        [{"field": "codigo_proyecto", "op": "contains", "value": "p-7"}],
        [{"field": "organizacion", "op": "contains", "value": "norte"}],
    ],
)
def test_filters_are_the_native_queryset(web, items):
    _rendiciones()
    params = _filtros(*items)

    data = web.get(API, params).json()

    assert _ids(data) == _nativos(params)
    assert len(data["results"]) == len(_nativa(web, params).rows)


def test_territorial_filter_and_broken_json_are_the_native_ones(web):
    territorial = _usuario("territorial_rm", first_name="Tere", last_name="Rial")
    organizacion = Organizacion.objects.create(nombre="Org T")
    organizacion.territoriales_abordaje_comunitario.add(territorial)
    asignada = R.objects.create(
        comedor=Comedor.objects.create(nombre="C T", organizacion=organizacion),
        mes=1,
        anio=2026,
    )
    otra = R.objects.create(mes=2, anio=2026)
    eq = _filtros(
        {"field": "territorial_asignado", "op": "eq", "value": str(territorial.pk)}
    )
    ne = _filtros(
        {"field": "territorial_asignado", "op": "ne", "value": str(territorial.pk)}
    )

    assert _ids(web.get(API, eq).json()) == _nativos(eq) == [asignada.pk]
    assert _ids(web.get(API, ne).json()) == _nativos(ne) == [otra.pk]
    roto = {"filters": "{no es json"}
    assert _ids(web.get(API, roto).json()) == _nativos(roto) == [otra.pk, asignada.pk]


# --- Pagination --------------------------------------------------------------------


def test_pagination_is_the_native_one_and_an_invalid_page_is_404(web):
    for mes in range(1, 13):
        for anio in (2024, 2025, 2026):
            R.objects.create(mes=mes, anio=anio)
    params = {**_filtros({"field": "anio", "op": "ne", "value": "1999"}), "page": "2"}

    data = web.get(API, params).json()

    pagina = data["page"]
    assert pagina["is_paginated"] is True
    assert pagina["number"] == 2
    assert pagina["count"] == 36
    assert pagina["previous"] == 1
    assert pagina["next"] is None
    assert pagina["range"] == [1, 2]
    assert pagina["query_without_page"] == f"filters={urlencode(params['filters'])}&"
    assert len(data["results"]) == len(_nativa(web, params).rows) == 11
    for page in ("3", "abc", "0"):
        assert web.get(API, {"page": page}).status_code == 404, page
        assert web.get(NATIVO, {"page": page}).status_code == 404, page
    assert web.get(API, {"page": "last"}).json()["page"]["number"] == 2


# --- CSV (native GET) ----------------------------------------------------------------


def test_export_url_is_the_native_get_with_the_current_filters(client):
    params = _filtros({"field": "mes", "op": "eq", "value": "3"})
    exportador = _usuario("exporta_rm", CODES[0], "auth.role_exportar_a_csv")
    client.force_login(exportador)
    _rendiciones()

    data = client.get(API, params).json()

    assert data["can_export"] is True
    assert data["urls"]["export"].startswith(NATIVO + "?filters=")
    assert data["urls"]["export"].endswith("&export=csv")
    csv = client.get(data["urls"]["export"])
    assert csv.status_code == 200
    assert csv["Content-Type"].startswith("text/csv")
    contenido = b"".join(csv.streaming_content).decode("utf-8-sig")
    assert contenido.splitlines()[0].split(";")[0] == "Proyecto"
    assert len(contenido.strip().splitlines()) == 2
    assert client.get(API).json()["urls"]["export"] == f"{NATIVO}?export=csv"


def test_export_button_and_csv_need_the_export_role_or_superuser(web, client):
    assert web.get(API).json()["can_export"] is False
    assert web.get(NATIVO, {"export": "csv"}).status_code == 403
    client.force_login(_usuario("super_rm", is_superuser=True))
    assert client.get(API).json()["can_export"] is True


# --- Access ---------------------------------------------------------------------------


@pytest.mark.parametrize("code", CODES)
def test_any_of_the_five_codes_reads_the_whole_list(client, code):
    _rendiciones()
    client.force_login(_usuario(f"u_{code.split('.')[1]}", code))

    respuesta = client.get(API)

    assert respuesta.status_code == 200
    assert len(respuesta.json()["results"]) == 3
    assert client.get(NATIVO).status_code == 200


def test_without_the_codes_both_answer_403(client):
    client.force_login(_usuario("sin_rm", "auth.role_exportar_a_csv"))
    assert client.get(API).status_code == 403
    assert client.get(NATIVO).status_code == 403


def test_nueva_auditoria_button_follows_the_django_permission(client):
    client.force_login(
        _usuario("auditor_rm", "rendicioncuentasmensual.manage_auditoria_stage")
    )
    assert client.get(API).json()["can_nueva_auditoria"] is True
    client.force_login(_usuario("territorial2_rm", CODES[1]))
    assert client.get(API).json()["can_nueva_auditoria"] is False
    client.force_login(_usuario("root_rm", is_superuser=True))
    assert client.get(API).json()["can_nueva_auditoria"] is True


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
    _rendiciones()
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


def test_pending_messages_are_consumed_like_the_native_page(web):
    rendicion = R.objects.create(mes=1, anio=2026)
    # The native PDF download queues an error and redirects to the detail.
    descarga = web.get(
        f"/rendicioncuentasmensual/rendicioncuentasmensual/detalle/{rendicion.pk}/descargar-pdf/"
    )
    assert descarga.status_code == 302

    assert web.get(API).json()["messages"] == [
        {
            "message": "La descarga consolidada solo está disponible cuando la "
            "rendición está finalizada.",
            "level": "error",
        }
    ]
    assert web.get(API).json()["messages"] == []


def test_admindocs_head_does_not_bypass_the_web_api(client):
    client.force_login(
        _ready(get_user_model().objects.create_user("staff_rm", is_staff=True))
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
