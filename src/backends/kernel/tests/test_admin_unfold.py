"""Issue #2789: admin con Django Unfold, solo para superusuarios."""

import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.test import RequestFactory, override_settings
from django.urls import reverse

from config.backends import load_backends_registry
from core.admin_navigation import (
    badge_entorno,
    enlaces_admin_de_backends,
    dominio_de_app,
    navegacion_sidebar,
    prefijo_titulo_entorno,
)
from core.admin_site import SisocAdminSite, puede_usar_admin


@pytest.fixture(name="staff")
def staff_fixture(db):
    return get_user_model().objects.create_user(
        username="staff_no_super", password="x", is_staff=True
    )


def test_el_sitio_por_defecto_es_el_de_sisoc():
    assert isinstance(admin.site, SisocAdminSite)


@pytest.mark.django_db
def test_staff_sin_superusuario_no_entra_al_admin(client, staff):
    client.force_login(staff)

    response = client.get(reverse("admin:index"))

    assert response.status_code == 302
    assert response.url.startswith(reverse("admin:login"))


@pytest.mark.django_db
def test_anonimo_no_entra_al_admin(client):
    response = client.get(reverse("admin:index"))

    assert response.status_code == 302
    assert response.url.startswith(reverse("admin:login"))


@pytest.mark.django_db
def test_superusuario_inactivo_no_entra(staff):
    staff.is_superuser = True
    staff.is_active = False

    assert not puede_usar_admin(staff)


@pytest.mark.django_db
def test_superusuario_ve_el_admin_con_unfold_y_badge(auth_client, settings):
    settings.ENVIRONMENT = "homologacion"

    response = auth_client.get(reverse("admin:index"))

    assert response.status_code == 200
    html = response.content.decode()
    assert "unfold/css/styles.css" in html
    assert "Homologación" in html
    assert "<title>[Homologación]" in html


@pytest.mark.django_db
def test_admindocs_solo_para_superusuarios(client, staff, superuser):
    url = reverse("django-admindocs-docroot")

    client.force_login(staff)
    denegado = client.get(url)
    client.force_login(superuser)
    permitido = client.get(url)

    assert denegado.status_code == 302
    assert denegado.url.startswith(reverse("admin:login"))
    assert permitido.status_code == 200


@pytest.mark.django_db
def test_ruta_legacy_de_auditoria_pwa_sigue_funcionando(auth_client):
    response = auth_client.get("/admin/pwa/auditoriasesionpwa/", follow=True)

    assert response.status_code == 200
    assert response.redirect_chain[-1][0] == reverse(
        "admin:audittrail_auditoriasesionpwa_changelist"
    )


@pytest.mark.parametrize(
    "entorno,esperado,prefijo",
    [
        ("dev", ["Desarrollo", "info"], "[Desarrollo]"),
        ("qa", ["QA", "success"], "[QA]"),
        ("homologacion", ["Homologación", "warning"], "[Homologación]"),
        ("prd", ["Producción", "danger"], None),
    ],
)
def test_badge_de_entorno(settings, entorno, esperado, prefijo):
    settings.ENVIRONMENT = entorno

    assert badge_entorno(None) == esperado
    assert prefijo_titulo_entorno(None) == prefijo


@pytest.mark.parametrize(
    "app_label,dominio",
    [
        ("comedores", "Comedores"),
        ("pwa", "Comedores"),
        ("centrodeinfancia", "CDI"),
        ("celiaquia", "Celiaquía"),
        ("VAT", "VAT"),
        ("ver_para_ser_libre", "VPSL"),
        ("auth", "Kernel y usuarios"),
        ("ciudadanos", "Kernel y usuarios"),
        ("auditlog", "Auditoría"),
        ("encuestas", "Núcleo SISOC"),
    ],
)
def test_dominio_de_cada_app(app_label, dominio):
    assert dominio_de_app(app_label)[0] == dominio


@pytest.mark.django_db
def test_sidebar_agrupa_por_dominio_y_suma_otros_servicios(superuser, monkeypatch):
    request = RequestFactory().get("/admin/")
    request.user = superuser
    monkeypatch.setattr(
        "core.admin_navigation.enlaces_admin_de_backends",
        lambda user: [{"label": "PAS <b>", "url": "/admin/pas/"}],
    )

    grupos = {grupo["title"]: grupo for grupo in navegacion_sidebar(request)}

    assert {"Comedores", "CDI", "Kernel y usuarios", "Auditoría"} <= set(grupos)
    enlaces_comedores = [item["link"] for item in grupos["Comedores"]["items"]]
    assert reverse("admin:comedores_comedor_changelist") in enlaces_comedores
    # Unfold renderiza el título con |safe: tiene que llegar escapado.
    assert grupos["Otros servicios"]["items"] == [
        {"title": "PAS &lt;b&gt;", "icon": "open_in_new", "link": "/admin/pas/"}
    ]


def test_enlaces_de_otros_backends_solo_para_superusuarios():
    registro = load_backends_registry()
    with override_settings(SISOC_BACKENDS={"pas": registro["pas"]}):
        super_ = SimpleNamespace(
            is_authenticated=True, is_active=True, is_staff=True, is_superuser=True
        )
        staff = SimpleNamespace(
            is_authenticated=True, is_active=True, is_staff=True, is_superuser=False
        )
        assert enlaces_admin_de_backends(super_) == registro["pas"]["admin_links"]
        assert enlaces_admin_de_backends(staff) == []


def test_static_de_unfold_disponibles_para_collectstatic():
    assert finders.find("unfold/css/styles.css")
    assert finders.find("unfold/js/alpine/alpine.js")


RUNTIMES = ["config.settings"] + [
    f"{nombre}_runtime.settings" for nombre in load_backends_registry()
]


@pytest.mark.parametrize("settings_module", RUNTIMES)
def test_admin_carga_en_cada_runtime(settings_module):
    script = """
import config, django
django.setup()
from types import SimpleNamespace
from django.conf import settings
from django.contrib import admin
from django.core.checks import run_checks
from django.test import RequestFactory
from django.urls import resolve, reverse
from core.admin_navigation import navegacion_sidebar
from core.admin_site import SisocAdminSite

assert isinstance(admin.site, SisocAdminSite), type(admin.site)
apps = settings.INSTALLED_APPS
assert apps.index("unfold.apps.BasicAppConfig") < apps.index(
    "core.admin_apps.SisocAdminConfig"
)
assert resolve(reverse("admin:index")).url_name == "index"
errors = [e for e in run_checks() if e.level >= 40]
assert not errors, errors
request = RequestFactory().get("/admin/")
request.user = SimpleNamespace(
    is_active=True, is_authenticated=True, is_superuser=True, is_staff=True,
    has_module_perms=lambda app: True, has_perm=lambda perm: True,
)
assert navegacion_sidebar(request)
print("ADMIN_UNFOLD_OK")
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).resolve().parents[4],
        env={
            **os.environ,
            "DJANGO_SETTINGS_MODULE": settings_module,
            "WAIT_FOR_DB": "false",
        },
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "ADMIN_UNFOLD_OK" in result.stdout


def test_regla_de_acceso_exige_staff_y_superusuario():
    def usuario(**flags):
        return SimpleNamespace(
            is_authenticated=True,
            is_active=True,
            **{"is_staff": True, "is_superuser": True, **flags},
        )

    assert puede_usar_admin(usuario())
    assert not puede_usar_admin(usuario(is_superuser=False))
    # Superusuario sin staff: hoy no entra al admin y sigue sin entrar.
    assert not puede_usar_admin(usuario(is_staff=False))
    assert not puede_usar_admin(None)


@pytest.mark.django_db
def test_todos_los_listados_del_admin_cargan(auth_client):
    # Con la base vacía, cada ModelAdmin migrado a Unfold renderiza su listado.
    fallidos = []
    for model in admin.site._registry:  # pylint: disable=protected-access
        url = reverse(
            f"admin:{model._meta.app_label}_{model._meta.model_name}_changelist"
        )
        status = auth_client.get(url).status_code
        if status != 200:
            fallidos.append((url, status))

    assert not fallidos


def _apps_de_verticales():
    return {app for spec in load_backends_registry().values() for app in spec["apps"]}


def test_admins_de_verticales_no_usan_autocomplete():
    # En deploy /admin/autocomplete/ lo sirve el core, que no instala los
    # modelos de los verticales: ahí el autocomplete responde 403. Se usa
    # raw_id_fields (su popup abre el admin del dueño, que sí está ruteado).
    from unfold.contrib.filters.admin import (  # pylint: disable=import-outside-toplevel
        AutocompleteSelectFilter,
        AutocompleteSelectMultipleFilter,
    )

    verticales = _apps_de_verticales()
    con_autocomplete = []
    for (
        model,
        model_admin,
    ) in admin.site._registry.items():  # pylint: disable=protected-access
        if model._meta.app_config.name not in verticales:
            continue
        admins = [
            model_admin,
            *(inline(model, admin.site) for inline in model_admin.inlines),
        ]
        for un_admin in admins:
            filtros = (
                [
                    filtro[1]
                    for filtro in un_admin.list_filter
                    if isinstance(filtro, (tuple, list))
                ]
                if hasattr(un_admin, "list_filter")
                else []
            )
            if un_admin.autocomplete_fields or any(
                issubclass(
                    filtro, (AutocompleteSelectFilter, AutocompleteSelectMultipleFilter)
                )
                for filtro in filtros
            ):
                con_autocomplete.append(
                    f"{model._meta.label}: {type(un_admin).__name__}"
                )

    assert not con_autocomplete
