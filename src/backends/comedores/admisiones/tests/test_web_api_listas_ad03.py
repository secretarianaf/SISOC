"""Web API (G1 v1) of the technical and legal admision lists (AD03.01)."""

import types

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, override_settings
from django.urls import reverse

from admisiones.models.admisiones import Admision
from admisiones.web_preview_seguimiento import seguimiento_preview_patterns
from comedores.models import Comedor
from config.urls_all import urlpatterns as monolith_patterns

API = "/api/web/comedores/admisiones/"
PERMISOS = (
    "comedores.view_comedor",
    "admisiones.view_admision",
    "acompanamientos.view_informacionrelevante",
)

pytestmark = pytest.mark.django_db


def _usuario(nombre, permiso=None, superuser=False):
    usuario = get_user_model().objects.create_user(nombre)
    perfil = usuario.profile
    perfil.acceso_web = True
    perfil.must_change_password = False
    perfil.needs_profile_confirmation = False
    perfil.save()
    if permiso:
        app, codigo = permiso.split(".")
        usuario.user_permissions.add(
            Permission.objects.get(content_type__app_label=app, codename=codigo)
        )
    if superuser:
        usuario.is_superuser = True
        usuario.save()
    return usuario


def _cliente(usuario):
    client = Client()
    client.force_login(usuario)
    return client


@pytest.fixture(name="admision")
def admision_fixture():
    comedor = Comedor.objects.create(nombre="Comedor Lista AD03")
    return Admision.objects.create(
        comedor=comedor, tipo="incorporacion", num_expediente="EX-1", convenio_numero=3
    )


def test_technical_list_projects_the_native_rows(admision):
    web = _cliente(_usuario("root_tec", superuser=True))

    datos = web.get(f"{API}tecnicos/").json()

    assert datos["title"] == "Admisiones - Equipos técnicos"
    assert [h["title"] for h in datos["headers"]][:3] == [
        "ID Comedor",
        "Tipo",
        "Nombre",
    ]
    fila = datos["results"][0]
    celdas = [c["content"] for c in fila["cells"]]
    assert celdas[0] == str(admision.comedor_id)
    assert celdas[2] == "Comedor Lista AD03"
    assert fila["cells"][2]["link_url"] == reverse(
        "comedor_detalle", args=[admision.comedor_id]
    )
    assert celdas[4:6] == ["EX-1", "3°"]
    assert fila["actions"] == [
        {
            "label": "Ver",
            "badge": None,
            "url": f"/comedores/admisiones/tecnicos/editar/{admision.pk}",
            "type": "warning",
        }
    ]
    assert datos["page"]["count"] == 1
    assert datos["favorites"]["section"]
    assert datos["filters_config"]["fields"]


def test_technical_badge_is_data_not_markup(admision):
    Admision.objects.filter(pk=admision.pk).update(estado_legales="A Rectificar")
    web = _cliente(_usuario("root_badge", superuser=True))

    accion = web.get(f"{API}tecnicos/").json()["results"][0]["actions"][0]

    assert (accion["label"], accion["badge"]) == ("Ver", "Rectificar")


def test_technical_list_scope_excludes_archived_and_inactive(admision):
    otro = Admision.objects.create(
        comedor=Comedor.objects.create(nombre="Archivada"), enviada_a_archivo=True
    )
    web = _cliente(_usuario("root_scope", superuser=True))

    datos = web.get(f"{API}tecnicos/").json()

    assert datos["page"]["count"] == 1
    assert otro.comedor.nombre not in str(datos["results"])


def test_legal_list_only_shows_sent_to_legales_and_links_to_the_native_detail(admision):
    Admision.objects.filter(pk=admision.pk).update(
        enviado_legales=True, estado_legales="Enviado a Legales"
    )
    Admision.objects.create(comedor=Comedor.objects.create(nombre="No enviada"))
    web = _cliente(_usuario("lector_leg", "comedores.view_comedor"))

    datos = web.get(f"{API}legales/").json()

    assert datos["title"] == "Expedientes - Legales"
    assert datos["page"]["count"] == 1
    fila = datos["results"][0]
    assert fila["cells"][8]["content"] == "Enviado a Legales"
    assert fila["actions"] == [
        {
            "label": "Ver",
            "badge": None,
            "url": f"/comedores/admisiones/legales/ver/{admision.pk}",
            "type": "primary",
        }
    ]


def test_ordering_and_pagination_come_from_the_native_view(admision):
    for numero in range(11):
        Admision.objects.create(comedor=Comedor.objects.create(nombre=f"C{numero:02}"))
    web = _cliente(_usuario("root_pag", superuser=True))

    primera = web.get(f"{API}tecnicos/").json()
    segunda = web.get(f"{API}tecnicos/?page=2&comedor_nombre=C").json()

    assert (primera["page"]["count"], len(primera["results"])) == (12, 10)
    assert primera["page"]["next"] == 2
    nombre = next(h for h in primera["headers"] if h["title"] == "Nombre")
    assert nombre["sort_url"]
    assert segunda["page"]["number"] == 2
    assert web.get(f"{API}tecnicos/?page=99").status_code == 404


def test_access_is_the_native_guard_per_list(admision):
    assert Client().get(f"{API}tecnicos/").status_code in (401, 403)
    assert _cliente(_usuario("sin_permiso_l")).get(f"{API}tecnicos/").status_code == 403
    for permiso in PERMISOS:
        web = _cliente(_usuario(f"u_{permiso.split('.')[1]}", permiso))
        assert web.get(f"{API}tecnicos/").status_code == 200, permiso
        assert web.get(f"{API}legales/").status_code == 200, permiso
    pagos = _cliente(_usuario("solo_pagos", "expedientespagos.view_expedientepago"))
    assert pagos.get(f"{API}legales/").status_code == 200
    # The technical list has no expedientes-de-pago clause.
    assert pagos.get(f"{API}tecnicos/").status_code == 403
    assert (
        _cliente(_usuario("w", PERMISOS[0])).post(f"{API}tecnicos/").status_code == 405
    )


INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)


@pytest.fixture(name="preview")
def preview_fixture(tmp_path):
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    module = types.ModuleType("seguimiento_preview_test_urls")
    module.urlpatterns = seguimiento_preview_patterns(tmp_path) + list(
        monolith_patterns
    )
    with override_settings(ROOT_URLCONF=module):
        yield


@pytest.mark.usefixtures("preview")
def test_preview_serves_the_index_after_the_native_guards(admision):
    web = _cliente(_usuario("lector_prev", "comedores.view_comedor"))

    for url in (
        "/comedores/admisiones/tecnicos/listar",
        "/comedores/admisiones/legales/listar",
    ):
        respuesta = web.get(url)
        assert respuesta.status_code == 200
        assert '/comedores/react/assets/app-1.js"' in respuesta.content.decode()
        assert "csrftoken" in respuesta.cookies
        assert Client().get(url).status_code in (302, 403)
        assert _cliente(_usuario(f"sin_{url[-12:]}")).get(url).status_code == 403
        assert web.get(f"{url}?page=99").status_code == 404


def test_preview_requires_an_index(tmp_path):
    with pytest.raises(ValueError):
        seguimiento_preview_patterns(tmp_path)
