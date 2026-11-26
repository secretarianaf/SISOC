"""Independent HTTP regressions for the canonical CDI Calidad and RM01 routes."""

from types import ModuleType

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import Client, override_settings
from django.urls import resolve, reverse

from centrodeinfancia.models import AccesoCDI, CentroDeInfancia, FormularioCalidadCDI
from centrodeinfancia.web_preview import cdi_preview_patterns
from comedores.models import Comedor
from config.urls_all import urlpatterns
from core.constants import UserGroups
from core.react_activation import react_preview_patterns
from rendicioncuentasmensual.models import RendicionCuentaMensual
from rendicioncuentasmensual.web_preview import rendicion_preview_patterns
from users.services_group_permissions import sync_permissions_for_group

pytestmark = pytest.mark.django_db

SHELL = b"<html><main>Canonical route test build</main></html>"
FORM = "application/x-www-form-urlencoded"
CDI_HTML = "/centrodeinfancia/{center}/calidad/"
CDI_API = "/api/web/cdi/centros/{center}/calidad/"
RM_HTML = "/rendicioncuentasmensual/rendicioncuentasmensual/{comedor}/"
RM_API = "/api/web/comedores/rendicioncuentasmensual/por-comedor/{comedor}/"


@pytest.fixture
def synthetic_build(tmp_path):
    (tmp_path / "index.html").write_bytes(SHELL)
    return tmp_path


def _urlconf(overrides):
    urlconf = ModuleType("canonical_t5_test_urls")
    urlconf.urlpatterns = [*overrides, *urlpatterns]
    return urlconf


def _user(name, *, role=None, permission=None):
    user = get_user_model().objects.create_user(name)
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    if role:
        group, _ = Group.objects.get_or_create(name=role)
        sync_permissions_for_group(group)
        user.groups.add(group)
    if permission:
        app_label, codename = permission.split(".", 1)
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label=app_label, codename=codename)
        )
    return user


def _center_user(center):
    user = _user("cdi-canonical-referente", role=UserGroups.CDI_REFERENTE_CENTRO)
    AccesoCDI.objects.create(user=user, centro=center)
    return user


def _quality_rows():
    return list(FormularioCalidadCDI.objects.order_by("pk").values())


def test_cdi_rejected_writes_keep_the_original_draft_and_other_center_unchanged():
    center = CentroDeInfancia.objects.create(nombre="Centro autorizado")
    outside = CentroDeInfancia.objects.create(nombre="Otro centro")
    draft = FormularioCalidadCDI.objects.create(centro=center, p1_inf_tenencia_tipo=1)
    outside_form = FormularioCalidadCDI.objects.create(
        centro=outside, p1_inf_tenencia_tipo=2
    )
    client = Client(enforce_csrf_checks=True)
    client.force_login(_center_user(center))
    entry = f"{CDI_API.format(center=center.pk)}cargar/"
    outside_entry = f"{CDI_API.format(center=outside.pk)}cargar/"
    csrf = client.get(entry).cookies["csrftoken"].value
    csrf_headers = {"HTTP_X_CSRFTOKEN": csrf}
    original = _quality_rows()

    cases = [
        (entry, "accion=guardar&p1_inf_tenencia_tipo=2", FORM, {}, 403),
        (entry, "accion=guardar&p17_esp_sup_lact=99999", FORM, csrf_headers, 400),
        (
            outside_entry,
            "accion=guardar&p1_inf_tenencia_tipo=1",
            FORM,
            csrf_headers,
            404,
        ),
        (entry, '{"accion":"guardar"}', "application/json", csrf_headers, 415),
    ]
    for url, body, content_type, headers, status_code in cases:
        result = client.post(url, body, content_type=content_type, **headers)
        assert result.status_code == status_code
        assert _quality_rows() == original

    saved = client.post(
        entry,
        "accion=guardar&p1_inf_tenencia_tipo=2",
        content_type=FORM,
        **csrf_headers,
    )
    assert saved.status_code == 200
    assert saved.json()["redirect"] == reverse(
        "centrodeinfancia_detalle", args=[center.pk]
    )
    assert FormularioCalidadCDI.objects.count() == 2
    outside_form.refresh_from_db()
    draft.refresh_from_db()
    assert outside_form.p1_inf_tenencia_tipo == 2
    assert draft.p1_inf_tenencia_tipo == 2


def test_cdi_html_and_json_enforce_center_scope_draft_privacy_and_page_bounds(
    synthetic_build,
):
    center = CentroDeInfancia.objects.create(nombre="Centro autorizado")
    outside = CentroDeInfancia.objects.create(nombre="Otro centro")
    draft = FormularioCalidadCDI.objects.create(centro=center)
    outside_form = FormularioCalidadCDI.objects.create(centro=outside, estado="enviado")
    client = Client()
    client.force_login(_center_user(center))

    with override_settings(
        ROOT_URLCONF=_urlconf(cdi_preview_patterns(synthetic_build))
    ):
        for pattern in (CDI_HTML, CDI_API):
            inside_url = pattern.format(center=center.pk)
            outside_url = pattern.format(center=outside.pk)
            for form in (draft, outside_form):
                assert client.get(f"{inside_url}{form.pk}/").status_code == 404
            for suffix in ("", "cargar/"):
                assert client.get(f"{outside_url}{suffix}").status_code == 404
            for page in ("0", "-1", "bogus", "9999"):
                assert client.get(inside_url, {"page": page}).status_code == 404

        assert client.get(CDI_HTML.format(center=center.pk)).content == SHELL


def test_rm01_list_is_read_only_and_stage_role_has_no_write_links(synthetic_build):
    comedor = Comedor.objects.create(nombre="Comedor autorizado")
    RendicionCuentaMensual.objects.create(comedor=comedor, mes=1, anio=2026)
    client = Client()
    client.force_login(
        _user(
            "rm01-canonical-stage",
            permission="rendicioncuentasmensual.manage_territorial_stage",
        )
    )
    api = RM_API.format(comedor=comedor.pk)
    html = RM_HTML.format(comedor=comedor.pk)
    original = list(RendicionCuentaMensual.objects.order_by("pk").values())

    with override_settings(
        ROOT_URLCONF=_urlconf(rendicion_preview_patterns(synthetic_build))
    ):
        result = client.get(api)
        assert result.status_code == 200
        payload = result.json()
        assert payload["back_url"] == reverse(
            "detalle_acompanamiento", args=[comedor.pk]
        )
        assert payload["new_url"] is None
        assert payload["rows"][0]["edit_url"] is None
        assert payload["rows"][0]["delete_url"] is None

        for method in ("post", "put", "patch", "delete"):
            assert getattr(client, method)(api).status_code == 405
        assert list(RendicionCuentaMensual.objects.order_by("pk").values()) == original
        assert client.get(html).content == SHELL

        denied = Client()
        denied.force_login(_user("rm01-canonical-denied"))
        assert denied.get(api).status_code == 403
        assert denied.get(html).status_code == 403


def test_t5_entries_follow_activation_and_keep_all_registered_api_destinations(
    synthetic_build, settings
):
    center = CentroDeInfancia.objects.create(nombre="Centro de prueba")
    form = FormularioCalidadCDI.objects.create(centro=center)
    comedor = Comedor.objects.create(nombre="Comedor de prueba")
    cdi_path = CDI_HTML.format(center=center.pk)
    canonical_entries = [
        (cdi_path, "CalidadHistorialEntry", "cdi"),
        (f"{cdi_path}cargar/", "CalidadCargarEntry", "cdi"),
        (f"{cdi_path}{form.pk}/", "CalidadDetalleEntry", "cdi"),
        (RM_HTML.format(comedor=comedor.pk), "PorComedorEntry", "comedores"),
    ]
    api_names = [
        ("centrodeinfancia_web_calidad_listado", [center.pk]),
        ("centrodeinfancia_web_calidad_cargar", [center.pk]),
        ("centrodeinfancia_web_calidad_detalle", [center.pk, form.pk]),
        ("rendicioncuentasmensual_web_por_comedor", [comedor.pk]),
    ]

    settings.SISOC_REACT_BUILD_DIR = str(synthetic_build)
    for keys in (("cdi",), ("comedores",), ("todas",)):
        settings.REACT_VERTICALES_ACTIVAS = keys
        overrides = react_preview_patterns("cdi", "comedores")
        with override_settings(ROOT_URLCONF=_urlconf(overrides)):
            for path, entry, vertical in canonical_entries:
                if vertical in keys or keys == ("todas",):
                    assert resolve(path).func.view_class.__name__ == entry
            for name, args in api_names:
                assert resolve(reverse(name, args=args)).url_name == name

    settings.REACT_VERTICALES_ACTIVAS = ("ninguna",)
    assert react_preview_patterns("cdi", "comedores") == []
    settings.REACT_VERTICALES_ACTIVAS = ("todas",)
    settings.SISOC_REACT_BUILD_DIR = str(synthetic_build / "absent")
    assert react_preview_patterns("cdi", "comedores") == []
