"""Políticas explícitas para rutas internas con aislamiento implementado."""

import posixpath
from urllib.parse import unquote, urlsplit

from django.apps import apps
from django.urls import Resolver404, resolve

from dashboard.services.alcance import AlcanceTablero, alcance_efectivo

CODIGO_PROGRESAR = "progresar_curso"
NOMBRE_RUTA_PROGRESAR = "dashboard_tablero_progresar_curso"


def es_ruta_progresar(ruta):
    if not ruta:
        return False
    try:
        camino = unquote(urlsplit(ruta).path)
        normalizado = posixpath.normpath(camino)
        if camino.endswith("/") and not normalizado.endswith("/"):
            normalizado += "/"
        return resolve(normalizado).url_name == NOMBRE_RUTA_PROGRESAR
    except Resolver404:
        return False


def configuracion_progresar():
    modelo = apps.get_model("dashboard", "ConfiguracionTableroInterno")
    return (
        modelo.objects.select_related("tablero")
        .filter(codigo=CODIGO_PROGRESAR, activa=True)
        .first()
    )


def alcance_progresar_explicito(usuario, configuracion):
    if not configuracion.tablero.activo or not es_ruta_progresar(
        configuracion.tablero.ruta_interna
    ):
        return AlcanceTablero()
    return alcance_efectivo(usuario, configuracion.tablero)


def visibilidad_tablero_interno(usuario, tablero, *, configuracion=...):
    if configuracion is ...:
        configuracion = configuracion_progresar()
    if not configuracion:
        return None
    if tablero.pk != configuracion.tablero_id and not es_ruta_progresar(
        tablero.ruta_interna
    ):
        return None
    alcance = alcance_progresar_explicito(usuario, configuracion)
    return bool(alcance.nacional or alcance.provincias)
