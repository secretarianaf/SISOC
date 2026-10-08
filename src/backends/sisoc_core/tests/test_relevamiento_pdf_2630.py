"""#2630 punto 2: el PDF del relevamiento se genera en SISOC.

El botón apuntaba a ``docPDF``, la URL que devuelve GESTIONAR al dar de alta.
Con la app nueva ese archivo nunca se genera en AppSheet (la app arma su PDF
en el navegador y no lo sube), así que el link quedaba vacío o daba 404.
"""

from io import BytesIO

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.urls import reverse
from PIL import Image
from pypdf import PdfReader

from comedores.models import Comedor
from core.models import Provincia
from relevamientos.models import Excepcion, Relevamiento
from relevamientos.pdf_service import RecursosLocalesURLFetcher, RelevamientoPdfService

pytestmark = pytest.mark.django_db

DOC_PDF_APPSHEET = (
    "https://www.appsheet.com/template/gettablefileurl?appName=GesCom"
    "&tableName=RelevamientoComedores&fileName=Relevamientos%20PDF%2F8868.pdf"
)


def _login(client, con_permiso=True):
    user = get_user_model().objects.create_user(
        username="pdf_2630", password="testpass123"
    )
    if con_permiso:
        user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="relevamientos", codename="view_relevamiento"
            )
        )
    client.force_login(user)
    return user


def _relevamiento(**extra):
    provincia = Provincia.objects.create(nombre="Prov PDF 2630")
    comedor = Comedor.objects.create(nombre="Comedor PDF 2630", provincia=provincia)
    datos = {"estado": "Finalizado", "docPDF": DOC_PDF_APPSHEET}
    datos.update(extra)
    return Relevamiento.objects.create(comedor=comedor, **datos)


def _url_pdf(relevamiento):
    return reverse(
        "relevamiento_pdf",
        kwargs={"comedor_pk": relevamiento.comedor_id, "pk": relevamiento.id},
    )


def test_boton_del_detalle_apunta_al_pdf_de_sisoc(client):
    _login(client)
    relevamiento = _relevamiento()

    response = client.get(
        reverse(
            "relevamiento_detalle",
            kwargs={"comedor_pk": relevamiento.comedor_id, "pk": relevamiento.id},
        )
    )

    html = response.content.decode()
    assert f'href="{_url_pdf(relevamiento)}"' in html
    assert "appsheet.com" not in html


def test_descarga_devuelve_un_pdf_adjunto(client):
    _login(client)
    relevamiento = _relevamiento(
        estado_validacion=Relevamiento.ESTADO_VALIDACION_PENDIENTE,
        observacion="Observación del territorial para comprobar el documento",
    )

    response = client.get(_url_pdf(relevamiento))

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert response["Content-Disposition"] == (
        f'attachment; filename="relevamiento-{relevamiento.id}.pdf"'
    )
    assert response.content.startswith(b"%PDF")
    lector = PdfReader(BytesIO(response.content))
    texto = " ".join(" ".join(pagina.extract_text() for pagina in lector.pages).split())
    for esperado in (
        "Comedor PDF 2630",
        "Pendiente de validación",
        "Domicilio del Comedor/Merendero",
        "Observación del territorial para comprobar el documento",
    ):
        assert esperado in texto


def test_pdf_con_observacion_larga_conserva_todo_el_texto(client):
    _login(client)
    marcas = [f"REGISTRO{i:03d}" for i in range(100)]
    observacion = " ".join(
        f"{marca} El territorial informa sobre el funcionamiento del comedor."
        for marca in marcas
    )
    relevamiento = _relevamiento(observacion=observacion)

    response = client.get(_url_pdf(relevamiento))

    assert response.status_code == 200
    lector = PdfReader(BytesIO(response.content))
    texto = " ".join(pagina.extract_text() for pagina in lector.pages)
    assert len(lector.pages) > 1
    for marca in marcas:
        assert texto.count(marca) == 1


@pytest.mark.parametrize("cantidad_fotos", [2, 12])
def test_pdf_incluye_firma_y_fotos_locales(client, settings, cantidad_fotos):
    _login(client)
    settings.MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (40, 20), "black").save(settings.MEDIA_ROOT / "firma.png")
    urls = [f"{settings.MEDIA_URL}firma.png"]
    for indice in range(cantidad_fotos):
        nombre = f"foto-{indice}.png"
        color = (indice * 19, 100, 180)
        Image.new("RGB", (800, 600), color).save(settings.MEDIA_ROOT / nombre)
        urls.append(f"{settings.MEDIA_URL}{nombre}")
    excepcion = Excepcion.objects.create(firma=urls[0])
    relevamiento = _relevamiento(excepcion=excepcion, imagenes=urls[1:])

    response = client.get(_url_pdf(relevamiento))

    assert response.status_code == 200
    lector = PdfReader(BytesIO(response.content))
    # WeasyPrint puede compartir el diccionario de recursos entre páginas.
    # Contar imágenes únicas evita contar varias veces el mismo recurso.
    imagenes = {imagen.data for pagina in lector.pages for imagen in pagina.images}
    assert len(imagenes) == cantidad_fotos + 1


def test_el_pdf_lleva_las_secciones_del_detalle(client, mocker):
    _login(client)
    relevamiento = _relevamiento(
        estado_validacion=Relevamiento.ESTADO_VALIDACION_PENDIENTE,
        observacion="Observación del territorial",
    )
    generar = mocker.patch(
        "relevamientos.views.web_views.RelevamientoPdfService.generar_pdf",
        return_value=b"%PDF-1.7 stub",
    )

    response = client.get(_url_pdf(relevamiento))

    assert response.status_code == 200
    html = generar.call_args.args[0]
    assert "Comedor PDF 2630" in html
    assert f"Relevamiento N.º {relevamiento.id}" in html
    assert "Pendiente de validación" in html
    assert "Domicilio del Comedor/Merendero" in html
    assert "Observación del territorial" in html
    # Ni formularios ni modales del detalle (los botones de colapsar de cada
    # sección se ocultan con el CSS del PDF).
    assert "<form" not in html
    assert "modalRevisionCoordinador" not in html
    assert ".card-tools, button" in html


def test_descarga_sin_permiso_no_entrega_el_pdf(client):
    _login(client, con_permiso=False)
    relevamiento = _relevamiento()

    response = client.get(_url_pdf(relevamiento))

    assert response.status_code != 200 or not response.content.startswith(b"%PDF")


def test_fetcher_sirve_estaticos_desde_disco():
    fetcher = RecursosLocalesURLFetcher(base_url="http://testserver/")

    respuesta = fetcher.fetch("http://testserver/static/custom/img/check_ok.svg")

    assert b"<svg" in respuesta.read()


@pytest.mark.parametrize(
    "url",
    [
        "https://otro-host.example/static/custom/img/check_ok.svg",
        "http://169.254.169.254/latest/meta-data/",
        "file:///etc/passwd",
        "http://testserver/static/../../etc/passwd",
        "http://testserver/admin/",
    ],
)
def test_fetcher_rechaza_recursos_que_no_son_locales(url):
    fetcher = RecursosLocalesURLFetcher(base_url="http://testserver/")

    with pytest.raises(ValueError):
        fetcher.fetch(url)


def test_generar_pdf_devuelve_bytes_de_pdf():
    pdf = RelevamientoPdfService.generar_pdf(
        "<html><body><h1>Relevamiento</h1></body></html>",
        base_url="http://testserver/",
    )

    assert pdf.startswith(b"%PDF")
