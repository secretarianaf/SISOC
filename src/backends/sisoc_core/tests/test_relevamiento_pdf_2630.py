"""#2630 punto 2: el PDF del relevamiento se genera en SISOC.

El botón apuntaba a ``docPDF``, la URL que devuelve GESTIONAR al dar de alta.
Con la app nueva ese archivo nunca se genera en AppSheet (la app arma su PDF
en el navegador y no lo sube), así que el link quedaba vacío o daba 404.
"""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.urls import reverse

from comedores.models import Comedor
from core.models import Provincia
from relevamientos.models import Relevamiento
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
    relevamiento = _relevamiento()

    response = client.get(_url_pdf(relevamiento))

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert response["Content-Disposition"] == (
        f'attachment; filename="relevamiento-{relevamiento.id}.pdf"'
    )
    assert response.content.startswith(b"%PDF")


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
