"""Router de `/v2/<modulo>/`: Django reenvia al servicio de front del modulo.

El Nginx del host no cambia: ya manda todo el trafico a Django. Aca Django
recibe `/v2/<modulo>/...` y lo reenvia al servicio que corresponde.

Reglas, todas deliberadas (ver `docs/implementaciones/frontend_v2.md`):

- **Allowlist por configuracion.** Los destinos salen de
  `settings.FRONTEND_V2_SERVICIOS`, nunca del request: si el modulo saliera de
  la URL, cualquiera podria hacer que Django consulte una URL arbitraria (SSRF).
- **Solo `GET`/`HEAD`.** El front es estatico; las escrituras van a `/api/`.
- **No se reenvian `Cookie` ni `Authorization`.** El servicio de front no los
  necesita, y mandarlos filtraria la sesion a otro proceso.
- **Login obligatorio**, con el mismo stack de middleware que el resto del sitio.
- **Timeout corto**: si el front no responde, esta ruta devuelve 503 y el resto
  del sitio sigue funcionando.
"""

from __future__ import annotations

import logging
from urllib.parse import urljoin

import requests
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.utils.decorators import method_decorator
from django.views import View

logger = logging.getLogger("django")

#: Assets con hash en el nombre: cambian de nombre en cada build, asi que se
#: pueden cachear para siempre. El index.html no, porque su nombre es fijo.
CACHE_ASSETS = "public, max-age=31536000, immutable"
CACHE_HTML = "no-cache"

TIMEOUT_SEGUNDOS = getattr(settings, "FRONTEND_V2_TIMEOUT", 3)

#: Cabeceras que no se copian de la respuesta del front: las maneja el servidor.
CABECERAS_OMITIDAS = {
    "connection",
    "content-encoding",
    "content-length",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}


def destino_de(modulo: str) -> str:
    """URL base del servicio de front de ese modulo, o 404 si no esta permitido."""

    servicios = getattr(settings, "FRONTEND_V2_SERVICIOS", {}) or {}
    destino = servicios.get(modulo)
    if not destino:
        raise Http404("Modulo de front no configurado.")
    return destino if destino.endswith("/") else f"{destino}/"


@method_decorator(login_required, name="dispatch")
class FrontendV2ProxyView(View):
    """Reenvia `/v2/<modulo>/<ruta>` al servicio de front del modulo."""

    http_method_names = ["get", "head"]

    def get(self, request, modulo: str, ruta: str = ""):
        base = destino_de(modulo)
        url = urljoin(base, ruta)

        try:
            respuesta = requests.get(
                url,
                timeout=TIMEOUT_SEGUNDOS,
                # Sin cookies ni credenciales: el front estatico no las necesita.
                headers={"Accept": request.headers.get("Accept", "*/*")},
                allow_redirects=False,
            )
        except requests.RequestException as exc:
            logger.warning("Front v2 '%s' no responde (%s): %s", modulo, url, exc)
            return HttpResponse(
                "El front del módulo no está disponible.",
                status=503,
                content_type="text/plain; charset=utf-8",
            )

        # Una SPA sirve su index.html para cualquier ruta del router del cliente.
        if respuesta.status_code == 404 and not _parece_asset(ruta):
            respuesta = _pedir_index(base, modulo)
            if respuesta is None:
                return HttpResponse(
                    "El front del módulo no está disponible.",
                    status=503,
                    content_type="text/plain; charset=utf-8",
                )

        django_respuesta = HttpResponse(
            respuesta.content,
            status=respuesta.status_code,
            content_type=respuesta.headers.get(
                "Content-Type", "application/octet-stream"
            ),
        )
        for nombre, valor in respuesta.headers.items():
            if nombre.lower() in CABECERAS_OMITIDAS or nombre.lower() == "content-type":
                continue
            django_respuesta[nombre] = valor

        django_respuesta["Cache-Control"] = (
            CACHE_ASSETS if _parece_asset(ruta) else CACHE_HTML
        )
        return django_respuesta

    def head(self, request, *args, **kwargs):
        respuesta = self.get(request, *args, **kwargs)
        respuesta.content = b""
        return respuesta


def _parece_asset(ruta: str) -> bool:
    """Los assets con hash viven bajo `assets/` en el build de Vite."""

    return ruta.startswith("assets/")


def _pedir_index(base: str, modulo: str):
    try:
        return requests.get(urljoin(base, "index.html"), timeout=TIMEOUT_SEGUNDOS)
    except requests.RequestException as exc:
        logger.warning("Front v2 '%s' sin index.html: %s", modulo, exc)
        return None
