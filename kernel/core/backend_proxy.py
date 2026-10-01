"""Proxy del SISOC core hacia los backends por vertical.

El core recibe todo el tráfico (el Nginx del host no cambia) y reenvía a cada
backend los prefijos que declara ``config/backends.json``. Antes de reenviar,
el stack de middleware del core ya corrió: sesión, autenticación y controles
de contraseña inicial, datos personales y encuesta obligatoria.

Contrato con el backend:

- La sesión es compartida (misma DB y ``SECRET_KEY``). El backend autentica y
  valida CSRF por su cuenta con la cookie y los headers originales. Por eso
  esta vista es ``csrf_exempt``: el core no valida dos veces.
- ``Host`` es el que el core ya validó contra ``ALLOWED_HOSTS``.
  ``X-Forwarded-Proto`` y ``X-Forwarded-For`` los calcula el core y **pisan**
  los que mande el cliente. ``X-Forwarded-Host`` no se reenvía.
- El backend no se publica fuera de la red de Compose: solo el core lo alcanza.
"""

from http.cookies import SimpleCookie

import requests
from django.conf import settings
from django.http import HttpResponse, StreamingHttpResponse
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


def _outbound_headers(request):
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

    url = origin.rstrip("/") + "/" + path
    if request.META.get("QUERY_STRING"):
        url += "?" + request.META["QUERY_STRING"]

    try:
        upstream = requests.request(
            request.method,
            url,
            headers=_outbound_headers(request),
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
