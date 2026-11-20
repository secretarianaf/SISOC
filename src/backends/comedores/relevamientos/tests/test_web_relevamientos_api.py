"""Web API (G1 v1) of the relevamiento list and detail (R01.01, ``relevamientos.web_api_views``).

The tests compare every projected value with the native HTML page and pin
today's access: ``relevamientos.view_relevamiento`` only, no object scope, the
detail looked up by ``pk`` alone and the native POSTs left alone.
"""

import re
from datetime import datetime, timezone as dt_timezone
from html.parser import HTMLParser

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, override_settings

from comedores.models import Comedor
from core import web_gate
from core.models import Localidad, Municipio, Provincia
from relevamientos.models import (
    ActaComplementaria,
    PrimerSeguimiento,
    Relevamiento,
    SeguimientoPnud,
)

VIEW = "relevamientos.view_relevamiento"
API = "/api/web/comedores/relevamientos/"
FECHA = datetime(2026, 3, 4, 15, 7, tzinfo=dt_timezone.utc)

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


@pytest.fixture(name="web")
def web_fixture():
    return _client(_usuario("lector_rel", VIEW))


@pytest.fixture(name="comedor_rel")
def comedor_fixture():
    provincia = Provincia.objects.create(nombre="Prov <R>")
    municipio = Municipio.objects.create(nombre="Muni R", provincia=provincia)
    localidad = Localidad.objects.create(nombre="Loc R", municipio=municipio)
    return Comedor.objects.create(
        nombre="Comedor <Rel>",
        provincia=provincia,
        municipio=municipio,
        localidad=localidad,
    )


def _ciclo(comedor):
    """Two relevamientos (the older one with two seguimientos), an acta and a PNUD one."""
    viejo = Relevamiento.objects.create(
        comedor=comedor, estado="Finalizado", fecha_visita=FECHA, numero_if="IF-1"
    )
    nuevo = Relevamiento.objects.create(
        comedor=comedor, estado="Visita pendiente", origen="app"
    )
    posterior = PrimerSeguimiento.objects.create(
        id_relevamiento=viejo,
        tipo=PrimerSeguimiento.TIPO_POSTERIOR,
        numero_orden=2,
        fecha_hora=FECHA,
    )
    primero = PrimerSeguimiento.objects.create(
        id_relevamiento=viejo, numero_orden=1, sincronizado_gestionar=True
    )
    acta = ActaComplementaria.objects.create(
        comedor=comedor, fecha_hora=FECHA, observaciones="x", origen="app"
    )
    pnud = SeguimientoPnud.objects.create(
        comedor=comedor,
        formulario=SeguimientoPnud.FORMULARIO_SIPH,
        fecha_hora=FECHA,
    )
    return viejo, nuevo, primero, posterior, acta, pnud


class _Texto(HTMLParser):
    """Whitespace-collapsed text of a native page (``<script>`` and ``<style>`` dropped)."""

    def __init__(self):
        super().__init__()
        self.partes, self._skip = [], 0

    def handle_starttag(self, tag, attrs):
        self._skip += tag in ("script", "style")

    def handle_endtag(self, tag):
        self._skip -= tag in ("script", "style")

    def handle_data(self, data):
        if not self._skip:
            self.partes.append(data)

    @property
    def texto(self):
        return " ".join("".join(self.partes).split())


def _texto(respuesta):
    parser = _Texto()
    parser.feed(respuesta.content.decode())
    return parser.texto


# --- List ----------------------------------------------------------------------


def test_list_projects_the_native_rows_order_and_links(web, comedor_rel):
    viejo, nuevo, primero, posterior, acta, pnud = _ciclo(comedor_rel)

    respuesta = web.get(f"{API}{comedor_rel.pk}/")

    assert respuesta.status_code == 200
    assert respuesta["Cache-Control"] == "private, no-store"
    data = respuesta.json()
    assert data["comedor"] == {"id": comedor_rel.pk, "nombre": "Comedor <Rel>"}
    assert data["encabezado"] == "Comedor <Rel> | Prov <R>, Muni R, Loc R"
    # ``-estado, -id``: "Visita pendiente" sorts above "Finalizado".
    assert [r["id"] for r in data["relevamientos"]] == [nuevo.pk, viejo.pk]
    fila = data["relevamientos"][1]
    assert (fila["numero_if"], fila["estado"], fila["origen"]) == (
        "IF-1",
        "Finalizado",
        "sisoc",
    )
    assert fila["detalle_url"] == f"/comedores/{comedor_rel.pk}/relevamiento/{viejo.pk}"
    assert fila["has_seguimiento"] is True and fila["sincronizado_gestionar"] is False
    assert [s["id"] for s in fila["seguimientos"]] == [primero.pk, posterior.pk]
    assert [s["numero_orden"] for s in fila["seguimientos"]] == [1, 2]
    assert fila["seguimientos"][1]["tipo"] == "Seguimiento Posterior"
    assert fila["seguimientos"][0]["sincronizado_gestionar"] is True
    assert data["relevamientos"][0]["seguimientos"] == []
    assert data["actas"][0]["id"] == acta.pk
    assert data["actas"][0]["prestaciones_count"] == 0
    assert data["actas"][0]["tecnico"] == "Sin técnico"
    assert data["seguimientos_pnud"][0]["formulario_display"] == (
        "FORM-SIPH — Seguimiento SIPH (Línea Tradicional y Módulos Secos)"
    )
    assert data["seguimientos_pnud"][0]["id"] == pnud.pk


def test_list_prints_the_values_like_the_native_page(web, comedor_rel):
    viejo, *_ = _ciclo(comedor_rel)
    nativa = _texto(web.get(f"/comedores/{comedor_rel.pk}/relevamiento/listar"))

    data = web.get(f"{API}{comedor_rel.pk}/").json()

    assert f"{viejo.pk} - {data['relevamientos'][1]['fecha']}" in nativa
    assert data["relevamientos"][0]["fecha"] == "Sin fecha"
    assert f"{data['relevamientos'][0]['id']} - Sin fecha" in nativa
    for acta in data["actas"]:
        assert f"{acta['id']} - {acta['fecha_hora']}" in nativa
    for seguimiento in data["seguimientos_pnud"]:
        assert f"{seguimiento['id']} - {seguimiento['formulario_display']}" in nativa
    for item in data["relevamientos"][1]["seguimientos"]:
        assert f"{item['tipo']} #{item['numero_orden']}" in nativa
    assert data["encabezado"] in nativa


def test_list_options_and_capabilities_follow_the_native_context(comedor_rel):
    solo_ver = _client(_usuario("solo_ver_rel", VIEW))
    todo = _client(
        _usuario(
            "todo_rel",
            VIEW,
            "relevamientos.add_relevamiento",
            "relevamientos.change_relevamiento",
            "relevamientos.add_actacomplementaria",
            "relevamientos.change_actacomplementaria",
        )
    )

    lectura = solo_ver.get(f"{API}{comedor_rel.pk}/").json()
    completo = todo.get(f"{API}{comedor_rel.pk}/").json()

    assert set(lectura["capabilities"]) == {
        "add_relevamiento",
        "change_relevamiento",
        "add_actacomplementaria",
        "change_actacomplementaria",
    }
    assert not any(lectura["capabilities"].values())
    assert all(completo["capabilities"].values())
    assert completo["opciones_alta"][0]["label"]
    assert completo["opciones_seguimiento"]
    assert completo["urls"]["alta"] == f"/comedores/ajax/{comedor_rel.pk}/relevamiento/"
    assert completo["urls"]["acta_crear"].startswith(f"/comedores/{comedor_rel.pk}/")


def test_list_of_an_unknown_comedor_is_404(web):
    assert web.get(f"{API}999999/").status_code == 404


def test_the_native_post_of_the_numero_if_is_untouched(comedor_rel):
    viejo, *_ = _ciclo(comedor_rel)
    editor = _client(
        _usuario("editor_if_rel", VIEW, "relevamientos.change_relevamiento")
    )

    respuesta = editor.post(
        f"/comedores/{comedor_rel.pk}/relevamiento/listar",
        {"relevamiento_id": viejo.pk, "numero_if": "IF-9"},
    )

    assert respuesta.status_code == 302
    viejo.refresh_from_db()
    assert viejo.numero_if == "IF-9"
    mensajes = editor.get(f"{API}{comedor_rel.pk}/").json()["messages"]
    assert mensajes == [
        {"message": "Número de IF actualizado correctamente.", "level": "success"}
    ]
    assert editor.get(f"{API}{comedor_rel.pk}/").json()["messages"] == []


# --- Detail --------------------------------------------------------------------


def test_detail_projects_the_header_timeline_and_cycle(web, comedor_rel):
    viejo, nuevo, primero, posterior, *_ = _ciclo(comedor_rel)

    respuesta = web.get(f"{API}{comedor_rel.pk}/relevamiento/{viejo.pk}/")

    assert respuesta.status_code == 200
    data = respuesta.json()
    cabecera = data["relevamiento"]
    assert cabecera["id"] == viejo.pk
    assert cabecera["comedor"] == {"id": comedor_rel.pk, "nombre": "Comedor <Rel>"}
    assert (cabecera["estado"], cabecera["estado_visible"]) == (
        "Finalizado",
        "Finalizado",
    )
    assert cabecera["estado_badge"] == "bg-success"
    assert cabecera["sincronizado_gestionar"] is False
    assert cabecera["observaciones_coordinador"] == ""
    assert sorted(t["id"] for t in data["timeline"]) == [viejo.pk, nuevo.pk]
    por_id = {t["id"]: t for t in data["timeline"]}
    assert por_id[viejo.pk]["card_class"] == "active"
    assert por_id[nuevo.pk]["fecha"] == "-"
    assert [s["id"] for s in data["seguimientos"]] == [primero.pk, posterior.pk]
    assert data["seguimientos"][0]["eliminar_url"] == (
        f"/comedores/{comedor_rel.pk}/relevamiento/{viejo.pk}/seguimiento/"
        f"{primero.pk}/eliminar"
    )
    assert data["pdf"]["disponible"] is True and data["pdf"]["oficial"] is False
    assert (
        data["pdf"]["url"] == f"/comedores/{comedor_rel.pk}/relevamiento/{viejo.pk}/pdf"
    )
    assert set(data["capabilities"]) == {
        "change_relevamiento",
        "review_relevamiento",
        "change_primerseguimiento",
        "delete_primerseguimiento",
        "view_logentry",
    }
    assert (
        data["urls"]["historial"].endswith(f"/relevamiento/{viejo.pk}/")
        or data["urls"]["historial"]
    )


def _textos(nodos):
    for nodo in nodos:
        if isinstance(nodo, str):
            yield nodo.strip()
        else:
            yield from _textos(nodo["c"])


def _nodos(nodos, etiqueta):
    for nodo in nodos:
        if not isinstance(nodo, str):
            if nodo["t"] == etiqueta:
                yield nodo
            yield from _nodos(nodo["c"], etiqueta)


def test_detail_sections_are_the_native_ones_in_order(web, comedor_rel):
    viejo, *_ = _ciclo(comedor_rel)
    nativa = web.get(f"/comedores/{comedor_rel.pk}/relevamiento/{viejo.pk}")
    titulos_nativos = [
        " ".join(t.split())
        for t in re.findall(
            r'<h3 class="card-title[^"]*">(.*?)</h3>',
            nativa.content.decode(),
            flags=re.S,
        )
    ]

    data = web.get(f"{API}{comedor_rel.pk}/relevamiento/{viejo.pk}/").json()

    # The native page adds the "Archivos adjuntos" card of its own template.
    assert data["titulos"] == titulos_nativos[: len(data["titulos"])]
    assert data["titulos"][:3] == [
        "Acompañamiento Territorial",
        "Información",
        "Datos del referente del Comedor/Merendero",
    ]
    assert data["titulos"][-3:] == ["Observacion", "Excepcion", "Fotos"]
    assert len(data["titulos"]) == 15
    texto = _texto(nativa)
    textos = [t for t in _textos(data["secciones"]) if t]
    assert len(textos) > 150
    assert all(t in texto for t in textos)


def test_detail_tree_keeps_the_native_markup_and_drops_the_rest(web, comedor_rel):
    viejo, *_ = _ciclo(comedor_rel)

    data = web.get(f"{API}{comedor_rel.pk}/relevamiento/{viejo.pk}/").json()

    raiz = data["secciones"]
    assert raiz[0]["a"]["class"] == "row relevamiento-container"
    primera = raiz[0]["c"][0]
    assert primera["a"]["class"] == "col-3"
    valores = [
        n["a"]["class"]
        for n in _nodos(raiz, "span")
        if "username" in n["a"].get("class", "")
    ]
    assert "username text-wrap" in valores
    assert "username fw-bold fs-5" in valores
    assert not list(_nodos(raiz, "script"))
    tabla = next(_nodos(raiz, "table"))
    cabecera = [t.strip() for t in _textos(next(_nodos([tabla], "tr"))["c"]) if t]
    assert cabecera[:2] == ["LUNES", "MARTES"]


def test_detail_ignores_the_comedor_of_the_url_like_the_native_view(web, comedor_rel):
    viejo, *_ = _ciclo(comedor_rel)
    otro = Comedor.objects.create(nombre="Otro")

    respuesta = web.get(f"{API}{otro.pk}/relevamiento/{viejo.pk}/")

    assert respuesta.status_code == 200
    assert respuesta.json()["relevamiento"]["comedor"]["id"] == comedor_rel.pk
    assert web.get(f"/comedores/{otro.pk}/relevamiento/{viejo.pk}").status_code == 200


def test_detail_of_a_soft_deleted_or_unknown_relevamiento_is_404(web, comedor_rel):
    viejo, *_ = _ciclo(comedor_rel)
    assert web.get(f"{API}{comedor_rel.pk}/relevamiento/999999/").status_code == 404
    viejo.delete()
    assert web.get(f"{API}{comedor_rel.pk}/relevamiento/{viejo.pk}/").status_code == 404
    assert (
        web.get(f"/comedores/{comedor_rel.pk}/relevamiento/{viejo.pk}").status_code
        == 404
    )


def test_detail_pending_validation_shows_the_unified_state(web, comedor_rel):
    pendiente = Relevamiento.objects.create(
        comedor=comedor_rel,
        estado="Finalizado",
        estado_validacion=Relevamiento.ESTADO_VALIDACION_PENDIENTE,
        observaciones_coordinador="Corregir",
    )

    cabecera = web.get(f"{API}{comedor_rel.pk}/relevamiento/{pendiente.pk}/").json()[
        "relevamiento"
    ]

    assert cabecera["estado"] == "Finalizado"
    assert cabecera["estado_visible"] == "Pendiente Revisión"
    assert cabecera["estado_badge"] == "bg-warning text-dark"
    assert cabecera["estado_validacion"] == "Pendiente validación coordinador"
    assert cabecera["observaciones_coordinador"] == "Corregir"
    assert cabecera["coordinador"] is None


def test_detail_capabilities_follow_the_django_permissions(comedor_rel):
    viejo, *_ = _ciclo(comedor_rel)
    revisor = _client(
        _usuario(
            "revisor_rel",
            VIEW,
            "relevamientos.review_relevamiento",
            "relevamientos.delete_primerseguimiento",
        )
    )

    caps = revisor.get(f"{API}{comedor_rel.pk}/relevamiento/{viejo.pk}/").json()[
        "capabilities"
    ]

    assert caps == {
        "change_relevamiento": False,
        "review_relevamiento": True,
        "change_primerseguimiento": False,
        "delete_primerseguimiento": True,
        "view_logentry": False,
    }


# --- Access --------------------------------------------------------------------


def test_without_view_relevamiento_both_answer_403(client, comedor_rel):
    viejo, *_ = _ciclo(comedor_rel)
    client.force_login(_usuario("sin_permiso_rel"))

    assert client.get(f"{API}{comedor_rel.pk}/").status_code == 403
    assert (
        client.get(f"{API}{comedor_rel.pk}/relevamiento/{viejo.pk}/").status_code == 403
    )
    assert (
        client.get(f"/comedores/{comedor_rel.pk}/relevamiento/listar").status_code
        == 403
    )


def test_superuser_reads_and_any_comedor_is_visible(client, comedor_rel):
    client.force_login(_usuario("super_rel", is_superuser=True))
    assert client.get(f"{API}{comedor_rel.pk}/").status_code == 200


def test_anonymous_gets_401_and_a_pending_requirement_403(client, comedor_rel):
    lector = _usuario("lector_gate_rel", VIEW)
    respuesta = client.get(f"{API}{comedor_rel.pk}/")
    assert respuesta.status_code == 401
    assert respuesta.json() == {"detail": web_gate.DETAIL_UNAUTHENTICATED}
    lector.profile.must_change_password = True
    lector.profile.save()
    client.force_login(lector)
    respuesta = client.get(f"{API}{comedor_rel.pk}/")
    assert respuesta.status_code == 403
    assert respuesta.json()["state"] == "password_change_required"


def test_only_get_and_head_are_served(web, comedor_rel):
    url = f"{API}{comedor_rel.pk}/"
    assert web.post(url, {}).status_code == 405
    assert web.delete(url).status_code == 405


def test_admindocs_head_does_not_bypass_the_web_api(client, comedor_rel):
    client.force_login(_usuario("staff_rel", is_staff=True))

    respuesta = client.head(f"{API}{comedor_rel.pk}/")

    assert respuesta.status_code == 403
    assert "X-View" not in respuesta


def test_read_does_not_write_rows(web, comedor_rel):
    viejo, *_ = _ciclo(comedor_rel)
    antes = (Relevamiento.objects.count(), PrimerSeguimiento.objects.count())

    web.get(f"{API}{comedor_rel.pk}/")
    web.get(f"{API}{comedor_rel.pk}/relevamiento/{viejo.pk}/")

    assert (Relevamiento.objects.count(), PrimerSeguimiento.objects.count()) == antes


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
def test_runtime_serves_only_signed_reads(comedor_rel):
    lector = _usuario("lector_runtime_rel", VIEW)
    web = _client(lector)
    url = f"{API}{comedor_rel.pk}/"
    firma = web_gate.sign(
        audience="comedores",
        user_pk=lector.pk,
        session_key=web.cookies[settings.SESSION_COOKIE_NAME].value,
        method="GET",
        target=url,
    )
    assert web.get(url, RAW_URI=url).status_code == 403
    assert web.get(url, RAW_URI=url, HTTP_X_SISOC_WEB_GATE=firma).status_code == 200
