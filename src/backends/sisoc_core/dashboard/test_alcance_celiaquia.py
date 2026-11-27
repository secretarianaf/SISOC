"""Contrato de alcance de Celiaquía para la sesión autenticada."""

from types import ModuleType

import pytest
from django.contrib.auth.models import User
from django.db import connection
from django.test import Client, RequestFactory
from django.test import override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import re_path

from core.models import Provincia
from dashboard.models import (
    AudienciaTableros,
    ConcesionTablero,
    ConfiguracionTableroInterno,
    Tablero,
)

URL = "/interno/tableros/celiaquia/alcance/"


@pytest.mark.django_db
def test_contrato_usa_solo_sesion_y_distingue_politicas():
    client = Client()
    assert client.get(URL).status_code == 403
    usuario = User.objects.create_user(username="alcance")
    otro = User.objects.create_user(username="otro")
    tablero = Tablero.objects.create(
        nombre="Celiaquía", slug="celiaquia", ruta_interna="/celiaquia/tablero/"
    )
    config = ConfiguracionTableroInterno.objects.create(
        codigo="celiaquia", tablero=tablero, activa=False
    )
    client.force_login(usuario)
    response = client.get(URL)
    assert response.status_code == 200
    assert response.json() == {"estado": "inactiva"}
    assert "no-store" in response["Cache-Control"]

    config.activa = True
    config.save(update_fields=["activa"])
    assert client.get(URL).json() == {"estado": "denegado"}
    provincia = Provincia.objects.create(nombre="Salta")
    audiencia = AudienciaTableros.objects.create(nombre="Territorial")
    audiencia.agregar_miembro(usuario)
    ConcesionTablero.objects.create(
        audiencia=audiencia, tablero=tablero, tipo="provincia", provincia=provincia
    )
    ConcesionTablero.objects.create(usuario=otro, tablero=tablero, tipo="nacional")
    ConcesionTablero.objects.create(
        usuario=usuario, tablero=tablero, tipo="cdi", cdi_id=1
    )
    response = client.get(URL, {"usuario": otro.pk, "provincia": 999})
    assert response.json() == {"estado": "provincial", "provincias": [provincia.pk]}
    ConcesionTablero.objects.create(usuario=usuario, tablero=tablero, tipo="nacional")
    assert client.get(URL).json() == {"estado": "nacional"}

    tablero.ruta_interna = "https://example.org/celiaquia/tablero/"
    tablero.save(update_fields=["ruta_interna"])
    assert client.get(URL).status_code == 503
    usuario.is_active = False
    usuario.save(update_fields=["is_active"])
    assert client.get(URL).status_code == 403


@pytest.mark.django_db
def test_sin_configuracion_es_legacy_y_cdi_no_concede_alcance():
    user = User.objects.create_user(username="datos")
    client = Client()
    client.force_login(user)
    assert client.get(URL).json() == {"estado": "inactiva"}
    tablero = Tablero.objects.create(
        nombre="Celiaquía", slug="celiaquia", ruta_interna="/celiaquia/tablero/"
    )
    ConfiguracionTableroInterno.objects.create(
        codigo="celiaquia", tablero=tablero, activa=True
    )
    ConcesionTablero.objects.create(usuario=user, tablero=tablero, tipo="cdi", cdi_id=1)
    assert client.get(URL).json() == {"estado": "denegado"}


@pytest.mark.django_db
def test_head_usa_la_misma_autorizacion_de_sesion():
    client = Client()
    assert client.head(URL).status_code == 403
    usuario = User.objects.create_user(username="staff", is_staff=True)
    client.force_login(usuario)
    response = client.head(URL)
    assert response.status_code == 200
    assert "X-View" not in response
    usuario.is_active = False
    usuario.save(update_fields=["is_active"])
    assert client.head(URL).status_code == 403


@pytest.mark.django_db
def test_menu_aplica_concesiones_y_no_puede_ser_eludido_por_alias():
    from dashboard.templatetags.dashboard_tags import tableros_para_sidebar

    usuario = User.objects.create_user(username="concesionario")
    sin_concesion = User.objects.create_superuser(username="legacy", password="x")
    tablero = Tablero.objects.create(
        nombre="Celiaquía", slug="celiaquia", ruta_interna="/celiaquia/tablero/"
    )
    config = ConfiguracionTableroInterno.objects.create(
        codigo="celiaquia", tablero=tablero, activa=True
    )
    alias = Tablero.objects.create(
        nombre="Alias", slug="alias-celiaquia", ruta_interna="/celiaquia/./tablero/"
    )
    audiencia = AudienciaTableros.objects.create(nombre="Audiencia")
    audiencia.agregar_miembro(usuario)
    provincia = Provincia.objects.create(nombre="Salta")
    ConcesionTablero.objects.create(
        tablero=tablero, audiencia=audiencia, tipo="provincia", provincia=provincia
    )
    assert tablero.usuario_puede_ver(usuario)
    assert alias.usuario_puede_ver(usuario)
    assert not tablero.usuario_puede_ver(sin_concesion)
    assert not alias.usuario_puede_ver(sin_concesion)
    alias.ruta_interna = "https://example.org/celiaquia/tablero/"
    alias.save(update_fields=["ruta_interna"])
    assert not alias.usuario_puede_ver(usuario)
    assert not alias.usuario_puede_ver(sin_concesion)
    alias.ruta_interna = "/celiaquia/./tablero/"
    alias.save(update_fields=["ruta_interna"])
    request = RequestFactory().get("/")
    request.user = usuario
    urls = [item["url"] for item in tableros_para_sidebar({"request": request})]
    assert "/celiaquia/tablero/" in urls
    request.user = sin_concesion
    assert tableros_para_sidebar({"request": request}) == []
    tablero.ruta_interna = "/ruta-invalida/"
    tablero.save(update_fields=["ruta_interna"])
    assert not tablero.usuario_puede_ver(usuario)
    assert not alias.usuario_puede_ver(usuario)
    config.activa = False
    config.save(update_fields=["activa"])
    assert tablero.usuario_puede_ver(sin_concesion)


@pytest.mark.django_db
def test_alias_resuelve_al_proxy_del_core_sin_saltar_la_politica():
    urlconf = ModuleType("urlconf_proxy_sintetico")
    urlconf.urlpatterns = [
        re_path(
            r"^(?P<path>celiaquia/.*)$",
            lambda request, path: None,
            name="backend_proxy_celiaquia_celiaquia",
        )
    ]
    tablero = Tablero.objects.create(
        nombre="Celiaquía", slug="celiaquia", ruta_interna="/celiaquia/tablero/"
    )
    ConfiguracionTableroInterno.objects.create(
        codigo="celiaquia", tablero=tablero, activa=True
    )
    alias = Tablero.objects.create(
        nombre="Alias", slug="alias-celiaquia", ruta_interna="/celiaquia/./tablero/"
    )
    usuario = User.objects.create_superuser(username="legacy", password="x")
    with override_settings(ROOT_URLCONF=urlconf):
        assert not alias.usuario_puede_ver(usuario)
        ConcesionTablero.objects.create(
            tablero=tablero, usuario=usuario, tipo="nacional"
        )
        assert alias.usuario_puede_ver(usuario)


@pytest.mark.django_db
def test_sidebar_consulta_configuraciones_una_vez_por_render():
    from dashboard.templatetags.dashboard_tags import tableros_para_sidebar

    usuario = User.objects.create_superuser(username="admin", password="x")
    for indice in range(11):
        Tablero.objects.create(nombre=f"Tablero {indice}", slug=f"tablero-{indice}")
    tablero = Tablero.objects.create(
        nombre="Celiaquía", slug="celiaquia", ruta_interna="/celiaquia/tablero/"
    )
    request = RequestFactory().get("/")
    request.user = usuario
    with CaptureQueriesContext(connection) as queries:
        assert len(tableros_para_sidebar({"request": request})) == 12
    consultas = [
        query
        for query in queries.captured_queries
        if "dashboard_configuraciontablerointerno" in query["sql"].lower()
    ]
    assert len(consultas) <= 2
    config = ConfiguracionTableroInterno.objects.create(
        codigo="celiaquia", tablero=tablero, activa=True
    )
    assert len(tableros_para_sidebar({"request": request})) == 11
    concesion = ConcesionTablero.objects.create(
        usuario=usuario, tablero=tablero, tipo="nacional"
    )
    assert len(tableros_para_sidebar({"request": request})) == 12
    concesion.delete()
    assert len(tableros_para_sidebar({"request": request})) == 11
    assert not tablero.usuario_puede_ver(usuario, configuracion=None)
    config.activa = False
    config.save(update_fields=["activa"])
    assert len(tableros_para_sidebar({"request": request})) == 12
    assert tablero.usuario_puede_ver(usuario, configuracion=None)


@pytest.mark.django_db
def test_revocacion_union_binding_y_cache():
    usuario = User.objects.create_user(username="persona")
    salta = Provincia.objects.create(nombre="Salta")
    jujuy = Provincia.objects.create(nombre="Jujuy")
    tablero = Tablero.objects.create(
        nombre="Celiaquia", slug="celiaquia", ruta_interna="/celiaquia/tablero/"
    )
    configuracion = ConfiguracionTableroInterno.objects.create(
        codigo="celiaquia", tablero=tablero, activa=True
    )
    audiencia = AudienciaTableros.objects.create(nombre="Audiencia")
    audiencia.agregar_miembro(usuario)
    ConcesionTablero.objects.create(
        usuario=usuario, tablero=tablero, tipo="provincia", provincia=salta
    )
    ConcesionTablero.objects.create(
        audiencia=audiencia, tablero=tablero, tipo="provincia", provincia=jujuy
    )
    cliente = Client()
    cliente.force_login(usuario)
    url = "/interno/tableros/celiaquia/alcance/"
    respuesta = cliente.get(url, {"usuario": 999, "nacional": "true"})
    assert respuesta.json() == {
        "estado": "provincial",
        "provincias": sorted([salta.pk, jujuy.pk]),
    }
    assert "no-store" in respuesta["Cache-Control"]
    assert "Cookie" in respuesta["Vary"]
    assert cliente.post(url).status_code == 405
    audiencia.quitar_miembro(usuario)
    assert cliente.get(url).json() == {"estado": "provincial", "provincias": [salta.pk]}
    tablero.activo = False
    tablero.save(update_fields=["activo"])
    assert cliente.get(url).status_code == 503
    assert cliente.head(url).status_code == 503
    configuracion.activa = False
    configuracion.save(update_fields=["activa"])
    assert cliente.get(url).json() == {"estado": "inactiva"}
    usuario.is_active = False
    usuario.save(update_fields=["is_active"])
    assert cliente.get(url).status_code == 403
