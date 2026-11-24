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
- Si la autenticación del core rotó la clave de sesión (``cycle_key()``, por
  ejemplo al validar con ``SECRET_KEY_FALLBACKS``), se reenvía la cookie de la
  sesión vigente y el cliente recibe su ``Set-Cookie``: la clave vieja ya no
  existe.
- ``/api/web/<vertical>/`` (G1 v1, ``core.web_gate``): el core exige sesión y
  requisitos web, responde 401/403 JSON sin reenviar y firma la constancia
  ``X-SISOC-Web-Gate`` del request que envía. Su read timeout es igual a la
  ventana de la constancia; los demás prefijos conservan sus timeouts.
"""

import time
from http.cookies import SimpleCookie
from urllib.parse import quote

import requests
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.http import Http404, HttpResponse, StreamingHttpResponse
from django.urls import re_path
from django.utils.cache import patch_vary_headers
from django.utils.http import http_date
from django.views.decorators.csrf import csrf_exempt
from urllib3.exceptions import NewConnectionError

from core import web_gate

CONNECT_TIMEOUT_SECONDS = 5
# Por debajo del timeout de Gunicorn del core, para responder 504 propio.
READ_TIMEOUT_SECONDS = 25
# Only ``/api/web/<vertical>/``: equal to the G1 attestation window, so the
# runtime never starts a request the core already abandoned with a 504.
WEB_API_READ_TIMEOUT_SECONDS = web_gate.MAX_AGE_SECONDS
SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}
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
    # G1 attestation: only the core emits it; a client value is never copied.
    "x-sisoc-web-gate",
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


def _session_cookie_header(cookie_header, session_key):
    """Client ``Cookie`` header carrying the current session key instead of the old one."""
    name = settings.SESSION_COOKIE_NAME
    parts = []
    for part in cookie_header.split(";"):
        part = part.strip()
        if part and part.partition("=")[0].strip() != name:
            parts.append(part)
    parts.append(f"{name}={session_key}")
    return "; ".join(parts)


def _set_session_cookie(response, session):
    """The same ``Set-Cookie`` ``SessionMiddleware`` would emit."""
    if session.get_expire_at_browser_close():
        max_age = expires = None
    else:
        max_age = session.get_expiry_age()
        expires = http_date(time.time() + max_age)
    response.set_cookie(
        settings.SESSION_COOKIE_NAME,
        session.session_key,
        max_age=max_age,
        expires=expires,
        domain=settings.SESSION_COOKIE_DOMAIN,
        path=settings.SESSION_COOKIE_PATH,
        secure=settings.SESSION_COOKIE_SECURE or None,
        httponly=settings.SESSION_COOKIE_HTTPONLY or None,
        samesite=settings.SESSION_COOKIE_SAMESITE,
    )
    patch_vary_headers(response, ("Cookie",))


def _rotated_session(request):
    """Session whose key changed during this request (``cycle_key()``), if any."""
    session = getattr(request, "session", None)
    incoming = request.COOKIES.get(settings.SESSION_COOKIE_NAME)
    if session is None or incoming is None:
        return None
    current = session.session_key
    if current and current != incoming:
        return session
    return None


def _never_sent(exc):
    """The request never left the core: the runtime cannot have run anything."""
    if isinstance(exc, requests.ConnectTimeout):
        return True
    reason = getattr(exc.args[0], "reason", None) if exc.args else None
    return isinstance(reason, NewConnectionError)


def _web_api_failure(request, exc):
    if _never_sent(exc):
        return web_gate.json_response(503, {"detail": web_gate.DETAIL_UNAVAILABLE})
    # Already sent: never retried. For a mutation the outcome is uncertain.
    if request.method not in SAFE_METHODS:
        return web_gate.json_response(
            504, {"detail": web_gate.DETAIL_UNCERTAIN, "uncertain": True}
        )
    if isinstance(exc, requests.Timeout):
        return web_gate.json_response(
            504, {"detail": web_gate.DETAIL_TIMEOUT, "uncertain": False}
        )
    return web_gate.json_response(503, {"detail": web_gate.DETAIL_UNAVAILABLE})


def _send_web_api(request, url, headers, data, audience):
    """Send, with the G1 attestation, the exact ``PreparedRequest`` that is signed."""
    headers["x-request-id"] = web_gate.request_id(headers.get("x-request-id"))
    with requests.Session() as http:
        prepared = http.prepare_request(
            requests.Request(request.method, url, headers=headers, data=data)
        )
        try:
            prepared.headers[web_gate.HEADER] = web_gate.sign(
                audience=audience,
                user_pk=request.user.pk,
                session_key=request.session.session_key,
                method=request.method,
                target=prepared.path_url,
            )
        except web_gate.TargetTooLarge:
            return web_gate.json_response(
                414, {"detail": web_gate.DETAIL_TARGET_TOO_LONG}
            )
        try:
            return http.send(
                prepared,
                allow_redirects=False,
                stream=True,
                timeout=(CONNECT_TIMEOUT_SECONDS, WEB_API_READ_TIMEOUT_SECONDS),
            )
        except requests.RequestException as exc:
            return _web_api_failure(request, exc)


def _send(request, url, headers, data, uncertain_on_failure):
    try:
        return requests.request(
            request.method,
            url,
            headers=headers,
            data=data,
            allow_redirects=False,
            stream=True,
            timeout=(CONNECT_TIMEOUT_SECONDS, READ_TIMEOUT_SECONDS),
        )
    except requests.Timeout:
        if uncertain_on_failure:
            return HttpResponse(
                "No se pudo confirmar el resultado. Verificá el usuario antes de reintentar.",
                status=504,
            )
        return HttpResponse("El servicio no respondió a tiempo.", status=504)
    except requests.RequestException:
        if uncertain_on_failure:
            return HttpResponse(
                "No se pudo confirmar el resultado. Verificá el usuario antes de reintentar.",
                status=503,
            )
        return HttpResponse("El servicio no está disponible.", status=503)


def _forward(  # pylint: disable=too-many-arguments
    request,
    origin,
    path,
    *,
    body=None,
    query_string=None,
    uncertain_on_failure=False,
    web_gate_audience=None,
):
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
    query_string = (
        request.META.get("QUERY_STRING") if query_string is None else query_string
    )
    if query_string:
        url += "?" + query_string

    headers = outbound_headers(request)
    rotated = _rotated_session(request)
    if rotated is not None:
        headers["cookie"] = _session_cookie_header(
            headers.get("cookie", ""), rotated.session_key
        )
    data = (
        body
        if body is not None
        else (_RequestBody(request) if request.META.get("CONTENT_LENGTH") else None)
    )

    if web_gate_audience is not None:
        upstream = _send_web_api(request, url, headers, data, web_gate_audience)
    else:
        upstream = _send(request, url, headers, data, uncertain_on_failure)
    if isinstance(upstream, HttpResponse):
        return upstream

    if request.method == "HEAD":
        response = HttpResponse(status=upstream.status_code)
        upstream.close()
    else:
        response = StreamingHttpResponse(
            _raw_body(upstream), status=upstream.status_code
        )
    _copy_response_headers(upstream, response)

    if rotated is not None and settings.SESSION_COOKIE_NAME not in response.cookies:
        _set_session_cookie(response, rotated)
    if web_gate_audience is not None:
        web_gate.mark_private(response)
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


# Propiedad de secciones del cluster aprobado; no registra un runtime C3.
APPS_SECCIONES_FAVORITAS = {
    "comedores": "comedores",
    "admisiones_tecnicos": "admisiones",
    "admisiones_legales": "admisiones",
    "acompanamientos": "acompanamientos",
    "duplas": "duplas",
    "rendiciones": "rendicioncuentasmensual",
}


def backend_de_seccion_favorita(seccion):
    """Backend dueño de una sección de filtros favoritos, si no es del core."""
    app_label = APPS_SECCIONES_FAVORITAS.get(seccion)
    if app_label is not None:
        return backend_de_app(app_label)
    for spec in getattr(settings, "SISOC_BACKENDS", {}).values():
        if seccion in spec.get("favorite_sections", ()):
            return spec
    return None


def reenviar_a_backend(request, spec, **kwargs):
    """Reenvía este request, tal cual, al backend ``spec``."""
    path = kwargs.pop("path", request.path_info.lstrip("/"))
    return _forward(request, spec["origin"], path, **kwargs)


def _proxy_view(origin):
    @csrf_exempt
    def view(request, path):
        return _forward(request, origin, path)

    return view


def _web_api_view(origin, audience):
    """``/api/web/<vertical>/``: the core decides web access before forwarding."""

    @csrf_exempt
    def view(request, path):
        session = getattr(request, "session", None)
        if not request.user.is_authenticated or not getattr(
            session, "session_key", None
        ):
            # The attestation binds a session cookie: other auth never crosses.
            return web_gate.unauthenticated_response()
        access = web_gate.resolve_local_policy(request)
        if access.state == "unauthenticated":
            return web_gate.unauthenticated_response()
        if access.state != "ready":
            return web_gate.requirement_response(access)
        return _forward(request, origin, path, web_gate_audience=audience)

    return view


def _view_for_prefix(name, spec, prefix):
    if not prefix.startswith(web_gate.WEB_API_ROOT):
        return _proxy_view(spec["origin"])
    if prefix != web_gate.web_api_prefix(name):
        raise ImproperlyConfigured(
            f"Backend {name!r} may only publish "
            f"{web_gate.web_api_prefix(name)!r} under {web_gate.WEB_API_ROOT!r}, "
            f"not {prefix!r}."
        )
    return _web_api_view(spec["origin"], name)


def backend_proxy_urlpatterns():
    """Una ruta por prefijo de cada backend de ``settings.SISOC_BACKENDS``."""
    patterns = []
    for name, spec in getattr(settings, "SISOC_BACKENDS", {}).items():
        for prefix in spec["url_prefixes"]:
            view = _view_for_prefix(name, spec, prefix)
            escaped = prefix.replace(".", r"\.")
            patterns.append(
                re_path(
                    rf"^(?P<path>{escaped}.*)$",
                    view,
                    name=f"backend_proxy_{name}_{prefix.strip('/').replace('/', '_')}",
                )
            )
    return patterns
