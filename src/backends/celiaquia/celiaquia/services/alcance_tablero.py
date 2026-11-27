"""Obtiene el alcance de la sesión desde el núcleo, sin parámetros del cliente."""

import json
from urllib.parse import urlsplit

import requests
from django.conf import settings
from django.http import Http404
from django.urls import Resolver404, resolve

RUTA = "/interno/tableros/celiaquia/alcance/"


def _origen_valido(origen):
    try:
        url = urlsplit(origen)
        return bool(
            url.scheme in ("http", "https")
            and url.hostname
            and url.username is None
            and url.password is None
            and url.path in ("", "/")
            and not url.query
            and not url.fragment
            and (url.port is None or 0 < url.port < 65536)
        )
    except ValueError:
        return False


def _respuesta_local(request):
    try:
        coincidencia = resolve(RUTA)
    except Resolver404:
        return None
    if coincidencia.url_name != "dashboard_alcance_celiaquia":
        return None
    try:
        respuesta = coincidencia.func(request)
    except Http404:
        # El registro de URLs puede resolver un stub de un servicio ausente.
        return None
    if respuesta.status_code != 200:
        return None
    try:
        return json.loads(respuesta.content)
    except (TypeError, ValueError):
        return None


def _respuesta_remota(request, origen):
    if not _origen_valido(origen):
        return None
    cookie = request.COOKIES.get(settings.SESSION_COOKIE_NAME)
    if not cookie:
        return None
    try:
        with requests.Session() as sesion:
            sesion.trust_env = False
            respuesta = sesion.get(
                origen.rstrip("/") + RUTA,
                cookies={settings.SESSION_COOKIE_NAME: cookie},
                headers={
                    "Host": request.get_host(),
                    "X-Forwarded-Proto": request.scheme,
                    "Accept": "application/json",
                },
                timeout=4,
                allow_redirects=False,
            )
            if respuesta.status_code != 200:
                return None
            return respuesta.json()
    except (requests.RequestException, ValueError):
        return None


def _provincias_validas(provincias):
    if not isinstance(provincias, list) or not provincias:
        return False
    if not all(
        isinstance(p, int) and not isinstance(p, bool) and p > 0 for p in provincias
    ):
        return False
    return len(set(provincias)) == len(provincias)


def alcance_tablero(request):
    """Devuelve (estado, provincias) o no disponible ante cualquier duda."""
    origen = getattr(settings, "SISOC_CORE_ORIGIN", "")
    datos = _respuesta_remota(request, origen) if origen else _respuesta_local(request)
    if not isinstance(datos, dict):
        return "no_disponible", ()
    estado = datos.get("estado")
    if estado in ("inactiva", "nacional", "denegado") and set(datos) == {"estado"}:
        return estado, ()
    provincias = datos.get("provincias")
    if (
        estado == "provincial"
        and set(datos) == {"estado", "provincias"}
        and _provincias_validas(provincias)
    ):
        return estado, tuple(provincias)
    return "no_disponible", ()
