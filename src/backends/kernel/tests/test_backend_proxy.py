"""Proxy del core hacia los backends (``core.backend_proxy``).

Se prueba contra un servidor HTTP real que hace de backend: lo que importa es
qué viaja por la red (headers, body, cookies, compresión), no la llamada a
``requests``.
"""

import gzip
import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from django.http import Http404
from django.test import RequestFactory, override_settings

from core.backend_proxy import _forward, backend_proxy_urlpatterns

CUERPO_GZIP = gzip.compress(b"contenido comprimido")


class _Backend(BaseHTTPRequestHandler):
    def log_message(self, *args):  # silencio en tests
        del args

    def _eco(self):
        largo = int(self.headers.get("Content-Length") or 0)
        cuerpo = self.rfile.read(largo) if largo else b""
        datos = {
            "method": self.command,
            "path": self.path,
            "headers": {k.lower(): v for k, v in self.headers.items()},
            "body_len": len(cuerpo),
            "body_head": cuerpo[:20].decode("latin-1"),
        }
        salida = json.dumps(datos).encode()
        self.send_response(201)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(salida)))
        self.send_header("Set-Cookie", "sessionid=abc; Path=/; HttpOnly")
        self.send_header("Set-Cookie", "messages=xyz; Path=/; Max-Age=0")
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(salida)

    def do_GET(self):  # noqa: N802
        if self.path.startswith("/dispositivos/gzip"):
            self.send_response(200)
            self.send_header("Content-Encoding", "gzip")
            self.send_header("Content-Length", str(len(CUERPO_GZIP)))
            self.end_headers()
            self.wfile.write(CUERPO_GZIP)
        elif self.path.startswith("/dispositivos/redirect"):
            self.send_response(302)
            self.send_header("Location", "/dispositivos/1/")
            self.send_header("Content-Length", "0")
            self.end_headers()
        else:
            self._eco()

    do_POST = _eco
    do_DELETE = _eco


@pytest.fixture(name="backend")
def backend_fixture():
    servidor = ThreadingHTTPServer(("127.0.0.1", 0), _Backend)
    hilo = threading.Thread(target=servidor.serve_forever, daemon=True)
    hilo.start()
    yield f"http://127.0.0.1:{servidor.server_port}"
    servidor.shutdown()


def _contenido(response):
    return b"".join(response.streaming_content)


def test_reenvia_metodo_path_query_y_body(backend):
    request = RequestFactory().post("/dispositivos/crear?x=1", data={"campo": "valor"})

    response = _forward(request, backend, "dispositivos/crear")
    datos = json.loads(_contenido(response))

    assert response.status_code == 201
    assert datos["method"] == "POST"
    assert datos["path"] == "/dispositivos/crear?x=1"
    assert datos["body_len"] > 0


@pytest.mark.parametrize(
    "path", ["dispositivos/../admin/", "dispositivos/./x", "dispositivos/.."]
)
def test_rechaza_segmentos_punto_para_no_salir_del_prefijo(backend, path):
    """``%2e%2e`` llega decodificado como ``..`` en ``path``."""
    request = RequestFactory().get("/dispositivos/%2e%2e/admin/")

    with pytest.raises(Http404):
        _forward(request, backend, path)


def test_reenvia_el_path_codificado(backend):
    request = RequestFactory().get("/dispositivos/a%3Fb%23c%25d%20e/")

    response = _forward(request, backend, "dispositivos/a?b#c%d e/ñ")
    datos = json.loads(_contenido(response))

    assert datos["path"] == "/dispositivos/a%3Fb%23c%25d%20e/%C3%B1"


def test_body_mayor_al_limite_de_memoria_se_reenvia_completo(backend):
    """Un upload grande no pasa por ``request.body`` (DATA_UPLOAD_MAX_MEMORY_SIZE)."""
    archivo = b"A" * (3 * 1024 * 1024)
    request = RequestFactory().generic(
        "POST",
        "/dispositivos/crear",
        data=archivo,
        content_type="application/octet-stream",
    )

    with override_settings(DATA_UPLOAD_MAX_MEMORY_SIZE=1024):
        response = _forward(request, backend, "dispositivos/crear")
    datos = json.loads(_contenido(response))

    assert datos["body_len"] == len(archivo)


def test_el_core_pisa_los_headers_de_identidad_del_cliente(backend):
    request = RequestFactory().get(
        "/dispositivos/",
        HTTP_HOST="sisoc.example",
        HTTP_X_FORWARDED_HOST="atacante.example",
        HTTP_X_FORWARDED_PROTO="https",
        HTTP_COOKIE="sessionid=abc",
        HTTP_AUTHORIZATION="Token t",
        REMOTE_ADDR="10.0.0.5",
    )

    with override_settings(ALLOWED_HOSTS=["sisoc.example"]):
        response = _forward(request, backend, "dispositivos/")
    headers = json.loads(_contenido(response))["headers"]

    assert headers["host"] == "sisoc.example"
    assert "x-forwarded-host" not in headers
    # Lo calcula el core (http en el test), no lo que mandó el cliente.
    assert headers["x-forwarded-proto"] == "http"
    assert headers["x-forwarded-for"] == "10.0.0.5"
    assert headers["cookie"] == "sessionid=abc"
    assert headers["authorization"] == "Token t"


def test_conserva_cada_set_cookie_del_backend(backend):
    response = _forward(
        RequestFactory().get("/dispositivos/"), backend, "dispositivos/"
    )

    assert response.cookies["sessionid"].value == "abc"
    assert response.cookies["sessionid"]["httponly"]
    assert response.cookies["messages"]["max-age"] == "0"


def test_no_descomprime_y_mantiene_content_encoding(backend):
    response = _forward(
        RequestFactory().get("/dispositivos/gzip"), backend, "dispositivos/gzip"
    )

    assert response["Content-Encoding"] == "gzip"
    assert _contenido(response) == CUERPO_GZIP


def test_no_sigue_redirects_del_backend(backend):
    response = _forward(
        RequestFactory().get("/dispositivos/redirect"), backend, "dispositivos/redirect"
    )

    assert response.status_code == 302
    assert response["Location"] == "/dispositivos/1/"


def test_backend_caido_responde_503():
    with socket.socket() as libre:
        libre.bind(("127.0.0.1", 0))
        puerto = libre.getsockname()[1]

    response = _forward(
        RequestFactory().get("/dispositivos/"), f"http://127.0.0.1:{puerto}", "x"
    )

    assert response.status_code == 503


def test_rutas_por_prefijo_y_csrf_exempt():
    backends = {
        "dispositivos": {
            "url_prefixes": ("dispositivos/", "api/datacalle/"),
            "origin": "http://backend:8000",
        }
    }
    with override_settings(SISOC_BACKENDS=backends):
        patrones = backend_proxy_urlpatterns()

    assert [p.pattern.match("dispositivos/1/") is not None for p in patrones] == [
        True,
        False,
    ]
    assert patrones[1].pattern.match("api/datacalle/x") is not None
    assert all(getattr(p.callback, "csrf_exempt", False) for p in patrones)


@pytest.mark.django_db
def test_favoritos_de_seccion_de_backend_se_reenvian(backend, django_user_model):
    """El core no tiene registrada la sección de un backend: la atiende el backend."""
    from core.views import filtros_favoritos  # pylint: disable=import-outside-toplevel

    usuario = django_user_model.objects.create_user("fav", password="x")
    request = RequestFactory().get("/filtros-favoritos/?seccion=seccion_backend")
    request.user = usuario
    backends = {
        "x": {
            "url_prefixes": ("x/",),
            "origin": backend,
            "favorite_sections": ("seccion_backend",),
        }
    }

    with override_settings(SISOC_BACKENDS=backends):
        response = filtros_favoritos(request)
    datos = json.loads(_contenido(response))

    assert datos["path"] == "/filtros-favoritos/?seccion=seccion_backend"


@pytest.mark.django_db
def test_favoritos_de_seccion_desconocida_siguen_dando_400(django_user_model):
    from core.views import filtros_favoritos  # pylint: disable=import-outside-toplevel

    request = RequestFactory().get("/filtros-favoritos/?seccion=inexistente")
    request.user = django_user_model.objects.create_user("fav2", password="x")

    with override_settings(SISOC_BACKENDS={}):
        assert filtros_favoritos(request).status_code == 400
