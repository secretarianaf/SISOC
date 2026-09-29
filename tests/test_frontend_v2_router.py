"""Router de /v2/<modulo>/.

El foco esta en lo que puede convertirse en un agujero: que el destino salga
siempre de la allowlist y nunca del request, que exija sesion, que no reenvie
credenciales y que un front caido no tumbe el resto del sitio.
"""

from unittest.mock import patch

import pytest
import requests
from django.contrib.auth.models import User
from django.urls import reverse

pytestmark = pytest.mark.django_db

SERVICIOS = {"celiaquia": "http://front_celiaquia:80/"}


class _RespuestaFalsa:
    def __init__(self, contenido=b"ok", status=200, headers=None):
        self.content = contenido
        self.status_code = status
        self.headers = headers or {"Content-Type": "text/html"}


@pytest.fixture
def usuario():
    return User.objects.create_user(username="lectora", password="pass")


def _url(modulo="celiaquia", ruta="index.html"):
    return reverse("frontend_v2", kwargs={"modulo": modulo, "ruta": ruta})


def test_sin_sesion_redirige_al_login(client):
    respuesta = client.get(_url())

    assert respuesta.status_code == 302
    assert "/login/" in respuesta["Location"]


@pytest.mark.parametrize("modulo", ["inexistente", "otro"])
def test_un_modulo_fuera_de_la_allowlist_es_404(client, usuario, modulo):
    """El destino sale de settings; un modulo arbitrario no alcanza ninguna URL."""

    client.force_login(usuario)

    with patch.multiple(
        "core.frontend_v2.settings", FRONTEND_V2_SERVICIOS=SERVICIOS, create=True
    ):
        respuesta = client.get(_url(modulo=modulo))

    assert respuesta.status_code == 404


def test_reenvia_el_contenido_del_servicio(client, usuario, settings):
    settings.FRONTEND_V2_SERVICIOS = SERVICIOS
    client.force_login(usuario)

    with patch(
        "core.frontend_v2.requests.get", return_value=_RespuestaFalsa(b"<html/>")
    ) as get:
        respuesta = client.get(_url())

    assert respuesta.status_code == 200
    assert respuesta.content == b"<html/>"
    assert get.call_args.args[0] == "http://front_celiaquia:80/index.html"


def test_no_reenvia_cookies_ni_authorization(client, usuario, settings):
    """El servicio de front no necesita la sesion; mandarsela la filtraria."""

    settings.FRONTEND_V2_SERVICIOS = SERVICIOS
    client.force_login(usuario)

    with patch("core.frontend_v2.requests.get", return_value=_RespuestaFalsa()) as get:
        client.get(_url(), HTTP_AUTHORIZATION="Bearer secreto")

    enviados = {k.lower() for k in (get.call_args.kwargs.get("headers") or {})}
    assert "cookie" not in enviados
    assert "authorization" not in enviados
    assert get.call_args.kwargs.get("cookies") is None


def test_si_el_front_no_responde_devuelve_503(client, usuario, settings):
    settings.FRONTEND_V2_SERVICIOS = SERVICIOS
    client.force_login(usuario)

    with patch(
        "core.frontend_v2.requests.get",
        side_effect=requests.RequestException("timeout"),
    ):
        respuesta = client.get(_url())

    assert respuesta.status_code == 503


def test_los_assets_con_hash_se_cachean_para_siempre(client, usuario, settings):
    settings.FRONTEND_V2_SERVICIOS = SERVICIOS
    client.force_login(usuario)

    with patch("core.frontend_v2.requests.get", return_value=_RespuestaFalsa()):
        respuesta = client.get(_url(ruta="assets/index-abc123.js"))

    assert respuesta["Cache-Control"] == "public, max-age=31536000, immutable"


def test_el_index_no_se_cachea(client, usuario, settings):
    """Su nombre es fijo: si se cacheara, un deploy no llegaria al navegador."""

    settings.FRONTEND_V2_SERVICIOS = SERVICIOS
    client.force_login(usuario)

    with patch("core.frontend_v2.requests.get", return_value=_RespuestaFalsa()):
        respuesta = client.get(_url())

    assert respuesta["Cache-Control"] == "no-cache"


def test_una_ruta_del_router_del_cliente_cae_en_el_index(client, usuario, settings):
    """La SPA maneja sus rutas: un 404 del servidor devuelve el index."""

    settings.FRONTEND_V2_SERVICIOS = SERVICIOS
    client.force_login(usuario)

    respuestas = [_RespuestaFalsa(status=404), _RespuestaFalsa(b"<html/>")]
    with patch("core.frontend_v2.requests.get", side_effect=respuestas) as get:
        respuesta = client.get(_url(ruta="expedientes/42"))

    assert respuesta.status_code == 200
    assert respuesta.content == b"<html/>"
    assert get.call_args.args[0] == "http://front_celiaquia:80/index.html"


def test_solo_acepta_get_y_head(client, usuario, settings):
    settings.FRONTEND_V2_SERVICIOS = SERVICIOS
    client.force_login(usuario)

    assert client.post(_url()).status_code == 405
    assert client.delete(_url()).status_code == 405
