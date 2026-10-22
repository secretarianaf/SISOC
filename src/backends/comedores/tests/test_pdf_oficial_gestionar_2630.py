"""#2630 (feedback de QA del 8 y 13/10): el PDF de SISOC es el mismo que el de la app.

Gestionar arma el PDF como réplica del formulario oficial (capa fija + datos en
posiciones medidas) y lo imprime desde el navegador. Al enviar un relevamiento
o un seguimiento, ahora sube ese mismo documento como HTML autocontenido
(fuentes e imágenes en ``data:``). SISOC lo guarda y lo convierte a PDF con
weasyprint: la descarga del detalle es ese PDF, no el genérico de SISOC.
"""

import io

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from pypdf import PdfReader
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from comedores.models import Comedor
from core.models import Provincia
from relevamientos import pdf_oficial
from relevamientos.models import PdfOficialGestionar, PrimerSeguimiento, Relevamiento
from users.models import TerritorialComedorProvincia

pytestmark = pytest.mark.django_db

URL_RELEVAMIENTO = "/api/relevamiento/pdf-oficial"
URL_SEGUIMIENTO = "/api/relevamiento/seguimiento/pdf-oficial"
VALIDADO = Relevamiento.ESTADO_VALIDACION_VALIDADO


def _html(texto):
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<style>@page{size:595pt 842pt;margin:0}</style></head>"
        f"<body><p>{texto}</p></body></html>"
    )


def _archivo(texto="Formato oficial de Gestionar", contenido=None):
    datos = contenido if contenido is not None else _html(texto).encode("utf-8")
    return SimpleUploadedFile("documento.html", datos, content_type="text/html")


def _territorial(nombre, provincia):
    user = get_user_model().objects.create_user(
        username=f"terr_{nombre}", password="testpass123"
    )
    user.profile.es_territorial_comedor = True
    user.profile.save(update_fields=["es_territorial_comedor"])
    TerritorialComedorProvincia.objects.create(
        profile=user.profile, provincia=provincia
    )
    token, _ = Token.objects.get_or_create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return user, client


def _escenario(nombre, **relevamiento):
    provincia = Provincia.objects.create(nombre=f"Prov {nombre}")
    comedor = Comedor.objects.create(nombre=f"Comedor {nombre}", provincia=provincia)
    user, client = _territorial(nombre, provincia)
    relevamiento = Relevamiento.objects.create(
        comedor=comedor, estado="Finalizado", territorial_user=user, **relevamiento
    )
    return comedor, relevamiento, user, client


def _subir(client, url, archivo=None, **ids):
    return client.post(
        url,
        {**ids, "html": archivo or _archivo(), "version_app": "1.1.62"},
        format="multipart",
    )


def _coordinador(client):
    user = get_user_model().objects.create_user(
        username="coord_pdf_oficial", password="testpass123"
    )
    user.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="relevamientos", codename="view_relevamiento"
        )
    )
    client.force_login(user)
    return user


def _texto_pdf(contenido):
    return " ".join(p.extract_text() for p in PdfReader(io.BytesIO(contenido)).pages)


# ------------------------------------------------------------------ API


def test_la_app_sube_el_pdf_oficial_del_relevamiento():
    _, relevamiento, user, client = _escenario("sube_rel")

    response = _subir(client, URL_RELEVAMIENTO, sisoc_id=relevamiento.id)

    assert response.status_code == 200, response.data
    oficial = PdfOficialGestionar.objects.get(relevamiento=relevamiento)
    assert "Formato oficial de Gestionar" in oficial.html
    assert oficial.version_app == "1.1.62"
    assert oficial.usuario == user
    assert oficial.seguimiento is None


def test_reenviar_reemplaza_el_documento_y_descarta_el_pdf_cacheado():
    _, relevamiento, _, client = _escenario("reenvio")
    _subir(client, URL_RELEVAMIENTO, sisoc_id=relevamiento.id)
    PdfOficialGestionar.objects.filter(relevamiento=relevamiento).update(
        pdf=b"%PDF-viejo"
    )

    response = _subir(
        client,
        URL_RELEVAMIENTO,
        archivo=_archivo("Version corregida"),
        sisoc_id=relevamiento.id,
    )

    assert response.status_code == 200, response.data
    oficial = PdfOficialGestionar.objects.get(relevamiento=relevamiento)
    assert "Version corregida" in oficial.html
    assert oficial.pdf is None
    assert PdfOficialGestionar.objects.count() == 1


@pytest.mark.parametrize("url", [URL_SEGUIMIENTO, URL_RELEVAMIENTO])
def test_el_territorial_no_sube_documentos_fuera_de_su_alcance(url):
    _, relevamiento, _, _ = _escenario("ajeno")
    seguimiento = PrimerSeguimiento.objects.create(id_relevamiento=relevamiento)
    otra = Provincia.objects.create(nombre="Prov otra pdf")
    _, intruso = _territorial("intruso_pdf", otra)

    ident = seguimiento.id if url == URL_SEGUIMIENTO else relevamiento.id
    response = _subir(intruso, url, sisoc_id=ident)

    assert response.status_code == 404
    assert not PdfOficialGestionar.objects.exists()


@pytest.mark.parametrize(
    "contenido,mensaje",
    [
        (b"<p>sin doctype</p>", "documento HTML"),
        ("<!doctype html><p>ñ</p>".encode("latin-1"), "UTF-8"),
        (b"", "documento HTML"),
    ],
)
def test_rechaza_lo_que_no_es_un_documento_html(contenido, mensaje):
    _, relevamiento, _, client = _escenario(f"invalido_{len(contenido)}")

    response = _subir(
        client,
        URL_RELEVAMIENTO,
        archivo=_archivo(contenido=contenido),
        sisoc_id=relevamiento.id,
    )

    assert response.status_code == 400
    assert mensaje in str(response.data)
    assert not PdfOficialGestionar.objects.exists()


def test_rechaza_un_documento_demasiado_grande(monkeypatch):
    monkeypatch.setattr(pdf_oficial, "MAX_HTML_BYTES", 100)
    _, relevamiento, _, client = _escenario("grande")

    response = _subir(client, URL_RELEVAMIENTO, sisoc_id=relevamiento.id)

    assert response.status_code == 400
    assert "supera" in str(response.data)


def test_sin_html_o_sin_identificador_es_400():
    _, relevamiento, _, client = _escenario("faltantes")

    sin_html = client.post(
        URL_RELEVAMIENTO, {"sisoc_id": relevamiento.id}, format="multipart"
    )
    sin_id = client.post(URL_RELEVAMIENTO, {"html": _archivo()}, format="multipart")

    assert sin_html.status_code == 400
    assert sin_id.status_code == 400


def test_un_validado_recibe_el_primer_documento_pero_no_lo_reemplaza():
    # Los registros enviados antes de 1.1.62 se completan cuando el territorial
    # abre el PDF en la app (solo sale validado). Una vez cargado, no se pisa.
    _, relevamiento, _, client = _escenario("validado", estado_validacion=VALIDADO)

    primero = _subir(client, URL_RELEVAMIENTO, sisoc_id=relevamiento.id)
    segundo = _subir(
        client,
        URL_RELEVAMIENTO,
        archivo=_archivo("Otro contenido"),
        sisoc_id=relevamiento.id,
    )

    assert primero.status_code == 200, primero.data
    assert segundo.status_code == 409
    oficial = PdfOficialGestionar.objects.get(relevamiento=relevamiento)
    assert "Otro contenido" not in oficial.html


def test_el_seguimiento_se_identifica_como_en_su_patch():
    _, relevamiento, _, client = _escenario("seguimiento")
    primero = PrimerSeguimiento.objects.create(
        id_relevamiento=relevamiento, numero_orden=1
    )
    posterior = PrimerSeguimiento.objects.create(
        id_relevamiento=relevamiento,
        numero_orden=2,
        tipo=PrimerSeguimiento.TIPO_POSTERIOR,
    )

    por_relevamiento = _subir(
        client,
        URL_SEGUIMIENTO,
        archivo=_archivo("Primera"),
        id_relevamiento=relevamiento.id,
    )
    por_instancia = _subir(
        client, URL_SEGUIMIENTO, archivo=_archivo("Segunda"), sisoc_id=posterior.id
    )

    assert por_relevamiento.status_code == 200, por_relevamiento.data
    assert por_instancia.status_code == 200, por_instancia.data
    assert "Primera" in PdfOficialGestionar.objects.get(seguimiento=primero).html
    assert "Segunda" in PdfOficialGestionar.objects.get(seguimiento=posterior).html


# ------------------------------------------------------------------ conversión


def test_el_fetcher_solo_resuelve_data_y_archivos_propios():
    fetcher = pdf_oficial.PdfOficialURLFetcher("https://sisoc.test/")

    imagen = fetcher("data:text/plain;base64,aG9sYQ==")

    assert imagen.read() == b"hola"
    for url in (
        "https://maps.googleapis.com/maps/api/staticmap?key=x",
        "http://169.254.169.254/latest/meta-data/",
        "file:///etc/passwd",
        "https://sisoc.test/admin/",
    ):
        with pytest.raises(ValueError):
            fetcher(url)


def test_el_pdf_se_genera_una_vez_y_queda_cacheado(monkeypatch):
    _, relevamiento, _, client = _escenario("cache")
    _subir(
        client,
        URL_RELEVAMIENTO,
        archivo=_archivo("Cacheado 8419"),
        sisoc_id=relevamiento.id,
    )
    oficial = PdfOficialGestionar.objects.get(relevamiento=relevamiento)
    llamadas = []
    original = pdf_oficial._renderizar

    def contar(html, base_url):
        llamadas.append(base_url)
        return original(html, base_url)

    monkeypatch.setattr(pdf_oficial, "_renderizar", contar)

    primero = pdf_oficial.pdf_de(oficial, "https://sisoc.test/")
    segundo = pdf_oficial.pdf_de(
        PdfOficialGestionar.objects.get(pk=oficial.pk), "https://sisoc.test/"
    )

    assert primero == segundo
    assert primero.startswith(b"%PDF")
    assert "Cacheado 8419" in _texto_pdf(primero)
    assert len(llamadas) == 1


# ------------------------------------------------------------------ backoffice


def test_el_detalle_del_relevamiento_descarga_el_pdf_de_gestionar(client):
    comedor, relevamiento, _, api = _escenario("descarga_rel")
    _subir(
        api,
        URL_RELEVAMIENTO,
        archivo=_archivo("RELEVAMIENTOS COMEDORES 2026"),
        sisoc_id=relevamiento.id,
    )
    _coordinador(client)
    kwargs = {"comedor_pk": comedor.id, "pk": relevamiento.id}

    detalle = client.get(reverse("relevamiento_detalle", kwargs=kwargs))
    pdf = client.get(reverse("relevamiento_pdf", kwargs=kwargs))

    assert "Formato oficial de Gestionar" in detalle.content.decode()
    assert pdf.status_code == 200
    assert pdf["Content-Type"] == "application/pdf"
    assert (
        f'filename="relevamiento-{relevamiento.id}.pdf"' in pdf["Content-Disposition"]
    )
    assert "RELEVAMIENTOS COMEDORES 2026" in _texto_pdf(pdf.content)


def test_sin_documento_de_gestionar_el_relevamiento_sigue_con_el_pdf_de_sisoc(client):
    comedor, relevamiento, _, _ = _escenario("sin_doc_rel")
    _coordinador(client)
    kwargs = {"comedor_pk": comedor.id, "pk": relevamiento.id}

    detalle = client.get(reverse("relevamiento_detalle", kwargs=kwargs))
    pdf = client.get(reverse("relevamiento_pdf", kwargs=kwargs))

    assert "Formato oficial de Gestionar" not in detalle.content.decode()
    assert pdf.status_code == 200
    assert "Acompañamiento Territorial" in _texto_pdf(pdf.content)


def test_el_seguimiento_tiene_su_pdf_en_el_detalle(client):
    comedor, relevamiento, _, api = _escenario("descarga_seg")
    seguimiento = PrimerSeguimiento.objects.create(id_relevamiento=relevamiento)
    _subir(
        api,
        URL_SEGUIMIENTO,
        archivo=_archivo("PRIMER VISITA DE SEGUIMIENTO"),
        sisoc_id=seguimiento.id,
    )
    _coordinador(client)
    kwargs = {
        "comedor_pk": comedor.id,
        "relevamiento_pk": relevamiento.id,
        "pk": seguimiento.id,
    }

    detalle = client.get(reverse("seguimiento_detalle", kwargs=kwargs))
    pdf = client.get(reverse("seguimiento_pdf", kwargs=kwargs))

    assert reverse("seguimiento_pdf", kwargs=kwargs) in detalle.content.decode()
    assert pdf.status_code == 200
    assert f'filename="seguimiento-{seguimiento.id}.pdf"' in pdf["Content-Disposition"]
    assert "PRIMER VISITA DE SEGUIMIENTO" in _texto_pdf(pdf.content)


def test_un_seguimiento_sin_documento_explica_de_donde_sale_el_pdf(client):
    comedor, relevamiento, _, _ = _escenario("sin_doc_seg")
    seguimiento = PrimerSeguimiento.objects.create(id_relevamiento=relevamiento)
    _coordinador(client)
    kwargs = {
        "comedor_pk": comedor.id,
        "relevamiento_pk": relevamiento.id,
        "pk": seguimiento.id,
    }

    detalle = client.get(reverse("seguimiento_detalle", kwargs=kwargs))
    pdf = client.get(reverse("seguimiento_pdf", kwargs=kwargs))

    assert reverse("seguimiento_pdf", kwargs=kwargs) not in detalle.content.decode()
    assert "cuando el territorial lo envía desde Gestionar" in detalle.content.decode()
    assert pdf.status_code == 404
