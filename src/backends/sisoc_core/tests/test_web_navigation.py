import re
from collections import Counter
from html.parser import HTMLParser
from types import SimpleNamespace
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.context_processors import PermWrapper
from django.contrib.auth.models import Group, Permission
from django.template.loader import get_template
from django.test import RequestFactory
from django.urls import reverse

from usuarios.web_navigation import build_web_navigation


class _SidebarParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.roots = []
        self.stack = []
        self.paragraph_depth = 0

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "li":
            style = attributes.get("style", "")
            match = re.search(r"\border\s*:\s*(\d+)", style)
            node = {
                "label": "",
                "href": None,
                "children": [],
                "order": int(match.group(1)) if match else None,
            }
            (self.stack[-1]["children"] if self.stack else self.roots).append(node)
            self.stack.append(node)
        elif tag == "a" and self.stack:
            self.stack[-1]["href"] = attributes.get("href")
        elif tag == "p":
            self.paragraph_depth += 1

    def handle_data(self, data):
        if self.paragraph_depth and self.stack:
            self.stack[-1]["label"] += data

    def handle_endtag(self, tag):
        if tag == "p" and self.paragraph_depth:
            self.paragraph_depth -= 1
        elif tag == "li" and self.stack:
            self.stack.pop()


def _make_user(*permission_codes, groups=(), superuser=False):
    user = get_user_model().objects.create_user(
        username=f"synthetic-navigation-{uuid4().hex[:10]}",
        password="synthetic-test-password",
        is_superuser=superuser,
        is_staff=superuser,
    )
    if permission_codes:
        permissions = []
        for permission_code in permission_codes:
            app_label, codename = permission_code.split(".", 1)
            permissions.append(
                Permission.objects.get(
                    content_type__app_label=app_label,
                    codename=codename,
                )
            )
        user.user_permissions.add(*permissions)
    for group_name in groups:
        group, _ = Group.objects.get_or_create(name=group_name)
        user.groups.add(group)
    return user


def _request(user):
    request = RequestFactory().get("/api/web/session/")
    request.user = user
    request.resolver_match = SimpleNamespace(route="api/web/session/")
    return request


def _set_sidebar_predicates(monkeypatch, **flags):
    from core.services import sidebar_access
    from core.services import sidebar_items

    predicate_names = ("vat", "cdi_local", "datacalle", "inspecciones_gestion")
    for predicate_name in predicate_names:
        flag_name = f"sidebar_{predicate_name}"
        monkeypatch.setitem(
            sidebar_access._PREDICADOS,
            predicate_name,
            lambda user, name=flag_name: bool(getattr(user, name, False)),
        )
    monkeypatch.setattr(sidebar_items, "_proveedor_tableros", None)
    return flags


def _normalized_tree(items):
    return [
        {
            "label": item["label"],
            "href": item["href"],
            "children": _normalized_tree(item["children"]),
        }
        for item in items
    ]


def _legacy_tree(request, monkeypatch, dashboard_provider=None):
    from core.services import sidebar_items

    monkeypatch.setattr(sidebar_items, "_proveedor_tableros", dashboard_provider)
    template = get_template("includes/sidebar/opciones.html")
    rendered = template.render({"request": request, "perms": PermWrapper(request.user)})
    parser = _SidebarParser()
    parser.feed(rendered)

    def convert(node):
        children = [item for child in node["children"] if (item := convert(child))]
        label = " ".join(node["label"].split())
        if not label or node["href"] is None:
            return None
        return {
            "label": label,
            "href": None if node["href"] == "#" else node["href"],
            "children": children,
        }

    # The main sidebar flex items use explicit order 1..7; Mi Cuenta is sticky.
    roots_with_order = []
    for node in parser.roots:
        item = convert(node)
        if item:
            order = 100 if item["label"] == "Mi cuenta" else node["order"] or 50
            roots_with_order.append((order, item))
    roots_with_order.sort(key=lambda entry: entry[0])
    return [item for _, item in roots_with_order]


def _assert_matches_legacy(request, monkeypatch, dashboard_provider=None):
    projected = _normalized_tree(build_web_navigation(request))
    legacy = _legacy_tree(request, monkeypatch, dashboard_provider)

    def nodes(items, parent=()):
        for index, item in enumerate(items):
            path = parent + (index,)
            yield path, item["label"], item["href"]
            yield from nodes(item["children"], path)

    actual_nodes, expected_nodes = list(nodes(projected)), list(nodes(legacy))
    actual_items = Counter((label, href) for _, label, href in actual_nodes)
    expected_items = Counter((label, href) for _, label, href in expected_nodes)
    differences = (
        f"Unexpected: {list((actual_items - expected_items).elements())}; "
        f"missing: {list((expected_items - actual_items).elements())}"
    )
    for actual, expected in zip(actual_nodes, expected_nodes):
        assert actual == expected, differences
    assert len(actual_nodes) == len(expected_nodes)


@pytest.mark.django_db
def test_view_insumo_projects_legacy_parent_and_child_in_css_display_order(monkeypatch):
    _set_sidebar_predicates(monkeypatch)
    request = _request(_make_user("insumos.view_insumo"))

    navigation = build_web_navigation(request)

    assert [item["id"] for item in navigation] == [
        "inicio",
        "legajos",
        "configuracion-comedores",
        "comunicados",
        "mi_cuenta",
    ]
    insumos = next(
        item for item in navigation if item["id"] == "configuracion-comedores"
    )["children"]
    assert insumos == [
        {
            "id": "insumos_listar",
            "label": "Insumos",
            "href": reverse("insumos_listar"),
            "children": [],
        }
    ]
    assert _normalized_tree(navigation)[1]["children"] == []
    _assert_matches_legacy(request, monkeypatch)


@pytest.mark.django_db
def test_normal_user_keeps_visible_legacy_empty_legajos_group(monkeypatch):
    _set_sidebar_predicates(monkeypatch)
    request = _request(_make_user())

    navigation = build_web_navigation(request)

    assert [item["id"] for item in navigation] == [
        "inicio",
        "legajos",
        "comunicados",
        "mi_cuenta",
    ]
    assert navigation[1]["children"] == []
    _assert_matches_legacy(request, monkeypatch)


@pytest.mark.django_db
def test_sidebar_registered_predicates_preserve_visibility_and_or_precedence(
    monkeypatch,
):
    _set_sidebar_predicates(monkeypatch)
    user = _make_user("auditlog.view_logentry", "insumos.view_insumo")
    user.sidebar_vat = True
    request = _request(user)

    navigation = build_web_navigation(request)
    ids = [item["id"] for item in navigation]

    assert ids == ["inicio", "legajos", "administracion-sistema", "mi_cuenta"]
    assert "audittrail:log_list" in [child["id"] for child in navigation[2]["children"]]
    assert not any(item["id"] == "configuracion-comedores" for item in navigation)
    _assert_matches_legacy(request, monkeypatch)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "predicate,expected_visible",
    [
        ("vat", False),
        ("cdi_local", True),
        ("datacalle", False),
    ],
)
def test_domain_predicates_match_legacy_comedor_visibility(
    monkeypatch, predicate, expected_visible
):
    _set_sidebar_predicates(monkeypatch)
    user = _make_user("insumos.view_insumo")
    setattr(user, f"sidebar_{predicate}", True)
    request = _request(user)

    navigation = build_web_navigation(request)
    has_configuration = any(
        item["id"] == "configuracion-comedores" for item in navigation
    )

    assert has_configuration is expected_visible
    assert not any(item["id"] == "comunicados" for item in navigation)
    _assert_matches_legacy(request, monkeypatch)


@pytest.mark.django_db
def test_superuser_projects_every_live_group_without_constant_false_links(monkeypatch):
    _set_sidebar_predicates(monkeypatch)
    request = _request(_make_user(superuser=True))

    navigation = build_web_navigation(request)

    assert [item["id"] for item in navigation] == [
        "inicio",
        "legajos",
        "tableros",
        "administracion-sistema",
        "configuracion-comedores",
        "ocr_upload",
        "comunicados",
        "mi_cuenta",
    ]
    assert [child["id"] for child in navigation[4]["children"]] == [
        "dupla_list",
        "montoprestacion_listar",
        "cursos_app_mobile_list",
        "actividades_pnud_list",
        "insumos_listar",
        "gestor-templates",
    ]
    all_ids = _all_ids(navigation)
    assert not all_ids.intersection(
        {
            "vat_inscripcion_list",
            "vat_evaluacion_list",
            "vat_resultado_evaluacion_list",
            "vat_oferta_institucional_list",
            "vat_comision_list",
            "vat_inscripcion_oferta_list",
            "vat_institucion_contacto_list",
            "vat_institucion_identificador_list",
            "vat_institucion_ubicacion_list",
            "rendicion_cuentas_final_listar",
        }
    )
    _assert_matches_legacy(request, monkeypatch)


def _all_ids(items):
    result = set()
    for item in items:
        result.add(item["id"])
        result.update(_all_ids(item["children"]))
    return result


@pytest.mark.django_db
def test_dynamic_dashboard_groups_keep_provider_order_and_ignore_active_flag(
    monkeypatch,
):
    _set_sidebar_predicates(monkeypatch)
    request = _request(_make_user())
    provider_items = [
        {
            "tipo": "grupo",
            "nombre": "Paneles",
            "activo": True,
            "hijos": [
                {
                    "tipo": "single",
                    "nombre": "Uno",
                    "url": "/dashboard/uno/",
                    "activo": True,
                },
                {
                    "tipo": "single",
                    "nombre": "Dos",
                    "url": "/dashboard/dos/",
                    "activo": False,
                },
            ],
        },
        {
            "tipo": "single",
            "nombre": "Suelto",
            "url": "/dashboard/suelto/",
            "activo": True,
        },
    ]
    from core.services import sidebar_items

    monkeypatch.setattr(
        sidebar_items,
        "_proveedor_tableros",
        lambda _context: provider_items,
    )

    navigation = build_web_navigation(request)
    dashboard = next(item for item in navigation if item["id"] == "tableros")

    assert [child["label"] for child in dashboard["children"]] == ["Paneles", "Suelto"]
    assert dashboard["children"][0]["id"] == "dashboard-group:dashboard:/dashboard/uno/"
    assert dashboard["children"][0]["href"] is None
    assert [child["label"] for child in dashboard["children"][0]["children"]] == [
        "Uno",
        "Dos",
    ]
    assert dashboard["children"][0]["children"][1]["href"] == "/dashboard/dos/"
    _assert_matches_legacy(request, monkeypatch, lambda _context: provider_items)


@pytest.mark.django_db
def test_missing_dashboard_provider_is_empty_but_provider_errors_propagate(
    monkeypatch,
):
    _set_sidebar_predicates(monkeypatch)
    request = _request(_make_user())
    from core.services import sidebar_items

    monkeypatch.setattr(sidebar_items, "_proveedor_tableros", None)
    assert all(item["id"] != "tableros" for item in build_web_navigation(request))

    def unavailable(_context):
        raise RuntimeError("Synthetic dashboard provider failure")

    monkeypatch.setattr(sidebar_items, "_proveedor_tableros", unavailable)
    with pytest.raises(RuntimeError, match="Synthetic dashboard provider failure"):
        build_web_navigation(request)


@pytest.mark.django_db
def test_dashboard_link_must_be_internal(monkeypatch):
    _set_sidebar_predicates(monkeypatch)
    request = _request(_make_user())
    from core.services import sidebar_items

    monkeypatch.setattr(
        sidebar_items,
        "_proveedor_tableros",
        lambda _context: [
            {
                "tipo": "single",
                "nombre": "Externo",
                "url": "https://example.test/",
                "activo": False,
            }
        ],
    )

    with pytest.raises(ValueError, match="internal path"):
        build_web_navigation(request)


@pytest.mark.django_db
def test_inet_catalogs_preserve_cfpinet_group_permissions(monkeypatch):
    _set_sidebar_predicates(monkeypatch)
    user = _make_user(
        "VAT.view_centro",
        "VAT.view_modalidadcursada",
        groups=("CFPINET",),
    )
    request = _request(user)

    navigation = build_web_navigation(request)
    legajos = next(item for item in navigation if item["id"] == "legajos")
    inet = next(item for item in legajos["children"] if item["id"] == "inet")
    catalogs = next(item for item in inet["children"] if item["id"] == "inet-catalogos")

    assert [item["id"] for item in catalogs["children"]] == [
        "vat_planversioncurricular_list"
    ]
    _assert_matches_legacy(request, monkeypatch)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "permission_code",
    [
        "auth.view_user",
        "auth.view_group",
        "encuestas.view_encuesta",
        "dashboard.view_dashboard",
        "comunicados.add_comunicado",
        "ciudadanos.view_ciudadano",
        "ciudadanos.add_ciudadano",
        "comedores.view_comedor",
        "importarexpediente.view_archivosimportados",
        "organizaciones.view_organizacion",
        "centrodeinfancia.view_centrodeinfancia",
        "ver_para_ser_libre.view_itinerariovpsl",
        "pas.view_paspersona",
        "dispositivos.view_dispositivo",
        "datacalle.view_relevamiento",
        "centrodefamilia.view_centro",
        "VAT.view_centro",
        "celiaquia.view_expediente",
        "celiaquia.view_cupo_dashboard",
        "celiaquia.view_reporte_provincias",
    ],
)
def test_each_domain_permission_matches_rendered_legacy(permission_code, monkeypatch):
    _set_sidebar_predicates(monkeypatch)
    request = _request(_make_user(permission_code))

    _assert_matches_legacy(request, monkeypatch)


@pytest.mark.django_db
def test_vat_only_user_keeps_inet_navigation(monkeypatch):
    _set_sidebar_predicates(monkeypatch)
    user = _make_user("VAT.view_centro")
    user.sidebar_vat = True
    request = _request(user)

    navigation = build_web_navigation(request)

    legajos = next(item for item in navigation if item["id"] == "legajos")
    assert [child["id"] for child in legajos["children"]] == ["inet"]
    assert [child["id"] for child in legajos["children"][0]["children"]] == [
        "vat_centro_list",
        "vat_reporte_inscripciones_asistencias",
        "vat_buscador_ciudadano",
    ]
    _assert_matches_legacy(request, monkeypatch)
