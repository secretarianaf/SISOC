"""Las URLs viejas de un vertical redirigen a su prefijo nuevo (solo compatibilidad)."""

from django.test import RequestFactory
from django.urls import URLResolver, get_resolver
from django.urls.resolvers import RegexPattern

from core.legacy_redirects import redirecciones_legacy


def _resolver(ruta):
    resolver = URLResolver(
        RegexPattern(r"^/"), redirecciones_legacy("centrodefamilia/", ["centros/"])
    )
    return resolver.resolve(ruta)


def test_get_redirige_301_conservando_resto_y_query():
    match = _resolver("/centros/12/detalle/")
    respuesta = match.func(
        RequestFactory().get("/centros/12/detalle/?page=2"), **match.kwargs
    )
    assert respuesta.status_code == 301
    assert respuesta["Location"] == "/centrodefamilia/centros/12/detalle/?page=2"


def test_post_redirige_308_para_conservar_metodo():
    match = _resolver("/centros/crear/")
    respuesta = match.func(RequestFactory().post("/centros/crear/"), **match.kwargs)
    assert respuesta.status_code == 308
    assert respuesta["Location"] == "/centrodefamilia/centros/crear/"


def test_el_core_redirige_las_urls_viejas_de_cdf():
    match = get_resolver("config.urls").resolve("/beneficiarios/")
    respuesta = match.func(RequestFactory().get("/beneficiarios/"), **match.kwargs)
    assert respuesta["Location"] == "/centrodefamilia/beneficiarios/"
