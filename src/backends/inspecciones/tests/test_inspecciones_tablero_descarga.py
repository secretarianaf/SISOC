"""Descarga de actas completas (PDF o ZIP) desde Tablero → Últimas actas (#2718)."""

import io
import zipfile

import pytest
from django.core.files.base import ContentFile
from django.urls import reverse

from inspecciones.services import descarga_actas
from inspecciones.services.formato import hoy
from tests.test_inspecciones_tablero import crear_acta

pytestmark = pytest.mark.django_db

URL = "/inspecciones/tablero/descargar-actas/"
PDF = b"%PDF-1.4 contenido"


def con_pdf(acta, contenido=PDF):
    acta.pdf.save("acta.pdf", ContentFile(contenido), save=True)
    return acta


def test_ruta_con_nombre():
    assert reverse("inspecciones_tablero_descargar_actas") == URL


def test_exige_permiso(client, inspector_a):
    assert client.get(URL).status_code == 302
    client.force_login(inspector_a)
    assert client.get(URL).status_code == 403


def test_una_acta_se_descarga_como_pdf(client, coordinacion, inspector_a, escuela):
    acta = con_pdf(crear_acta(inspector_a, escuela))
    client.force_login(coordinacion)

    response = client.get(URL)

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert f"{acta.numero}.pdf" in response["Content-Disposition"]
    assert b"".join(response.streaming_content) == PDF


def test_varias_actas_se_descargan_en_zip(client, coordinacion, inspector_a, escuela):
    a = con_pdf(crear_acta(inspector_a, escuela), PDF + b"a")
    b = con_pdf(crear_acta(inspector_a, escuela), PDF + b"b")
    client.force_login(coordinacion)

    response = client.get(URL)

    assert response["Content-Type"] == "application/zip"
    assert f"inspecciones-actas-{hoy().isoformat()}.zip" in (
        response["Content-Disposition"]
    )
    with zipfile.ZipFile(io.BytesIO(b"".join(response.streaming_content))) as zf:
        assert sorted(zf.namelist()) == sorted([f"{a.numero}.pdf", f"{b.numero}.pdf"])
        assert zf.read(f"{a.numero}.pdf") == PDF + b"a"


def test_respeta_filtros_y_excluye_lo_que_el_csv_excluye(
    client, coordinacion, inspector_a, inspector_b, escuela
):
    a = con_pdf(crear_acta(inspector_a, escuela, turno="tarde"))
    con_pdf(crear_acta(inspector_b, escuela, turno="tarde"))
    con_pdf(crear_acta(inspector_a, escuela, turno="manana"))
    con_pdf(crear_acta(inspector_a, escuela, es_prueba=True))
    client.force_login(coordinacion)

    response = client.get(URL, {"inspector": inspector_a.pk, "turno": "tarde"})

    assert response["Content-Type"] == "application/pdf"
    assert f"{a.numero}.pdf" in response["Content-Disposition"]


def test_actas_sin_pdf_se_listan_en_el_zip(client, coordinacion, inspector_a, escuela):
    con_pdf(crear_acta(inspector_a, escuela))
    sin = crear_acta(inspector_a, escuela)
    client.force_login(coordinacion)

    response = client.get(URL)

    with zipfile.ZipFile(io.BytesIO(b"".join(response.streaming_content))) as zf:
        assert len(zf.namelist()) == 2
        listado = zf.read(descarga_actas.NOMBRE_FALTANTES).decode("utf-8")
    assert sin.numero in listado


def test_sin_actas_informa_y_vuelve_al_tablero(client, coordinacion):
    client.force_login(coordinacion)

    response = client.get(URL, {"turno": "tarde"}, follow=True)

    assert response.redirect_chain[0][0].startswith("/inspecciones/tablero/")
    assert "turno=tarde" in response.redirect_chain[0][0]
    textos = [str(m) for m in response.context["messages"]]
    assert textos == [descarga_actas.MENSAJE_SIN_ACTAS]


def test_solo_actas_sin_pdf_informa(client, coordinacion, inspector_a, escuela):
    crear_acta(inspector_a, escuela)
    client.force_login(coordinacion)

    response = client.get(URL, follow=True)

    textos = [str(m) for m in response.context["messages"]]
    assert textos == [descarga_actas.MENSAJE_SIN_PDF]


def test_supera_el_tope_informa(
    client, coordinacion, inspector_a, escuela, monkeypatch
):
    monkeypatch.setattr(descarga_actas, "MAX_ACTAS", 1)
    con_pdf(crear_acta(inspector_a, escuela))
    con_pdf(crear_acta(inspector_a, escuela))
    client.force_login(coordinacion)

    response = client.get(URL, follow=True)

    textos = [str(m) for m in response.context["messages"]]
    assert textos == [descarga_actas.mensaje_tope(1)]


def test_el_boton_esta_antes_del_csv(client, coordinacion):
    client.force_login(coordinacion)

    html = client.get("/inspecciones/tablero/").content.decode()

    descargar = html.index("Descargar actas completas")
    assert descargar < html.index("Exportar CSV (filtros aplicados)")
    assert "data-tablero-descargar" in html


def test_supera_el_tope_de_bytes_informa(
    client, coordinacion, inspector_a, escuela, monkeypatch
):
    monkeypatch.setattr(descarga_actas, "MAX_BYTES", len(PDF))
    con_pdf(crear_acta(inspector_a, escuela))
    con_pdf(crear_acta(inspector_a, escuela))
    client.force_login(coordinacion)

    response = client.get(URL, follow=True)

    textos = [str(m) for m in response.context["messages"]]
    assert textos == [descarga_actas.mensaje_tope_bytes(len(PDF))]


def test_pdf_faltante_en_disco_se_lista_en_el_zip(
    client, coordinacion, inspector_a, escuela
):
    con_pdf(crear_acta(inspector_a, escuela))
    perdida = con_pdf(crear_acta(inspector_a, escuela))
    perdida.pdf.storage.delete(perdida.pdf.name)
    client.force_login(coordinacion)

    response = client.get(URL)

    assert response["Content-Type"] == "application/zip"
    with zipfile.ZipFile(io.BytesIO(b"".join(response.streaming_content))) as zf:
        assert f"{perdida.numero}.pdf" not in zf.namelist()
        listado = zf.read(descarga_actas.NOMBRE_FALTANTES).decode("utf-8")
    assert perdida.numero in listado
