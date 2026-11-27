"""Políticas explícitas para el catálogo de tableros."""

import posixpath
from urllib.parse import unquote, urlsplit

from django.apps import apps
from django.urls import Resolver404, resolve

from dashboard.services.alcance import (
    AlcanceTablero,
    alcance_efectivo,
    concesiones_nacionales,
)

CODIGO_PROGRESAR = "progresar_curso"
NOMBRE_RUTA_PROGRESAR = "dashboard_tablero_progresar_curso"
CODIGO_CELIAQUIA = "celiaquia"
RUTA_CELIAQUIA = "/celiaquia/tablero/"
NOMBRE_RUTA_CELIAQUIA = "celiaquia_tablero"
NOMBRE_PROXY_CELIAQUIA = "backend_proxy_celiaquia_celiaquia"


def es_embed_externo(tablero):
    if tablero.ruta_interna or not tablero.url:
        return False
    try:
        destino = urlsplit(tablero.url)
        return destino.scheme in ("http", "https") and bool(destino.hostname)
    except ValueError:
        return False


def acceso_explicito_embed(usuario, tablero, *, tableros_nacionales=None):
    if not tablero.activo or not es_embed_externo(tablero):
        return False
    if tableros_nacionales is not None:
        return tablero.pk in tableros_nacionales
    return concesiones_nacionales(usuario).filter(tablero=tablero).exists()


def ids_embeds_nacionales(usuario, tableros):
    embeds = [tablero.pk for tablero in tableros if es_embed_externo(tablero)]
    return set(
        concesiones_nacionales(usuario)
        .filter(tablero_id__in=embeds)
        .values_list("tablero_id", flat=True)
        .distinct()
    )


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


def es_ruta_celiaquia(ruta):
    if not ruta:
        return False
    try:
        camino = unquote(urlsplit(ruta).path)
        normalizado = posixpath.normpath(camino)
        if camino.endswith("/") and not normalizado.endswith("/"):
            normalizado += "/"
        nombre = resolve(normalizado).url_name
        return nombre == NOMBRE_RUTA_CELIAQUIA or (
            normalizado == RUTA_CELIAQUIA and nombre == NOMBRE_PROXY_CELIAQUIA
        )
    except (Resolver404, ValueError):
        return False


def ruta_celiaquia_interna_segura(ruta):
    try:
        partes = urlsplit(ruta)
    except ValueError:
        return False
    return bool(
        ruta.startswith("/")
        and not ruta.startswith("//")
        and not partes.scheme
        and not partes.netloc
        and not partes.query
        and not partes.fragment
    )


def configuracion_progresar():
    modelo = apps.get_model("dashboard", "ConfiguracionTableroInterno")
    return (
        modelo.objects.select_related("tablero")
        .filter(codigo=CODIGO_PROGRESAR, activa=True)
        .first()
    )


def configuracion_celiaquia():
    modelo = apps.get_model("dashboard", "ConfiguracionTableroInterno")
    return (
        modelo.objects.select_related("tablero")
        .filter(codigo=CODIGO_CELIAQUIA, activa=True)
        .first()
    )


def alcance_progresar_explicito(usuario, configuracion):
    if not configuracion.tablero.activo or not es_ruta_progresar(
        configuracion.tablero.ruta_interna
    ):
        return AlcanceTablero()
    return alcance_efectivo(usuario, configuracion.tablero)


def visibilidad_tablero_interno(
    usuario, tablero, *, configuracion=..., configuracion_celiaquia_actual=...
):
    if configuracion is ...:
        configuracion = configuracion_progresar()
    if configuracion and (
        tablero.pk == configuracion.tablero_id
        or es_ruta_progresar(tablero.ruta_interna)
    ):
        alcance = alcance_progresar_explicito(usuario, configuracion)
        return bool(alcance.nacional or alcance.provincias)
    celiaquia = (
        configuracion_celiaquia()
        if configuracion_celiaquia_actual is ...
        else configuracion_celiaquia_actual
    )
    if celiaquia and (
        tablero.pk == celiaquia.tablero_id or es_ruta_celiaquia(tablero.ruta_interna)
    ):
        if (
            not celiaquia.tablero.activo
            or celiaquia.tablero.ruta_interna != RUTA_CELIAQUIA
            or not ruta_celiaquia_interna_segura(tablero.ruta_interna)
        ):
            return False
        alcance = alcance_efectivo(usuario, celiaquia.tablero)
        return bool(alcance.nacional or alcance.provincias)
    return None
