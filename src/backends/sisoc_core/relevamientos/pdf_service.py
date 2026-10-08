"""PDF del relevamiento generado por SISOC (#2630).

Antes el botón del detalle enlazaba ``docPDF``, la URL que GESTIONAR devuelve
al dar de alta. Con la app nueva ese PDF no se genera en AppSheet: la app arma
el suyo en el navegador y no lo sube. SISOC renderiza ahora su propio PDF con
weasyprint a partir de los mismos datos que muestra el detalle.
"""

import mimetypes
from pathlib import Path
from urllib.parse import unquote, urlsplit

from django.conf import settings
from django.contrib.staticfiles import finders


def _ruta_dentro_de(raiz, relativa):
    """Ruta absoluta de ``relativa`` dentro de ``raiz``, o ``None`` si se escapa."""
    if not raiz:
        return None
    raiz = Path(raiz).resolve()
    ruta = (raiz / relativa).resolve()
    if ruta != raiz and raiz not in ruta.parents:
        return None
    return ruta if ruta.is_file() else None


def _ruta_estatico(relativa):
    # En producción el manifest deja el nombre con hash en STATIC_ROOT; en
    # desarrollo el archivo solo está en los directorios de cada app.
    ruta = _ruta_dentro_de(settings.STATIC_ROOT, relativa)
    if ruta:
        return ruta
    encontrada = finders.find(relativa)
    return Path(encontrada) if encontrada else None


class RecursosLocalesURLFetcher:
    """Resuelve imágenes y estilos del PDF solo desde el disco de SISOC.

    Las URLs de imágenes del relevamiento llegan desde la app y GESTIONAR; si
    weasyprint las descargara, cualquier URL cargada ahí haría que el servidor
    pida recursos de la red interna (SSRF). Solo se sirven archivos de
    ``STATIC_URL`` y ``MEDIA_URL`` del propio host; el resto se rechaza y
    weasyprint lo omite del PDF.
    """

    def __init__(self, base_url):
        self._host = urlsplit(base_url).netloc

    def __call__(self, url):
        return self.fetch(url)

    def fetch(self, url, headers=None):  # pylint: disable=unused-argument
        partes = urlsplit(url)
        if partes.scheme not in ("http", "https") or partes.netloc != self._host:
            raise ValueError(f"Recurso externo no permitido en el PDF: {url}")
        ruta_url = unquote(partes.path)
        if ".." in ruta_url.split("/"):
            raise ValueError(f"Ruta no permitida en el PDF: {url}")
        ruta = None
        if ruta_url.startswith(settings.STATIC_URL):
            ruta = _ruta_estatico(ruta_url[len(settings.STATIC_URL) :])
        elif ruta_url.startswith(settings.MEDIA_URL):
            ruta = _ruta_dentro_de(
                settings.MEDIA_ROOT, ruta_url[len(settings.MEDIA_URL) :]
            )
        if ruta is None:
            raise ValueError(f"Recurso local inexistente en el PDF: {url}")

        from weasyprint.urls import URLFetcherResponse

        tipo = mimetypes.guess_type(ruta.name)[0] or "application/octet-stream"
        return URLFetcherResponse(
            url, body=ruta.read_bytes(), headers={"Content-Type": tipo}
        )


class RelevamientoPdfService:
    """Convierte el HTML imprimible del relevamiento en PDF."""

    @staticmethod
    def generar_pdf(html, base_url):
        from weasyprint import HTML

        return HTML(
            string=html,
            base_url=base_url,
            url_fetcher=RecursosLocalesURLFetcher(base_url),
        ).write_pdf()
