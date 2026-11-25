"""Canonical React entry and web contract for the per-comedor list."""

import types

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, override_settings
from django.urls import reverse

from comedores.models import Comedor
from config.urls_all import urlpatterns as native_patterns
from core.web_gate import DETAIL_UNAUTHENTICATED
from organizaciones.models import Organizacion, ProyectoOrganizacion
from rendicioncuentasmensual.models import RendicionCuentaMensual
from rendicioncuentasmensual.web_preview import rendicion_preview_patterns

pytestmark = pytest.mark.django_db

INDEX = '<!doctype html><html><body><div id="root"></div></body></html>'
PREFIX = "/rendicioncuentasmensual/rendicioncuentasmensual/"
API = "/api/web/comedores/rendicioncuentasmensual/por-comedor/"


def _login(*codes):
    user = get_user_model().objects.create_user(f"rm01_{'_'.join(codes)}")
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    for code in codes:
        user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="rendicioncuentasmensual", codename=code
            )
        )
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture(name="preview")
def preview_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    module = types.ModuleType("rendicion_por_comedor_preview_test_urls")
    module.urlpatterns = rendicion_preview_patterns(tmp_path) + list(native_patterns)
    with override_settings(ROOT_URLCONF=module):
        yield


@pytest.fixture(name="comedor")
def comedor_fixture():
    return Comedor.objects.create(nombre="Comedor de prueba")


@pytest.mark.usefixtures("preview")
def test_native_per_comedor_url_loads_react_after_the_existing_guard(comedor):
    path = f"{PREFIX}{comedor.pk}/"
    client = _login("manage_territorial_stage")

    result = client.get(path)
    assert result.status_code == 200
    assert result.content.decode() == INDEX
    assert "no-store" in result["Cache-Control"]
    assert client.get(f"{path}?page=invalid").status_code == 404
    assert client.get(f"{PREFIX}{comedor.pk + 1000}/").status_code == 404
    assert Client().get(path).status_code == 403
    assert _login().get(path).status_code == 403


def test_native_list_remains_available_without_preview(comedor):
    client = _login("view_rendicioncuentamensual")
    result = client.get(f"{PREFIX}{comedor.pk}/")
    assert result.status_code == 200
    assert "Nuevo seguimiento mensual" in result.content.decode()
    assert result.templates[0].name == "rendicioncuentasmensual_list.html"


def test_api_preserves_native_rows_and_destination_links(comedor):
    organization = Organizacion.objects.create(nombre="Organización de prueba")
    project = ProyectoOrganizacion.objects.create(
        organizacion=organization, codigo="PRUEBA-RM01"
    )
    Comedor.objects.filter(pk=comedor.pk).update(
        organizacion=organization, proyecto=project
    )
    sibling = Comedor.objects.create(
        nombre="Comedor del mismo proyecto", organizacion=organization, proyecto=project
    )
    other = Comedor.objects.create(nombre="Comedor no relacionado")
    a = RendicionCuentaMensual.objects.create(
        comedor=comedor, mes=3, anio=2026, observaciones="Revisión <pendiente>"
    )
    b = RendicionCuentaMensual.objects.create(comedor=comedor, mes=5, anio=2026)
    same_project = RendicionCuentaMensual.objects.create(
        comedor=sibling, proyecto=project, mes=6, anio=2026
    )
    excluded = RendicionCuentaMensual.objects.create(comedor=comedor, mes=7, anio=2026)
    excluded.delete()
    RendicionCuentaMensual.objects.create(comedor=other, mes=8, anio=2026)
    client = _login("view_rendicioncuentamensual", "edit_rendicion_data")
    path = f"{API}{comedor.pk}/"

    result = client.get(path)
    assert result.status_code == 200
    native = client.get(f"{PREFIX}{comedor.pk}/")
    rows = result.json()["rows"]
    assert [row["id"] for row in rows] == [
        row.pk for row in native.context["rendiciones_cuentas_mensuales"]
    ]
    assert {row["id"] for row in rows} == {a.pk, b.pk, same_project.pk}
    row = next(row for row in rows if row["id"] == a.pk)
    assert row == {
        "id": a.pk,
        "mes": 3,
        "anio": 2026,
        "observaciones": "Revisión <pendiente>",
        "detail_url": f"{PREFIX}detalle/{a.pk}/",
        "edit_url": f"{PREFIX}editar/{a.pk}/",
        "delete_url": f"{PREFIX}eliminar/{a.pk}/",
    }
    assert result.json()["comedor"] == "Comedor de prueba"
    assert result.json()["new_url"] == f"{PREFIX}nuevo/{comedor.pk}/"
    assert result.json()["back_url"] == reverse(
        "detalle_acompanamiento", args=[comedor.pk]
    )
    assert "no-store" in result["Cache-Control"]
    assert client.get(f"{path}?page=invalid").status_code == 404
    assert client.get(f"{API}{comedor.pk + 1000}/").status_code == 404
    assert client.post(path).status_code == 405


def test_stage_access_does_not_offer_mutations_and_json_checks_access(comedor):
    RendicionCuentaMensual.objects.create(comedor=comedor, mes=3, anio=2026)
    path = f"{API}{comedor.pk}/"
    result = _login("manage_territorial_stage").get(path)
    assert result.status_code == 200
    payload = result.json()
    assert payload["new_url"] is None
    assert payload["rows"][0]["detail_url"]
    assert payload["rows"][0]["edit_url"] is None
    assert payload["rows"][0]["delete_url"] is None
    anonymous = Client().get(path)
    assert anonymous.status_code == 401
    assert anonymous.json() == {"detail": DETAIL_UNAUTHENTICATED}
    assert _login().get(path).status_code == 403

    # The native edit destination has a separate dispatch permission.
    view_only = _login("view_rendicioncuentamensual").get(path).json()
    assert view_only["new_url"]
    assert view_only["rows"][0]["delete_url"]
    assert view_only["rows"][0]["edit_url"] is None
