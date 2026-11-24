"""Web API (G1 v1) of the seguimiento, PNUD and acta detail pages (R03.01, R02.01).

The tests compare the projected values with the native HTML pages and pin
today's access: ``relevamientos.view_relevamiento`` only, no object scope other
than the URL's own comedor and relevamiento, and the native POSTs left alone.
"""

from datetime import datetime, timezone as dt_timezone
from html.parser import HTMLParser

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client

from comedores.models import Comedor
from core import web_gate
from relevamientos.models import (
    ActaComplementaria,
    CierreSeguimiento,
    ItemRecetaSeguimiento,
    MenuSeguimiento,
    PrestacionActaComplementaria,
    PrestacionSeguimiento,
    PrimerSeguimiento,
    Relevamiento,
    SeguimientoPnud,
)

VIEW = "relevamientos.view_relevamiento"
API = "/api/web/comedores/relevamientos/"
FECHA = datetime(2026, 3, 4, 15, 7, tzinfo=dt_timezone.utc)
FIRMA = "https://sisoc.example/media/firmas/1/entrevistado.png"

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
    return _client(_usuario("lector_seg", VIEW))


class _Texto(HTMLParser):
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


def _texto(respuesta):
    parser = _Texto()
    parser.feed(respuesta.content.decode())
    return " ".join("".join(parser.partes).split())


def _ciclo():
    comedor = Comedor.objects.create(nombre="Comedor <Seg>")
    relevamiento = Relevamiento.objects.create(
        comedor=comedor, estado="Finalizado", fecha_visita=FECHA
    )
    menu = MenuSeguimiento.objects.create(id_menu="m1", tipo_prestacion="Almuerzo")
    ItemRecetaSeguimiento.objects.create(
        menu=menu, id_item_receta="i1", ingrediente="Arroz", cantidad_medida="2"
    )
    primero = PrimerSeguimiento.objects.create(
        id_relevamiento=relevamiento,
        estado=PrimerSeguimiento.ESTADO_COMPLETO,
        fecha_hora=FECHA,
        gestionar_id="G-9",
        tecnico="Téc <1>",
        origen="app",
        menu=menu,
        cierre=CierreSeguimiento.objects.create(
            comentarios_finales="listo", firma_entrevistado=FIRMA
        ),
        motivo_diferencia_aprobado_declarado="Línea 1\nLínea 2",
        observaciones_coordinador="Corregir\nfoto",
    )
    PrestacionSeguimiento.objects.create(
        seguimiento=primero,
        id_prestacion_seg="p1",
        dias_prestacion="Lunes",
        tipo_prestacion="Almuerzo",
        ap_total=5,
    )
    posterior = PrimerSeguimiento.objects.create(
        id_relevamiento=relevamiento,
        tipo=PrimerSeguimiento.TIPO_POSTERIOR,
        numero_orden=2,
    )
    return comedor, relevamiento, primero, posterior


def _url(comedor, relevamiento, seguimiento=None):
    base = f"{API}{comedor.pk}/relevamiento/{relevamiento.pk}/seguimientos/"
    return f"{base}{seguimiento.pk}/" if seguimiento else f"{base}primero/"


def _nativa(comedor, relevamiento, seguimiento):
    return (
        f"/comedores/{comedor.pk}/relevamiento/{relevamiento.pk}/seguimiento/"
        f"{seguimiento.pk}/"
    )


# --- Seguimiento ---------------------------------------------------------------


def test_seguimiento_projects_the_native_summary_cycle_and_tables(web):
    comedor, relevamiento, primero, posterior = _ciclo()
    nativa = _texto(web.get(_nativa(comedor, relevamiento, primero)))

    respuesta = web.get(_url(comedor, relevamiento, primero))

    assert respuesta.status_code == 200
    assert respuesta["Cache-Control"] == "private, no-store"
    data = respuesta.json()
    seg = data["seguimiento"]
    assert (seg["id"], seg["tipo_display"], seg["numero_orden"]) == (
        primero.pk,
        "Primer seguimiento",
        1,
    )
    assert (seg["gestionar_id"], seg["tecnico"], seg["referente"]) == (
        "G-9",
        "Téc <1>",
        "Sin asignar",
    )
    assert seg["estado"] == "Finalizado" and seg["estado_badge"] == "bg-success"
    assert seg["origen"] == "app" and seg["sincronizado_gestionar"] is False
    assert seg["motivo_diferencia_aprobado_declarado"] == "Línea 1\nLínea 2"
    assert seg["observaciones_coordinador"] == "Corregir\nfoto"
    assert data["comedor"] == {"id": comedor.pk, "nombre": "Comedor <Seg>"}
    assert data["relevamiento"]["id"] == relevamiento.pk
    assert [i["id"] for i in data["instancias"]] == [primero.pk, posterior.pk]
    assert data["instancias"][1]["detalle_url"] == (
        _nativa(comedor, relevamiento, posterior)
    )
    assert data["prestaciones"] == [["Lunes", "Almuerzo", "5", "-", "-"]]
    assert data["es_primer"] is True
    assert data["receta_items"] == [["Arroz", "-", "2"]]
    assert data["pdf"] == {"url": None, "fecha_oficial": None}
    for valor in (seg["gestionar_id"], seg["fecha_hora"], "Arroz", "Lunes"):
        assert valor in nativa
    labels = [c["label"] for b in data["bloques"] for c in b["campos"]]
    assert all(label in nativa for label in labels)


def test_seguimiento_marks_the_signature_as_an_image_node(web):
    comedor, relevamiento, primero, _ = _ciclo()

    data = web.get(_url(comedor, relevamiento, primero)).json()

    campos = {c["label"]: c for b in data["bloques"] for c in b["campos"]}
    assert campos["Comentarios finales"]["value"] == "listo"
    assert campos["Comentarios finales"]["es_imagen"] is False
    firma = campos["Firma entrevistado"]
    assert firma["es_imagen"] is True
    imagenes = []

    def buscar(nodos):
        for n in nodos:
            if not isinstance(n, str):
                if n["t"] == "img":
                    imagenes.append(n["a"]["src"])
                buscar(n["c"])

    buscar(firma["value"])
    assert any(FIRMA.rsplit("/", 1)[-1] in src for src in imagenes)


def test_seguimiento_alias_resolves_the_first_instance_or_404(web):
    comedor, relevamiento, primero, _ = _ciclo()
    vacio = Relevamiento.objects.create(comedor=comedor)

    assert (
        web.get(_url(comedor, relevamiento)).json()["seguimiento"]["id"] == primero.pk
    )
    assert web.get(_url(comedor, vacio)).status_code == 404
    assert (
        web.get(
            f"/comedores/{comedor.pk}/relevamiento/{vacio.pk}/primer-seguimiento/"
        ).status_code
        == 404
    )


def test_seguimiento_of_another_relevamiento_or_comedor_is_404(web):
    comedor, relevamiento, primero, _ = _ciclo()
    otro_rel = Relevamiento.objects.create(comedor=comedor)
    otro_comedor = Comedor.objects.create(nombre="Otro")

    assert web.get(_url(comedor, otro_rel, primero)).status_code == 404
    assert (
        web.get(
            f"{API}{otro_comedor.pk}/relevamiento/{relevamiento.pk}/seguimientos/{primero.pk}/"
        ).status_code
        == 404
    )
    assert (
        web.get(
            f"{API}{comedor.pk}/relevamiento/{relevamiento.pk}/seguimientos/9999/"
        ).status_code
        == 404
    )


def test_seguimiento_without_blocks_is_empty_and_non_primer_has_two_ap_columns(web):
    comedor, relevamiento, _, posterior = _ciclo()
    PrestacionSeguimiento.objects.create(
        seguimiento=posterior, dias_prestacion="Martes", ap_presencial=1, ap_vianda=2
    )

    data = web.get(_url(comedor, relevamiento, posterior)).json()

    assert data["bloques"] == [] and data["es_primer"] is False
    assert data["prestaciones"] == [["Martes", "-", "1", "2", "-", "-"]]
    assert data["seguimiento"]["sincronizado_gestionar"] is False


def test_seguimiento_capabilities_follow_the_django_permissions():
    comedor, relevamiento, primero, _ = _ciclo()
    revisor = _client(
        _usuario("revisor_seg", VIEW, "relevamientos.review_relevamiento")
    )

    caps = revisor.get(_url(comedor, relevamiento, primero)).json()["capabilities"]

    assert caps == {
        "change_primerseguimiento": False,
        "review_relevamiento": True,
        "delete_primerseguimiento": False,
    }


# --- PNUD ----------------------------------------------------------------------


def _pnud(comedor, formulario="siph", datos=None):
    return SeguimientoPnud.objects.create(
        comedor=comedor,
        formulario=formulario,
        fecha_hora=FECHA,
        datos=datos or {"funcionamiento": "Cerrado\nhoy"},
    )


def test_pnud_projects_the_native_sections_and_the_siph_pdf(web):
    comedor = Comedor.objects.create(nombre="Comedor PNUD")
    siph = _pnud(comedor)
    iia = _pnud(comedor, "iia")
    nativa = _texto(web.get(f"/comedores/{comedor.pk}/seguimiento-pnud/{siph.pk}"))

    data = web.get(f"{API}{comedor.pk}/pnud/{siph.pk}/").json()
    otro = web.get(f"{API}{comedor.pk}/pnud/{iia.pk}/").json()

    assert data["seguimiento"]["formulario_display"].startswith("FORM-SIPH")
    assert data["seguimiento"]["tecnico"] == "Sin técnico"
    assert data["seguimiento"]["fecha_hora"] in nativa
    assert data["pdf_url"] == f"/comedores/{comedor.pk}/seguimiento-pnud/{siph.pk}/pdf"
    assert otro["pdf_url"] is None
    assert data["secciones"]
    for seccion in data["secciones"]:
        assert seccion["titulo"] in nativa
        for fila in seccion["filas"]:
            assert fila["etiqueta"] in nativa
    assert data["capabilities"] == {"review_relevamiento": False}
    assert set(data["encabezado_formulario"]) == {"linea", "titulo"}


def test_pnud_of_another_comedor_is_404(web):
    comedor = Comedor.objects.create(nombre="A")
    otro = Comedor.objects.create(nombre="B")
    siph = _pnud(comedor)

    assert web.get(f"{API}{otro.pk}/pnud/{siph.pk}/").status_code == 404
    assert web.get(f"{API}{comedor.pk}/pnud/9999/").status_code == 404


def test_pnud_without_answers_has_no_sections(web):
    comedor = Comedor.objects.create(nombre="Vacío")
    pnud = SeguimientoPnud.objects.create(comedor=comedor, formulario="iia", datos={})

    data = web.get(f"{API}{comedor.pk}/pnud/{pnud.pk}/").json()

    assert data["secciones"] == []
    assert data["seguimiento"]["fecha_hora"] == "Sin fecha"


# --- Acta ----------------------------------------------------------------------


def _acta(comedor, **extra):
    return ActaComplementaria.objects.create(
        comedor=comedor, fecha_hora=FECHA, observaciones="Línea\ndos", **extra
    )


def test_acta_projects_the_native_summary_and_prestaciones(web):
    comedor = Comedor.objects.create(nombre="Comedor Acta")
    acta = _acta(comedor, origen="app")
    PrestacionActaComplementaria.objects.create(
        acta=acta, dias_prestacion="Lunes", tipo_prestacion="Cena", cantidad_actual=3
    )
    nativa = _texto(web.get(f"/comedores/{comedor.pk}/acta-complementaria/{acta.pk}"))

    respuesta = web.get(f"{API}{comedor.pk}/actas/{acta.pk}/")

    assert respuesta.status_code == 200
    data = respuesta.json()
    resumen = data["acta"]
    assert resumen["comedor"] == {"id": comedor.pk, "nombre": "Comedor Acta"}
    assert resumen["tecnico"] == "Sin asignar" and resumen["origen"] == "app"
    assert resumen["observaciones"] == "Línea\ndos"
    assert resumen["estado"] == "Pendiente Revisión"
    assert resumen["fecha_hora"] in nativa and resumen["fecha_creacion"] in nativa
    assert data["prestaciones"] == [["Lunes", "Cena", "3", "-"]]
    assert set(data["capabilities"]) == {
        "change_actacomplementaria",
        "review_relevamiento",
        "delete_actacomplementaria",
    }
    assert data["urls"]["eliminar"] == (
        f"/comedores/{comedor.pk}/acta-complementaria/{acta.pk}/eliminar"
    )


def test_acta_without_prestaciones_or_content_and_other_comedor_404(web):
    comedor = Comedor.objects.create(nombre="C")
    otro = Comedor.objects.create(nombre="D")
    vacia = ActaComplementaria.objects.create(comedor=comedor)

    data = web.get(f"{API}{comedor.pk}/actas/{vacia.pk}/").json()

    assert data["prestaciones"] == [] and data["acta"]["sin_cargar"] is True
    assert data["acta"]["fecha_hora"] == "Sin fecha"
    assert web.get(f"{API}{otro.pk}/actas/{vacia.pk}/").status_code == 404
    assert web.get(f"{API}{comedor.pk}/actas/9999/").status_code == 404


# --- Access --------------------------------------------------------------------


def test_every_detail_needs_view_relevamiento_and_the_gate(client):
    comedor, relevamiento, primero, _ = _ciclo()
    pnud = _pnud(comedor)
    acta = _acta(comedor)
    urls = [
        _url(comedor, relevamiento, primero),
        f"{API}{comedor.pk}/pnud/{pnud.pk}/",
        f"{API}{comedor.pk}/actas/{acta.pk}/",
    ]
    for url in urls:
        assert client.get(url).status_code == 401
    client.force_login(_usuario("sin_permiso_seg"))
    for url in urls:
        assert client.get(url).status_code == 403
    lector = _usuario("pendiente_seg", VIEW)
    lector.profile.must_change_password = True
    lector.profile.save()
    client.force_login(lector)
    respuesta = client.get(urls[0])
    assert respuesta.status_code == 403
    assert respuesta.json()["state"] == "password_change_required"
    assert web_gate.DETAIL_UNAUTHENTICATED


def test_only_get_is_served_and_reads_write_nothing(web):
    comedor, relevamiento, primero, _ = _ciclo()
    antes = PrimerSeguimiento.objects.count()
    url = _url(comedor, relevamiento, primero)

    assert web.post(url, {}).status_code == 405
    web.get(url)

    assert PrimerSeguimiento.objects.count() == antes
