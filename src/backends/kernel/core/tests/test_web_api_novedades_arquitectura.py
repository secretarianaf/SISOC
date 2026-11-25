"""Novedades (T02.01) y mapa de arquitectura (T03) en JSON: mismo contexto que las vistas nativas."""

from datetime import datetime

import pytest
from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import Client
from django.utils import timezone

pytestmark = pytest.mark.django_db

CHANGELOG = (
    "## Despliegue: 2026.02.03\n### Added\n- Feature **A**\n\n"
    "## Despliegue: 2026.01.23\n### Fixed\n- Bug B\n"
)


@pytest.fixture(autouse=True)
def limpiar_cache():
    cache.clear()
    yield
    cache.clear()


def _cliente(username="nov_user"):
    user = User.objects.create_user(username=username, password="x")
    client = Client()
    client.force_login(user)
    return client


def test_anonimo_401():
    assert Client().get("/api/web/core/novedades/").status_code == 401
    assert Client().get("/api/web/core/arquitectura/").status_code == 401


def test_novedades_proyecta_el_contexto_de_la_vista_nativa(monkeypatch):
    monkeypatch.setattr(
        "core.web_api_novedades.fetch_changelog_content", lambda: CHANGELOG
    )
    cliente = _cliente()
    respuesta = cliente.get("/api/web/core/novedades/")
    datos = respuesta.json()
    assert respuesta.status_code == 200
    assert datos["error"] is False
    assert [v["version"] for v in datos["versions"]] == ["2026.02.03", "2026.01.23"]
    assert "<strong>A</strong>" in datos["versions"][0]["html"]
    assert datos["urls"]["architecture"] == "/arquitectura/"
    assert datos["messages"] == []
    assert "no-store" in respuesta["Cache-Control"]
    nativa = cliente.get("/novedades/")
    assert nativa.context["current_version"] == datos["current_version"]
    assert [v["version"] for v in nativa.context["versions"]] == [
        v["version"] for v in datos["versions"]
    ]


def test_novedades_cachea_y_no_vuelve_a_leer(monkeypatch):
    lecturas = []

    def leer():
        lecturas.append(1)
        return CHANGELOG

    monkeypatch.setattr("core.web_api_novedades.fetch_changelog_content", leer)
    cliente = _cliente()
    primera = cliente.get("/api/web/core/novedades/").json()
    segunda = cliente.get("/api/web/core/novedades/").json()
    assert len(lecturas) == 1
    assert primera["versions"] == segunda["versions"]
    assert cache.get("changelog_content")["versions"]


def test_novedades_sin_contenido_es_error_y_no_cachea(monkeypatch):
    monkeypatch.setattr("core.web_api_novedades.fetch_changelog_content", lambda: None)
    datos = _cliente().get("/api/web/core/novedades/").json()
    assert datos["error"] is True
    assert datos["versions"] == []
    assert cache.get("changelog_content") is None


def test_novedades_sin_bloques_de_version_no_se_cachea(monkeypatch):
    monkeypatch.setattr(
        "core.web_api_novedades.fetch_changelog_content", lambda: "texto sin cabeceras"
    )
    datos = _cliente().get("/api/web/core/novedades/").json()
    assert datos["error"] is True
    assert cache.get("changelog_content") is None


def test_arquitectura_sin_grafo(tmp_path, settings):
    settings.BASE_DIR = tmp_path
    datos = _cliente().get("/api/web/core/arquitectura/").json()
    assert datos["grafo_disponible"] is False
    assert datos["generado"] is None
    assert datos["urls"] == {"data": "/arquitectura/grafo.json", "back": "/novedades/"}


def test_arquitectura_con_grafo_informa_la_hora_y_no_lo_copia(tmp_path, settings):
    settings.BASE_DIR = tmp_path
    grafo = tmp_path / "var" / "arquitectura" / "grafo.json"
    grafo.parent.mkdir(parents=True)
    grafo.write_text('{"secreto": "estructura interna"}', encoding="utf-8")
    cliente = _cliente()
    respuesta = cliente.get("/api/web/core/arquitectura/")
    datos = respuesta.json()
    esperado = datetime.fromtimestamp(
        grafo.stat().st_mtime, tz=timezone.get_current_timezone()
    ).strftime("%d/%m/%Y %H:%M")
    assert datos["grafo_disponible"] is True
    assert datos["generado"] == esperado
    assert "estructura interna" not in respuesta.content.decode()
    nativa = cliente.get("/arquitectura/")
    assert nativa.context["generado"] == esperado
    assert nativa.context["grafo_disponible"] is True


def test_el_grafo_solo_se_entrega_con_sesion(tmp_path, settings):
    settings.BASE_DIR = tmp_path
    grafo = tmp_path / "var" / "arquitectura" / "grafo.json"
    grafo.parent.mkdir(parents=True)
    grafo.write_text("{}", encoding="utf-8")
    assert Client().get("/arquitectura/grafo.json").status_code == 302
    assert _cliente().get("/arquitectura/grafo.json").status_code == 200
