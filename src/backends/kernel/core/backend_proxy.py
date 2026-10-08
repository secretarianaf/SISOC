"""Proxy del SISOC core hacia los backends por vertical.

El core recibe todo el tráfico (el Nginx del host no cambia) y reenvía a cada
backend los prefijos que declara ``src/backends/config/backends.json``. Antes de reenviar,
el stack de middleware del core ya corrió: sesión, autenticación y controles
de contraseña inicial, datos personales y encuesta obligatoria.

Contrato con el backend:

- La sesión es compartida (misma DB y ``SECRET_KEY``). El backend autentica y
  valida CSRF por su cuenta con la cookie y los headers originales. Por eso
  esta vista es ``csrf_exempt``: el core no valida dos veces.
- ``Host`` es el que el core ya validó contra ``ALLOWED_HOSTS``.
  ``X-Forwarded-Proto`` lo calcula el core y **pisa** el del cliente.
  ``X-Forwarded-For`` conserva la cadena recibida y le agrega ``REMOTE_ADDR``
  (convención de proxies): solo el último salto es confiable.
  ``X-Forwarded-Host`` no se reenvía.
- El path viaja codificado otra vez y sin segmentos ``.``/``..``: un
  ``%2e%2e`` no puede salir del prefijo declarado.
- El backend no se publica fuera de la red de Compose: solo el core lo alcanza.
"""

from http.cookies import SimpleCookie
from urllib.parse import quote

import requests
from django.conf import settings
from django.http import Http404, HttpResponse, StreamingHttpResponse
from django.urls import re_path
from django.views.decorators.csrf import csrf_exempt

CONNECT_TIMEOUT_SECONDS = 5
# Por debajo del timeout de Gunicorn del core, para responder 504 propio.
READ_TIMEOUT_SECONDS = 25
CHUNK_SIZE = 64 * 1024

# RFC 9110 §7.6.1 más los que el core recalcula.
HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
}
REQUEST_HEADERS_SET_BY_CORE = {
    "host",
    "content-length",
    "x-forwarded-for",
    "x-forwarded-host",
    "x-forwarded-proto",
}
RESPONSE_HEADERS_SET_BY_CORE = {"set-cookie"}
# Caracteres que pueden ir sin codificar en un path (RFC 3986 pchar y "/").
PATH_SAFE_CHARS = "/:@!$&'()*+,;="


def outbound_headers(request):
    """Headers para pedir algo a un backend en nombre del request del usuario."""
    headers = {}
    for key, value in request.META.items():
        if key.startswith("HTTP_"):
            name = key[5:].replace("_", "-").lower()
        elif key in ("CONTENT_TYPE", "CONTENT_LENGTH"):
            name = key.replace("_", "-").lower()
        else:
            continue
        if name in HOP_BY_HOP_HEADERS or name in REQUEST_HEADERS_SET_BY_CORE:
            continue
        headers[name] = value

    headers["host"] = request.get_host()
    headers["x-forwarded-proto"] = request.scheme
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    remote_addr = request.META.get("REMOTE_ADDR", "")
    headers["x-forwarded-for"] = (
        f"{forwarded_for}, {remote_addr}" if forwarded_for else remote_addr
    )
    return headers


def _copy_response_headers(upstream, response):
    for name, value in upstream.headers.items():
        if (
            name.lower() in HOP_BY_HOP_HEADERS
            or name.lower() in RESPONSE_HEADERS_SET_BY_CORE
        ):
            continue
        response[name] = value
    # requests une los Set-Cookie repetidos en un solo header: se leen crudos.
    for raw_cookie in upstream.raw.headers.getlist("Set-Cookie"):
        response.cookies.load(SimpleCookie(raw_cookie))


class _RequestBody:
    """Body del request como stream con largo conocido.

    No usa ``request.body``: ese acceso aplica ``DATA_UPLOAD_MAX_MEMORY_SIZE``
    y rechazaría uploads grandes (documentación de Dispositivos). Con ``len``
    requests manda ``Content-Length``, que Django del backend necesita.
    """

    def __init__(self, request):
        self._request = request
        self._length = int(request.META.get("CONTENT_LENGTH") or 0)

    def __len__(self):
        return self._length

    def read(self, size=-1):
        return self._request.read(size)


def _raw_body(upstream):
    """Bytes tal como los mandó el backend, sin descomprimir.

    Así ``Content-Encoding`` y ``Content-Length`` siguen siendo válidos.
    Django cierra este generador al terminar la respuesta y eso libera la
    conexión con el backend.
    """
    try:
        yield from upstream.raw.stream(CHUNK_SIZE, decode_content=False)
    finally:
        upstream.close()


def _forward(request, origin, path):
    # Si algún middleware del core tocó la sesión, se guarda antes de reenviar
    # y no se vuelve a guardar después, para no pisar lo que escriba el backend.
    session = getattr(request, "session", None)
    if session is not None and session.modified:
        session.save()

    # ``path`` llega decodificado: se rechazan los segmentos punto y se vuelve
    # a codificar para que ``%3F``, ``%23`` o ``%25`` lleguen tal cual.
    if any(segmento in {".", ".."} for segmento in path.split("/")):
        raise Http404
    url = origin.rstrip("/") + "/" + quote(path, safe=PATH_SAFE_CHARS)
    if request.META.get("QUERY_STRING"):
        url += "?" + request.META["QUERY_STRING"]

    try:
        upstream = requests.request(
            request.method,
            url,
            headers=outbound_headers(request),
            data=_RequestBody(request) if request.META.get("CONTENT_LENGTH") else None,
            allow_redirects=False,
            stream=True,
            timeout=(CONNECT_TIMEOUT_SECONDS, READ_TIMEOUT_SECONDS),
        )
    except requests.Timeout:
        return HttpResponse("El servicio no respondió a tiempo.", status=504)
    except requests.RequestException:
        return HttpResponse("El servicio no está disponible.", status=503)

    if request.method == "HEAD":
        response = HttpResponse(status=upstream.status_code)
        upstream.close()
    else:
        response = StreamingHttpResponse(
            _raw_body(upstream), status=upstream.status_code
        )
    _copy_response_headers(upstream, response)

    if session is not None:
        session.modified = False
    return response


def backend_de_app(app_label):
    """Backend (``SISOC_BACKENDS``) que corre ``app_label``, si no es del core."""
    from config.backends import (  # pylint: disable=import-outside-toplevel
        load_backends_registry,
    )

    for nombre, spec in load_backends_registry().items():
        if app_label in spec["apps"]:
            return getattr(settings, "SISOC_BACKENDS", {}).get(nombre)
    return None


def pedir_json_a_backend(request, spec, path, timeout=4):
    """GET ``path`` al backend ``spec`` con la sesión del usuario; ``None`` si falla.

    Para datos chicos que una pantalla del core muestra de un vertical que corre
    aparte (p. ej. las métricas de Centro de Familia en el dashboard).
    """
    try:
        respuesta = requests.get(
            spec["origin"].rstrip("/") + "/" + path.lstrip("/"),
            headers=outbound_headers(request),
            timeout=timeout,
            allow_redirects=False,
        )
    except requests.RequestException:
        return None
    if respuesta.status_code != 200:
        return None
    try:
        return respuesta.json()
    except ValueError:
        return None


def backend_de_seccion_favorita(seccion):
    """Backend dueño de una sección de filtros favoritos, si no es del core."""
    for spec in getattr(settings, "SISOC_BACKENDS", {}).values():
        if seccion in spec.get("favorite_sections", ()):
            return spec
    return None


def reenviar_a_backend(request, spec):
    """Reenvía este request, tal cual, al backend ``spec``."""
    return _forward(request, spec["origin"], request.path_info.lstrip("/"))


def _proxy_view(origin):
    @csrf_exempt
    def view(request, path):
        return _forward(request, origin, path)

    return view


def backend_proxy_urlpatterns():
    """Una ruta por prefijo de cada backend de ``settings.SISOC_BACKENDS``."""
    patterns = []
    for name, spec in getattr(settings, "SISOC_BACKENDS", {}).items():
        view = _proxy_view(spec["origin"])
        for prefix in spec["url_prefixes"]:
            escaped = prefix.replace(".", r"\.")
            patterns.append(
                re_path(
                    rf"^(?P<path>{escaped}.*)$",
                    view,
                    name=f"backend_proxy_{name}_{prefix.strip('/').replace('/', '_')}",
                )
            )
    return patterns
