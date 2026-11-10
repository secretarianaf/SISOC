from pathlib import Path

import pytest
from django.core.exceptions import ValidationError
from django.db import connection
from django.test import RequestFactory
from django.test.utils import CaptureQueriesContext

import dashboard
from dashboard.admin import TableroAdminForm
from dashboard.apps import DashboardConfig
from dashboard.models import Tablero
from dashboard.templatetags.dashboard_tags import tableros_para_sidebar


def _request_para(user, path="/"):
    request = RequestFactory().get(path)
    request.user = user
    return request


def test_dashboard_ready_no_consulta_la_base(db):
    app_config = DashboardConfig("dashboard", dashboard)

    with CaptureQueriesContext(connection) as queries:
        app_config.ready()

    assert len(queries) == 0


def test_tablero_convierte_url_compartible_de_lookerstudio_a_embed():
    tablero = Tablero(
        nombre="FCH Google Analytics",
        slug="fch-google-analytics",
        url=(
            "https://lookerstudio.google.com/u/0/reporting/"
            "7feb7647-eadb-4fd8-910d-11a794227234"
        ),
    )

    assert tablero.usa_url_compartible_looker_studio() is True
    assert (
        tablero.get_embed_url() == "https://lookerstudio.google.com/embed/reporting/"
        "7feb7647-eadb-4fd8-910d-11a794227234"
    )


def test_dashboard_tablero_renderiza_iframe_con_url_embed_de_lookerstudio(
    admin_client,
):
    tablero = Tablero.objects.create(
        nombre="FCH Google Analytics",
        slug="fch-google-analytics",
        url=(
            "https://lookerstudio.google.com/u/0/reporting/"
            "7feb7647-eadb-4fd8-910d-11a794227234"
        ),
        activo=True,
        permisos=["dashboard.view_dashboard"],
    )

    response = admin_client.get(tablero.get_absolute_url())
    content = response.content.decode()

    assert f'src="{tablero.get_embed_url()}"' in content
    assert 'target="_blank"' in content
    assert "File &gt; Embed report" in content


def test_tableros_para_sidebar_agrupa_por_grupo_menu(db, django_user_model):
    admin = django_user_model.objects.create_superuser(
        "admin_tab", "admin_tab@example.com", "x"
    )
    Tablero.objects.create(
        nombre="Aduana", slug="aduana", grupo_menu="Aduana", orden=1, activo=True
    )
    Tablero.objects.create(
        nombre="Aduana Ejecutivo",
        slug="aduana-ejecutivo",
        grupo_menu="Aduana",
        orden=2,
        activo=True,
    )
    suelto = Tablero.objects.create(
        nombre="Prestación Alimentar", slug="prestacion", orden=3, activo=True
    )

    items = tableros_para_sidebar({"request": _request_para(admin)})

    assert [item["tipo"] for item in items] == ["grupo", "single"]
    grupo = items[0]
    assert grupo["nombre"] == "Aduana"
    assert [hijo["nombre"] for hijo in grupo["hijos"]] == ["Aduana", "Aduana Ejecutivo"]
    assert items[1]["nombre"] == "Prestación Alimentar"
    assert items[1]["url"] == suelto.get_absolute_url()


def test_tableros_para_sidebar_ancla_grupo_en_primer_miembro(db, django_user_model):
    admin = django_user_model.objects.create_superuser(
        "admin_tab_intercalado", "admin_tab_intercalado@example.com", "x"
    )
    Tablero.objects.create(
        nombre="G1 Primero",
        slug="g1-primero",
        grupo_menu="G1",
        orden=1,
        activo=True,
    )
    Tablero.objects.create(nombre="S1", slug="s1", orden=2, activo=True)
    Tablero.objects.create(nombre="S2", slug="s2", orden=3, activo=True)
    Tablero.objects.create(
        nombre="G1 Segundo",
        slug="g1-segundo",
        grupo_menu="G1",
        orden=4,
        activo=True,
    )

    items = tableros_para_sidebar({"request": _request_para(admin)})

    assert [item["nombre"] for item in items] == ["G1", "S1", "S2"]
    grupo = items[0]
    assert grupo["tipo"] == "grupo"
    assert [hijo["nombre"] for hijo in grupo["hijos"]] == [
        "G1 Primero",
        "G1 Segundo",
    ]


def test_tableros_para_sidebar_colapsa_grupo_de_un_solo_tablero(db, django_user_model):
    admin = django_user_model.objects.create_superuser(
        "admin_tab2", "admin_tab2@example.com", "x"
    )
    Tablero.objects.create(
        nombre="Solo", slug="solo", grupo_menu="Programa X", orden=1, activo=True
    )

    items = tableros_para_sidebar({"request": _request_para(admin)})

    assert len(items) == 1
    assert items[0]["tipo"] == "single"
    assert items[0]["nombre"] == "Solo"


def test_tableros_para_sidebar_marca_activo_por_path(db, django_user_model):
    admin = django_user_model.objects.create_superuser(
        "admin_tab3", "admin_tab3@example.com", "x"
    )
    tablero = Tablero.objects.create(
        nombre="Comedores Interno", slug="comedores-interno", orden=1, activo=True
    )

    items = tableros_para_sidebar(
        {"request": _request_para(admin, tablero.get_absolute_url())}
    )

    assert items[0]["activo"] is True


def test_tablero_con_ruta_interna_enlaza_a_la_pantalla_de_sisoc():
    con_ruta = Tablero(
        nombre="Celiaquía Seguimiento",
        slug="celiaquia-seguimiento",
        ruta_interna="/celiaquia/tablero/",
    )
    sin_ruta = Tablero(nombre="Aduana", slug="aduana")

    assert con_ruta.get_absolute_url() == "/celiaquia/tablero/"
    assert sin_ruta.get_absolute_url() == "/dashboard/aduana/"


def test_tableros_para_sidebar_usa_ruta_interna_y_marca_activo(db, django_user_model):
    admin = django_user_model.objects.create_superuser(
        "admin_tab4", "admin_tab4@example.com", "x"
    )
    Tablero.objects.create(
        nombre="Celiaquía Seguimiento",
        slug="celiaquia-seguimiento",
        ruta_interna="/celiaquia/tablero/",
        orden=1,
        activo=True,
    )

    items = tableros_para_sidebar(
        {"request": _request_para(admin, "/celiaquia/tablero/")}
    )

    assert items[0]["url"] == "/celiaquia/tablero/"
    assert items[0]["activo"] is True


def test_dashboard_tablero_con_ruta_interna_redirige_a_la_pantalla(admin_client):
    Tablero.objects.create(
        nombre="Celiaquía Seguimiento",
        slug="celiaquia-seguimiento",
        ruta_interna="/celiaquia/tablero/",
        activo=True,
    )

    response = admin_client.get("/dashboard/celiaquia-seguimiento/")

    assert response.status_code == 302
    assert response["Location"] == "/celiaquia/tablero/"


def test_dashboard_tablero_con_ruta_interna_sin_permiso_no_redirige(
    client, django_user_model
):
    usuario = django_user_model.objects.create_user("sin_permiso_tab", password="x")
    Tablero.objects.create(
        nombre="Celiaquía Seguimiento",
        slug="celiaquia-seguimiento",
        ruta_interna="/celiaquia/tablero/",
        activo=True,
        permisos=["dashboard.view_dashboard"],
    )
    client.force_login(usuario)

    response = client.get("/dashboard/celiaquia-seguimiento/")

    assert response.status_code == 403


@pytest.mark.parametrize(
    "ruta",
    [
        "https://otro-sitio.com/",
        "//otro-sitio.com/",
        "/\\otro-sitio.com",
        "celiaquia/tablero/",
        "/celiaquia/ tablero/",
    ],
)
def test_ruta_interna_rechaza_rutas_externas_o_mal_formadas(ruta):
    tablero = Tablero(nombre="X", slug="x", ruta_interna=ruta)

    with pytest.raises(ValidationError) as error:
        tablero.clean_fields()

    assert "ruta_interna" in error.value.message_dict


def test_ruta_interna_acepta_ruta_de_sisoc():
    tablero = Tablero(nombre="X", slug="x", ruta_interna="/celiaquia/tablero/")

    tablero.clean_fields()


def test_admin_form_rechaza_ruta_interna_externa(db):
    form = TableroAdminForm(
        data={
            "nombre": "X",
            "slug": "x",
            "ruta_interna": "https://otro-sitio.com/",
            "orden": 0,
            "activo": True,
        }
    )

    assert form.is_valid() is False
    assert "ruta_interna" in form.errors
