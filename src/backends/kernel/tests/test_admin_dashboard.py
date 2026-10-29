"""Issue #2789, Fase 3: dashboard del admin con métricas por dominio."""

import json
from importlib import import_module

import pytest
from django.apps import apps
from django.contrib.auth.models import User
from django.core.cache import cache
from django.urls import reverse

from core import admin_dashboard
from core.admin_dashboard import altas_por_mes, contar_por, secciones_de_app


@pytest.fixture(autouse=True)
def cache_limpio():
    cache.clear()
    yield
    cache.clear()


def _apps_con_metricas():
    con_metricas = []
    for app_config in apps.get_app_configs():
        try:
            import_module(f"{app_config.name}.{admin_dashboard.MODULO_METRICAS}")
        except ModuleNotFoundError:
            continue
        con_metricas.append(app_config.label)
    return con_metricas


def test_cada_dominio_aporta_metricas():
    assert {
        "users",
        "ciudadanos",
        "audittrail",
        "encuestas",
        "comedores",
        "relevamientos",
        "admisiones",
        "rendicioncuentasmensual",
        "celiaquia",
        "centrodeinfancia",
        "centrodefamilia",
        "VAT",
        "ver_para_ser_libre",
        "pas",
        "inspecciones",
        "datacalle",
        "ocr",
    } <= set(_apps_con_metricas())


@pytest.mark.django_db
@pytest.mark.parametrize("app_label", _apps_con_metricas())
def test_metricas_no_rompen_con_la_base_vacia(app_label):
    secciones = secciones_de_app(app_label)

    assert secciones
    assert not any(seccion["error"] for seccion in secciones)
    for seccion in secciones:
        for grafico in seccion["graficos"]:
            json.loads(grafico["datos_json"])


@pytest.mark.django_db
def test_dashboard_carga_con_la_base_vacia(auth_client):
    response = auth_client.get(reverse("admin:index"))

    assert response.status_code == 200
    html = response.content.decode()
    assert "sisoc-dashboard-seccion" in html
    assert "Usuarios" in html
    assert "Celiaquía" in html


@pytest.mark.django_db
def test_indice_de_app_muestra_solo_sus_metricas(auth_client):
    response = auth_client.get(reverse("admin:app_list", args=["celiaquia"]))

    assert response.status_code == 200
    titulos = [s["titulo"] for s in response.context["sisoc_secciones"]]
    assert titulos == ["Celiaquía"]


@pytest.mark.django_db
def test_metricas_reflejan_los_datos_y_se_cachean(django_assert_num_queries):
    User.objects.create_user(username="a", is_active=True)
    User.objects.create_user(username="b", is_active=False)

    secciones = secciones_de_app("users")
    with django_assert_num_queries(0):
        cacheadas = secciones_de_app("users")

    kpis = {kpi["titulo"]: kpi["valor"] for kpi in secciones[0]["kpis"]}
    assert kpis["Usuarios activos"] == 1
    assert cacheadas == secciones


@pytest.mark.django_db
def test_una_seccion_rota_no_tira_el_dashboard(auth_client, monkeypatch):
    def romper():
        raise RuntimeError("consulta rota")

    monkeypatch.setattr("ciudadanos.admin_metricas.metricas", romper)

    response = auth_client.get(reverse("admin:index"))

    assert response.status_code == 200
    rotas = [s for s in response.context["sisoc_secciones"] if s["error"]]
    assert [s["titulo"] for s in rotas] == ["Ciudadanos"]
    assert "No se pudieron calcular estas métricas" in response.content.decode()


@pytest.mark.django_db
def test_contar_por_usa_las_etiquetas_de_los_choices():
    User.objects.create_user(username="x", is_active=True)
    User.objects.create_user(username="y", is_active=True)
    User.objects.create_user(username="z", is_active=False)

    grafico = contar_por(User.objects.all(), "is_active", "Activos")

    assert dict(zip(grafico.etiquetas, grafico.series[0][1])) == {True: 2, False: 1}


@pytest.mark.django_db
def test_altas_por_mes_agrupa_por_mes():
    User.objects.create_user(username="m1")
    User.objects.create_user(username="m2")

    grafico = altas_por_mes(User.objects.all(), "date_joined", "Altas")

    assert grafico.tipo == "line"
    assert grafico.series[0][1] == [2]
    assert len(grafico.etiquetas) == 1


@pytest.mark.django_db
def test_dashboard_usa_consultas_agregadas(auth_client, django_assert_max_num_queries):
    for indice in range(30):
        User.objects.create_user(username=f"u{indice}")
    auth_client.get(reverse("admin:index"))  # calienta la caché

    # Con la caché caliente, el índice no recalcula las métricas.
    with django_assert_max_num_queries(25):
        response = auth_client.get(reverse("admin:index"))

    assert response.status_code == 200
