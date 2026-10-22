"""PDF oficial de Gestionar en SISOC (#2630, feedback de QA del 8 y 13/10).

QA pidió que el PDF que descarga SISOC sea el mismo que el de la app. La app
arma cada formulario como réplica del PDF oficial (capa fija del papel y datos
en posiciones medidas) y lo imprime desde el navegador. Al enviar un
relevamiento o un seguimiento sube ese documento como HTML autocontenido:
fuentes, capa fija e imágenes van en ``data:``.

SISOC guarda el HTML (``PdfOficialGestionar``) y lo convierte a PDF con
weasyprint la primera vez que se descarga; el resultado queda cacheado hasta
que la app suba otra versión. El documento viene del cliente, así que:

- nunca se sirve como HTML (solo el PDF que sale de él);
- weasyprint solo resuelve ``data:`` y archivos propios de ``STATIC_URL`` y
  ``MEDIA_URL`` (``RecursosLocalesURLFetcher``): nada de red (SSRF);
- se limita el tamaño y se exige un documento HTML en UTF-8.
"""

from django.db import transaction

from relevamientos.models import PdfOficialGestionar
from relevamientos.pdf_service import RecursosLocalesURLFetcher

# Una réplica de 12 páginas con sus fuentes y la capa fija en ``data:`` ronda
# 1 MB; las fotos pueden sumar varias. El tope deja margen sin abrir la puerta
# a documentos arbitrarios.
MAX_HTML_BYTES = 20 * 1024 * 1024
_MB = 1024 * 1024


class DocumentoInvalido(ValueError):
    """El archivo subido no es un documento que SISOC acepte convertir."""


def leer_html(archivo):
    """Texto del documento subido, o ``DocumentoInvalido`` con el motivo."""
    if archivo is None:
        raise DocumentoInvalido("Falta el documento HTML ('html').")
    if archivo.size > MAX_HTML_BYTES:
        maximo = max(1, round(MAX_HTML_BYTES / _MB))
        raise DocumentoInvalido(
            f"El documento supera el máximo permitido ({maximo} MB)."
        )
    try:
        html = archivo.read().decode("utf-8")
    except UnicodeDecodeError as error:
        raise DocumentoInvalido(
            "El documento debe estar codificado en UTF-8."
        ) from error
    if not html.lstrip().lower().startswith("<!doctype html"):
        raise DocumentoInvalido(
            "El archivo no es un documento HTML (falta <!doctype html>)."
        )
    return html


def guardar(*, html, version_app="", usuario=None, relevamiento=None, seguimiento=None):
    """Guarda (o reemplaza) el documento de un relevamiento o un seguimiento.

    Reemplazar descarta el PDF cacheado: la próxima descarga lo regenera.
    """
    with transaction.atomic():
        oficial, _ = PdfOficialGestionar.objects.update_or_create(
            relevamiento=relevamiento,
            seguimiento=seguimiento,
            defaults={
                "html": html,
                "pdf": None,
                "version_app": str(version_app or "")[:20],
                "usuario": usuario,
            },
        )
    return oficial


class PdfOficialURLFetcher(RecursosLocalesURLFetcher):
    """Como el fetcher del PDF de SISOC, más los ``data:`` del documento."""

    def fetch(self, url, headers=None):
        if url.startswith("data:"):
            from weasyprint.urls import (  # pylint: disable=import-outside-toplevel
                URLFetcher,
            )

            return URLFetcher().fetch(url)
        return super().fetch(url, headers)


def _renderizar(html, base_url):
    from weasyprint import HTML  # pylint: disable=import-outside-toplevel

    return HTML(
        string=html, base_url=base_url, url_fetcher=PdfOficialURLFetcher(base_url)
    ).write_pdf()


def pdf_de(oficial, base_url):
    """PDF del documento; se genera una vez y queda guardado.

    Si la app subió otra versión mientras se generaba, el resultado no se
    guarda (``fecha_actualizacion`` ya no coincide) y se regenera la próxima vez.
    """
    if oficial.pdf:
        return bytes(oficial.pdf)
    pdf = _renderizar(oficial.html, base_url)
    PdfOficialGestionar.objects.filter(
        pk=oficial.pk, fecha_actualizacion=oficial.fecha_actualizacion
    ).update(pdf=pdf)
    return pdf


def documento_de(**registro):
    """Metadatos del documento de un registro (sin el HTML ni el PDF), o ``None``."""
    return PdfOficialGestionar.objects.filter(**registro).defer("html", "pdf").first()
