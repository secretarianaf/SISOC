"""Web API (G1 v1) of the final rendición screens (RF01.01).

``/api/web/comedores/rendicion_cuentas_final/`` runs the native detail view and
the native area-scoped document list. The tests compare every projected value
with the native HTML and AJAX answers and pin the access: the web endpoints
need ``view_rendicioncuentasfinal`` (the native screens' own guard).
"""

from datetime import timedelta
from html.parser import HTMLParser

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db import connection
from django.test import Client, override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from comedores.models import Comedor
from core import web_gate
from duplas.models import Dupla
from django.contrib.contenttypes.models import ContentType
from historial.models import Historial
from rendicioncuentasfinal.models import (
    DocumentoRendicionFinal,
    EstadoDocumentoRendicionFinal,
    RendicionCuentasFinal,
    TipoDocumentoRendicionFinal,
)

BASE = "/api/web/comedores/rendicion_cuentas_final/"
DETALLE = BASE + "comedor/{}/"
DOCUMENTOS = BASE + "documentos/"
NATIVO_LISTAR = "/rendicion_cuentas_final/listar/"
NATIVO_AJAX = "/rendicion_cuentas_final/ajax/"
NATIVO_DETALLE = "/comedores/{}/rendicion_cuentas_final/"
VIEW = "rendicioncuentasfinal.view_rendicioncuentasfinal"

pytestmark = pytest.mark.django_db


def _ready(user):
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    return user


def _usuario(nombre, *codes, **extra):
    usuario = _ready(get_user_model().objects.create_user(nombre, **extra))
    for code in codes:
        app, codename = code.split(".")
        usuario.user_permissions.add(
            Permission.objects.get(content_type__app_label=app, codename=codename)
        )
    return usuario


def _client(usuario):
    client = Client()
    client.force_login(usuario)
    return client


@pytest.fixture(name="estados")
def estados_fixture():
    return {
        nombre: EstadoDocumentoRendicionFinal.objects.create(pk=pk, nombre=nombre)
        for pk, nombre in enumerate(
            ["No presentado", "En análisis", "Validado", "Subsanar"], start=1
        )
    }


@pytest.fixture(name="tipos")
def tipos_fixture():
    return {
        validador: TipoDocumentoRendicionFinal.objects.create(
            nombre=f"Informe {validador}", validador=validador
        )
        for validador in ("Dupla", "Contable", "Legales")
    }


@pytest.fixture(name="lector")
def lector_fixture():
    return _usuario("lector_rf", VIEW)


@pytest.fixture(name="web")
def web_fixture(lector):
    return _client(lector)


def _documentos(comedor, estados, tipos, ahora=None):
    """One rendición with one document per type and a different state each."""
    ahora = ahora or timezone.now()
    rendicion = RendicionCuentasFinal.objects.create(comedor=comedor)
    docs = {d.tipo.validador: d for d in rendicion.documentos.select_related("tipo")}
    docs["Dupla"].estado = estados["En análisis"]
    docs["Dupla"].documento = "rendicion_cuentas_final/dupla.pdf"
    docs["Dupla"].fecha_modificacion = ahora
    docs["Contable"].estado = estados["Subsanar"]
    docs["Contable"].observaciones = "Falta <firma>"
    docs["Contable"].fecha_modificacion = ahora - timedelta(days=1)
    docs["Legales"].estado = estados["Validado"]
    docs["Legales"].fecha_modificacion = ahora - timedelta(days=2)
    for doc in docs.values():
        doc.save()
    return rendicion, docs


def _historial(documento, accion, usuario):
    return Historial.objects.create(
        accion=accion,
        usuario=usuario,
        content_type=ContentType.objects.get_for_model(DocumentoRendicionFinal),
        object_id=str(documento.pk),
    )


class _Filas(HTMLParser):
    """Text of the cells of every ``<tr>`` plus links and disabled buttons."""

    def __init__(self):
        super().__init__()
        self.filas, self._celda, self._clases = [], None, []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "tr":
            self.filas.append({"celdas": [], "clase": attrs.get("class"), "hrefs": []})
        elif tag in ("td", "th"):
            self._celda = []
        elif tag == "a" and self.filas and attrs.get("href"):
            self.filas[-1]["hrefs"].append(attrs["href"])

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._celda is not None and self.filas:
            self.filas[-1]["celdas"].append(" ".join("".join(self._celda).split()))
            self._celda = None

    def handle_data(self, data):
        if self._celda is not None:
            self._celda.append(data)


def _filas(html):
    parser = _Filas()
    parser.feed(html)
    return parser.filas


def _tabla_nativa(client, comedor_filas=True):
    respuesta = client.get(NATIVO_LISTAR)
    assert respuesta.status_code == 200
    html = respuesta.content.decode()
    cuerpo = html.split('id="rendicion-cuentas-table-body"', 1)[1].split("</tbody>")[0]
    return _filas(cuerpo)


# --- List ---------------------------------------------------------------------


def test_list_projects_the_native_rows(web, estados, tipos):
    comedor = Comedor.objects.create(nombre="Comedor <Uno>")
    _documentos(comedor, estados, tipos)
    nativas = _tabla_nativa(web)

    respuesta = web.get(DOCUMENTOS)

    assert respuesta.status_code == 200
    assert respuesta["Cache-Control"] == "private, no-store"
    data = respuesta.json()
    assert data["page_size"] is None
    assert data["pages"] == 1
    assert data["count"] == len(data["results"]) == 3
    assert data["filters"] == {"busqueda": ""}
    # Native order (``-fecha_modificacion``) and cell text; the date is local time.
    assert [f["estado"] for f in data["results"]] == [
        "En análisis",
        "Subsanar",
        "Validado",
    ]
    for fila, nativa in zip(data["results"], nativas):
        assert nativa["clase"] == f"documento-row estado-{fila['estado_slug']}"
        assert nativa["celdas"][:4] == [
            fila["tipo_nombre"],
            fila["comedor_nombre"],
            fila["fecha_modificacion"],
            fila["estado"],
        ]
    assert data["results"][0]["comedor_nombre"] == "Comedor <Uno>"
    assert [f["accionable"] for f in data["results"]] == [True, False, False]
    assert (
        data["results"][0]["archivo_url"] == "/media/rendicion_cuentas_final/dupla.pdf"
    )
    assert data["results"][1]["archivo_url"] is None
    assert nativas[0]["hrefs"] == ["/media/rendicion_cuentas_final/dupla.pdf"]


def test_list_filters_states_and_orders_by_modification(web, estados, tipos):
    comedor = Comedor.objects.create(nombre="C")
    _, docs = _documentos(comedor, estados, tipos)
    otra = RendicionCuentasFinal.objects.create(
        comedor=Comedor.objects.create(nombre="D")
    )
    # «No presentado» documents never show; a null date sorts after the dated ones.
    assert {d.estado.nombre for d in otra.documentos.all()} == {"No presentado"}
    DocumentoRendicionFinal.objects.filter(pk=docs["Legales"].pk).update(
        fecha_modificacion=None
    )

    data = _results(web)

    assert [f["estado"] for f in data] == ["En análisis", "Subsanar", "Validado"]


def _results(client, **params):
    respuesta = client.get(DOCUMENTOS, params)
    assert respuesta.status_code == 200
    return respuesta.json()["results"]


def test_search_by_comedor_and_by_type_matches_the_native_ajax(web, estados, tipos):
    uno = Comedor.objects.create(nombre="Alfa")
    dos = Comedor.objects.create(nombre="Beta")
    _documentos(uno, estados, tipos)
    _documentos(dos, estados, tipos)

    for busqueda in ("alfa", "BETA", "Contable", "zzz", ""):
        nativo = web.get(NATIVO_AJAX, {"busqueda": busqueda}).json()
        data = web.get(DOCUMENTOS, {"busqueda": busqueda}).json()
        assert data["count"] == nativo["count"], busqueda
        assert data["pages"] == nativo["num_pages"]
        assert data["page"] == nativo["current_page"]
        assert data["has_previous"] == nativo["has_previous"]
        assert data["has_next"] == nativo["has_next"]
        assert data["filters"] == {"busqueda": busqueda}
        nativas = _filas(nativo["html"])
        assert [f["comedor_nombre"] for f in data["results"]] == [
            n["celdas"][1] for n in nativas if len(n["celdas"]) > 1
        ]
    assert {f["comedor_nombre"] for f in _results(web, busqueda="alfa")} == {"Alfa"}
    assert {f["tipo_nombre"] for f in _results(web, busqueda="Contable")} == {
        "Informe Contable"
    }
    assert _results(web, busqueda="zzz") == []


def test_pagination_is_the_native_one_and_a_bad_page_does_not_fail(web, estados, tipos):
    comedor = Comedor.objects.create(nombre="Muchos")
    rendicion, docs = _documentos(comedor, estados, tipos)
    base = timezone.now()
    for indice in range(27):
        tipo = TipoDocumentoRendicionFinal.objects.create(
            nombre=f"Extra {indice}", validador="Dupla", personalizado=True
        )
        DocumentoRendicionFinal.objects.create(
            rendicion_final=rendicion,
            tipo=tipo,
            estado=estados["En análisis"],
            fecha_modificacion=base + timedelta(minutes=indice + 1),
        )

    sin_parametros = web.get(DOCUMENTOS).json()
    primera = web.get(DOCUMENTOS, {"page": "1"}).json()
    segunda = web.get(DOCUMENTOS, {"page": "2"}).json()

    assert sin_parametros["page_size"] is None and len(sin_parametros["results"]) == 30
    assert primera["page_size"] == 25 and primera["pages"] == 2
    assert len(primera["results"]) == 25 and len(segunda["results"]) == 5
    assert primera["has_next"] and not primera["has_previous"]
    assert segunda["has_previous"] and not segunda["has_next"]
    assert primera["range"] == [1, 2] and (primera["previous"], primera["next"]) == (
        None,
        2,
    )
    nativo = web.get(NATIVO_AJAX, {"page": "2"}).json()
    assert len(_filas(nativo["html"])) == len(segunda["results"])
    # An empty ``busqueda`` still paginates, like the AJAX call.
    assert web.get(DOCUMENTOS, {"busqueda": ""}).json()["page_size"] == 25
    for mala in ("abc", "999", "-3"):
        respuesta = web.get(DOCUMENTOS, {"page": mala})
        nativa = web.get(NATIVO_AJAX, {"page": mala}).json()
        assert respuesta.status_code == 200
        assert respuesta.json()["page"] == nativa["current_page"]


def test_list_scope_by_area_and_the_open_asymmetry(client, estados, tipos):
    comedor = Comedor.objects.create(nombre="Area")
    _documentos(comedor, estados, tipos)

    def validadores(usuario):
        respuesta = _client(usuario).get(DOCUMENTOS)
        assert respuesta.status_code == 200
        return sorted(
            {
                f["tipo_nombre"].removeprefix("Informe ")
                for f in respuesta.json()["results"]
            }
        )

    super_ = _usuario("super_rf", is_superuser=True)
    assert validadores(super_) == ["Contable", "Dupla", "Legales"]
    assert validadores(_usuario("view_comedor_rf", VIEW, "comedores.view_comedor")) == [
        "Contable",
        "Dupla",
        "Legales",
    ]
    assert validadores(
        _usuario("pago_rf", VIEW, "expedientespagos.view_expedientepago")
    ) == ["Contable", "Legales"]
    assert validadores(_usuario("admision_rf", VIEW, "admisiones.view_admision")) == [
        "Dupla",
        "Legales",
    ]
    # Kept on purpose: no area permission and not a coordinator sees every validator.
    assert validadores(_usuario("solo_rf", VIEW)) == ["Contable", "Dupla", "Legales"]


def test_coordinator_sees_only_the_assigned_duplas(estados, tipos):
    abogado = _usuario("abogado_rf")
    propia = Dupla.objects.create(nombre="Propia", abogado=abogado)
    ajena = Dupla.objects.create(nombre="Ajena", abogado=abogado)
    _documentos(
        Comedor.objects.create(nombre="De la dupla", dupla=propia), estados, tipos
    )
    _documentos(Comedor.objects.create(nombre="De otra", dupla=ajena), estados, tipos)
    coordinador = _usuario("coord_rf", VIEW)
    coordinador.profile.es_coordinador = True
    coordinador.profile.save()
    sin_duplas = _results(_client(coordinador))
    coordinador.profile.duplas_asignadas.add(propia)

    con_duplas = _results(_client(coordinador))

    assert sin_duplas == []
    assert {f["comedor_nombre"] for f in con_duplas} == {"De la dupla"}
    assert {f["tipo_nombre"] for f in con_duplas} == {"Informe Dupla"}


# --- Detail -------------------------------------------------------------------


def test_detail_projects_the_native_documents_and_history(web, lector, estados, tipos):
    comedor = Comedor.objects.create(nombre="Comedor <Detalle>")
    rendicion, docs = _documentos(comedor, estados, tipos)
    lector.first_name, lector.last_name = "Ana", "Pérez"
    lector.save()
    _historial(docs["Dupla"], "Validar documento", lector)
    nativa = web.get(NATIVO_DETALLE.format(comedor.pk))
    assert nativa.status_code == 200

    respuesta = web.get(DETALLE.format(comedor.pk))

    assert respuesta.status_code == 200
    assert respuesta["Cache-Control"] == "private, no-store"
    data = respuesta.json()
    assert data["rendicion"] == {"id": rendicion.pk, "fisicamente_presentada": False}
    assert data["comedor"] == {"id": comedor.pk, "nombre": "Comedor <Detalle>"}
    assert data["urls"]["comedor"] == f"/comedores/{comedor.pk}"
    assert [d["tipo_nombre"] for d in data["documentos"]] == [
        "Informe Dupla",
        "Informe Contable",
        "Informe Legales",
    ]
    by_tipo = {d["tipo_nombre"]: d for d in data["documentos"]}
    assert by_tipo["Informe Dupla"]["validable"] is True
    assert by_tipo["Informe Dupla"]["eliminable"] is True
    assert by_tipo["Informe Dupla"]["editable"] is False
    assert (
        by_tipo["Informe Dupla"]["archivo_url"]
        == "/media/rendicion_cuentas_final/dupla.pdf"
    )
    assert by_tipo["Informe Contable"]["observaciones"] == "Falta <firma>"
    assert by_tipo["Informe Contable"]["editable"] is True
    assert by_tipo["Informe Contable"]["validable"] is False
    assert by_tipo["Informe Legales"]["observaciones"] is None
    assert by_tipo["Informe Legales"]["validador"] == "Legales"
    html = nativa.content.decode()
    for doc in data["documentos"]:
        assert doc["tipo_nombre"] in html
        if doc["fecha_modificacion"]:
            assert doc["fecha_modificacion"] in html
    assert data["historial"] == [
        {
            "tipo_nombre": "Informe Dupla",
            "accion": "Validar documento",
            "usuario": "Ana Pérez",
            "fecha": data["historial"][0]["fecha"],
        }
    ]
    assert data["historial"][0]["fecha"] in html
    assert "Ana Pérez" in html


def test_history_without_type_name_and_empty_user(web, estados, tipos):
    comedor = Comedor.objects.create(nombre="Hist")
    _, docs = _documentos(comedor, estados, tipos)
    lector = get_user_model().objects.get(username="lector_rf")
    _historial(docs["Dupla"], "Uno", lector)
    _historial(docs["Contable"], "Dos", lector)
    DocumentoRendicionFinal.objects.filter(pk=docs["Contable"].pk).update(tipo=None)
    docs["Legales"].delete()
    # A row without user (SET_NULL) shows an empty user name.
    _historial(docs["Dupla"], "Tres", None)

    historial = web.get(DETALLE.format(comedor.pk)).json()["historial"]

    por_accion = {h["accion"]: h for h in historial}
    assert por_accion["Uno"]["tipo_nombre"] == "Informe Dupla"
    assert por_accion["Dos"]["tipo_nombre"] == "Desconocido"
    assert por_accion["Tres"]["usuario"] == ""
    assert por_accion["Uno"]["usuario"] == "lector_rf"


def test_detail_of_a_missing_comedor_is_404(web):
    assert web.get(DETALLE.format(987654)).status_code == 404
    assert web.get(NATIVO_DETALLE.format(987654)).status_code == 404


def test_detail_without_rendicion_creates_it_with_the_base_documents(
    web, estados, tipos
):
    comedor = Comedor.objects.create(nombre="Nuevo")
    extra = TipoDocumentoRendicionFinal.objects.create(
        nombre="Personalizado", validador="Dupla", personalizado=True
    )
    assert not RendicionCuentasFinal.objects.filter(comedor=comedor).exists()

    data = web.get(DETALLE.format(comedor.pk)).json()

    rendicion = RendicionCuentasFinal.objects.get(comedor=comedor)
    assert data["rendicion"]["id"] == rendicion.pk
    assert sorted(d["tipo_nombre"] for d in data["documentos"]) == sorted(
        t.nombre for t in tipos.values()
    )
    assert extra.nombre not in {d["tipo_nombre"] for d in data["documentos"]}
    assert {d["estado"] for d in data["documentos"]} == {"No presentado"}
    assert all(d["editable"] and not d["eliminable"] for d in data["documentos"])
    assert data["historial"] == []
    # A second call reuses the rendición (native ``get_or_create``).
    web.get(DETALLE.format(comedor.pk))
    assert RendicionCuentasFinal.objects.filter(comedor=comedor).count() == 1


def test_detail_reads_the_state_of_the_switch(web, estados, tipos):
    comedor = Comedor.objects.create(nombre="Switch")
    rendicion, _ = _documentos(comedor, estados, tipos)
    RendicionCuentasFinal.objects.filter(pk=rendicion.pk).update(
        fisicamente_presentada=True
    )

    assert web.get(DETALLE.format(comedor.pk)).json()["rendicion"][
        "fisicamente_presentada"
    ]


# --- Access and gate ----------------------------------------------------------


@pytest.mark.parametrize("url", [DOCUMENTOS, DETALLE.format(1)])
def test_without_the_screen_permission_answers_403(client, url):
    sin_permiso = _client(_usuario("sin_rf", "comedores.view_comedor"))
    assert sin_permiso.get(url).status_code == 403
    assert "detail" in sin_permiso.get(url).json()
    # The native screens refuse the same user.
    assert sin_permiso.get(NATIVO_LISTAR).status_code == 403


@pytest.mark.parametrize("url", [DOCUMENTOS, DETALLE.format(1)])
def test_a_superuser_and_the_permission_holder_read(client, url, estados, tipos):
    comedor = Comedor.objects.create(nombre="Uno")
    url = url.replace("/1/", f"/{comedor.pk}/")
    assert _client(_usuario("root_rf", is_superuser=True)).get(url).status_code == 200
    assert _client(_usuario("con_rf", VIEW)).get(url).status_code == 200


def test_anonymous_gets_401_and_a_pending_requirement_403(client, lector):
    respuesta = client.get(DOCUMENTOS)
    assert respuesta.status_code == 401
    assert respuesta.json() == {"detail": web_gate.DETAIL_UNAUTHENTICATED}
    assert client.get(DETALLE.format(1)).status_code == 401
    lector.profile.must_change_password = True
    lector.profile.save()
    client.force_login(lector)
    respuesta = client.get(DOCUMENTOS)
    assert respuesta.status_code == 403
    assert respuesta.json()["state"] == "password_change_required"


def test_list_is_read_only_and_only_get_is_served(web, estados, tipos):
    comedor = Comedor.objects.create(nombre="RO")
    _documentos(comedor, estados, tipos)
    for url in (DOCUMENTOS, DETALLE.format(comedor.pk)):
        for metodo in ("post", "put", "patch", "delete"):
            assert getattr(web, metodo)(url).status_code == 405, metodo
    with CaptureQueriesContext(connection) as consultas:
        assert web.get(DOCUMENTOS).status_code == 200
    escrituras = [
        q["sql"]
        for q in consultas.captured_queries
        if q["sql"].lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))
    ]
    assert escrituras == []


def test_pending_messages_are_consumed_like_the_native_page(web, estados, tipos):
    rendicion, docs = _documentos(Comedor.objects.create(nombre="Msg"), estados, tipos)
    # A native action queues a success message and redirects back.
    respuesta = web.post(
        f"/rendicion_cuentas_final/{rendicion.pk}/fisicamente_presentada/"
    )
    assert respuesta.status_code == 302

    assert web.get(DOCUMENTOS).json()["messages"] == [
        {"message": "Estado de revisión actualizado.", "level": "success"}
    ]
    assert web.get(DOCUMENTOS).json()["messages"] == []


def test_admindocs_head_does_not_bypass_the_web_api(client):
    client.force_login(
        _ready(get_user_model().objects.create_user("staff_rf", is_staff=True))
    )

    for url in (DOCUMENTOS, DETALLE.format(1)):
        respuesta = client.head(url)
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
        target=DOCUMENTOS,
    )
    assert web.get(DOCUMENTOS, RAW_URI=DOCUMENTOS).status_code == 403
    assert (
        web.get(DOCUMENTOS, RAW_URI=DOCUMENTOS, HTTP_X_SISOC_WEB_GATE=firma).status_code
        == 200
    )
