"""Web API (G1 v1) of the CDF beneficiaries and responsables consultation (CDF03.01).

Lists and details run the native views; the tests pin the exact and NoCount
envelopes, the 404 rules, the filters, the export availability and the
absence of any centre or territorial scope (D1 parity).
"""

import json
import types
from datetime import date

import pytest
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.test import Client, override_settings

from centrodefamilia.models import (
    Actividad,
    Beneficiario,
    BeneficiarioResponsable,
    Categoria,
    Centro,
    Responsable,
)
from centrodefamilia.web_preview import cdf_preview_patterns
from config.urls_all import urlpatterns as monolith_patterns
from core.models import Municipio, Provincia

INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)

pytestmark = pytest.mark.django_db


def _user(username, *roles, view=True):
    user = User.objects.create_user(username)
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    if view:
        user.user_permissions.add(
            Permission.objects.get(
                content_type=ContentType.objects.get_for_model(Centro),
                codename="view_centro",
            )
        )
    for role in roles:
        permission, _ = Permission.objects.get_or_create(
            content_type=ContentType.objects.get_for_model(Group),
            codename=role,
            defaults={"name": role},
        )
        user.user_permissions.add(permission)
    return User.objects.get(pk=user.pk)


def _client(user):
    client = Client()
    client.force_login(user)
    return client


def _filters(field, value, op="eq"):
    return json.dumps(
        {"logic": "AND", "items": [{"field": field, "op": op, "value": value}]}
    )


@pytest.fixture(name="padron")
def padron_fixture():
    provincia = Provincia.objects.create(nombre="Buenos Aires")
    municipio = Municipio.objects.create(nombre="La Matanza", provincia=provincia)
    responsables = [
        Responsable.objects.create(
            cuil=27000000000 + n,
            dni=30000000 + n,
            apellido=f"Resp{n:02d}",
            nombre="Ana",
            genero="F" if n % 2 else "M",
            fecha_nacimiento=date(1980, 1, 1),
            vinculo_parental="Padre/Madre",
            calle="Calle",
            provincia=provincia,
            prefijo_celular="11" if n == 1 else None,
            numero_celular="4000" if n == 1 else None,
        )
        for n in range(1, 13)
    ]
    beneficiarios = []
    for n in range(1, 13):
        beneficiario = Beneficiario.objects.create(
            cuil=20000000000 + n,
            dni=40000000 + n,
            apellido=f"Benef{n:02d}",
            nombre="Sol",
            genero="F" if n % 2 else "M",
            fecha_nacimiento=date(2012, 3, n),
            domicilio="Siempreviva 742",
            calle="Siempreviva",
            altura=742 if n == 1 else None,
            maximo_nivel_educativo="Primario incompleto",
            responsable=responsables[0] if n <= 3 else responsables[n - 1],
            provincia=provincia,
            municipio=municipio if n == 1 else None,
            actividad_preferida=["Deportiva"] if n == 1 else [],
            actividades_extracurriculares=n == 1,
        )
        BeneficiarioResponsable.objects.create(
            beneficiario=beneficiario,
            responsable=beneficiario.responsable,
            vinculo_parental="Tutor/Tutora",
        )
        beneficiarios.append(beneficiario)
    return {"beneficiarios": beneficiarios, "responsables": responsables}


@pytest.fixture(name="lector")
def lector_fixture():
    return _client(_user("lector_cdf"))


def test_beneficiarios_exact_page_rows_and_capabilities(lector, padron):
    respuesta = lector.get("/api/web/cdf/beneficiarios/")

    assert respuesta.status_code == 200
    assert respuesta["Cache-Control"] == "private, no-store"
    data = respuesta.json()
    assert (data["count"], data["pages"], data["page"], data["page_size"]) == (
        12,
        2,
        1,
        10,
    )
    assert data["page_range"] == [1, 2]
    assert data["is_paginated"] is True
    assert [h["title"] for h in data["headers"]][:3] == [
        "CUIL",
        "Apellido y Nombre",
        "DNI",
    ]
    assert data["headers"][0] == {
        "title": "CUIL",
        "width": "10%",
        "sortable": True,
        "sort_key": "cuil",
    }
    primera = data["results"][0]
    assert primera["id"] == padron["beneficiarios"][-1].pk
    assert primera["cells"] == [
        "20000000012",
        "Benef12, Sol",
        "40000012",
        "12/03/2012",
        "Masculino",
        "Resp12, Ana",
        "27000000012",
        "Buenos Aires",
        "-",
    ]
    assert (
        primera["url"]
        == f"/centrodefamilia/beneficiarios/beneficiarios/{primera['id']}/"
    )
    assert data["can_export"] is False
    assert data["urls"]["add"] == "/centrodefamilia/beneficiarios/nuevo/"
    assert (
        data["urls"]["export"]
        == "/centrodefamilia/beneficiarios/beneficiarios/exportar/"
    )
    assert data["breadcrumb"] == [
        {
            "text": "Beneficiarios",
            "url": "/centrodefamilia/beneficiarios/beneficiarios/",
        },
        {"text": "Listar", "url": None},
    ]
    assert data["columns"]["list_key"] == "centrodefamilia_beneficiarios_list"


def test_beneficiarios_page_rules_are_the_listview_ones(lector, padron):
    assert lector.get("/api/web/cdf/beneficiarios/", {"page": "abc"}).status_code == 404
    assert lector.get("/api/web/cdf/beneficiarios/", {"page": "999"}).status_code == 404
    ultima = lector.get("/api/web/cdf/beneficiarios/", {"page": "last"}).json()
    assert (ultima["page"], len(ultima["results"])) == (2, 2)
    filtro = _filters("genero", "femenino")
    data = lector.get(
        "/api/web/cdf/beneficiarios/", {"filters": filtro, "page": "1"}
    ).json()
    assert data["count"] == 6
    assert {fila["cells"][4] for fila in data["results"]} == {"Femenino"}
    assert data["query_without_page"].startswith("filters=%7B")
    assert data["filters"]["filters"] == filtro


def test_responsables_nocount_envelope_and_annotation(lector, padron):
    data = lector.get("/api/web/cdf/responsables/", {"page": "0"}).json()
    assert data["count"] is None and data["pages"] is None
    assert data["page"] == 1 and data["has_next"] is True
    assert data["results"][0]["cells"] == [
        "27000000012",
        "Resp12, Ana",
        "30000012",
        "Masculino",
        "1",
        "Buenos Aires",
        "-",
    ]
    fuera = lector.get("/api/web/cdf/responsables/", {"page": "99"}).json()
    assert (fuera["page"], fuera["count"], len(fuera["results"])) == (2, None, 2)
    con_varios = lector.get(
        "/api/web/cdf/responsables/",
        {"filters": _filters("cantidad_beneficiarios", 1, "gt")},
    ).json()
    assert [f["id"] for f in con_varios["results"]] == [padron["responsables"][0].pk]
    assert con_varios["results"][0]["cells"][4] == "3"
    assert "urls" in con_varios and "add" not in con_varios["urls"]


def test_export_availability_and_permission(padron):
    sse = _client(_user("sse_export", "role_cdf_sse"))
    csv = _client(_user("csv_export", "role_exportar_a_csv"))
    sin_rol = _client(_user("sin_rol_export"))
    url = "/api/web/cdf/beneficiarios/exportar/disponible/"

    assert sse.get(url).json() == {"exists": True, "message": ""}
    vacio = csv.get(url, {"filters": _filters("dni", 1)})
    assert vacio.json() == {
        "exists": False,
        "message": "No hay beneficiarios para exportar con el filtro aplicado.",
    }
    assert sin_rol.get(url).status_code == 403
    assert (
        sin_rol.get(
            "/centrodefamilia/beneficiarios/beneficiarios/exportar/"
        ).status_code
        == 403
    )
    assert sse.get("/api/web/cdf/beneficiarios/").json()["can_export"] is True
    assert csv.get("/api/web/cdf/beneficiarios/").json()["can_export"] is True


def test_beneficiario_detail_projection_and_404(lector, padron):
    beneficiario = padron["beneficiarios"][0]
    actividad = Actividad.objects.create(
        nombre="Ajedrez", categoria=Categoria.objects.create(nombre="Juegos")
    )
    beneficiario.actividades_detalle.add(actividad)

    data = lector.get(f"/api/web/cdf/beneficiarios/{beneficiario.pk}/").json()

    assert data["nombre_completo"] == "Benef01, Sol"
    assert data["fecha_nacimiento"] == "01/03/2012"
    assert data["correo_electronico"] == "No especificado"
    assert data["responsable"]["nombre_completo"] == "Resp01, Ana"
    assert data["responsable"]["celular"] == "11-4000"
    assert data["responsable"]["vinculo_display"] == "Padre/Madre"
    assert data["domicilio"]["calle"] == "Siempreviva 742"
    assert data["domicilio"]["municipio"] == "La Matanza"
    assert data["domicilio"]["localidad"] == "None"
    assert data["domicilio"]["barrio"] == "No especificado"
    assert data["academico"] == {
        "estudia": False,
        "nivel_actual": None,
        "maximo_nivel": "Primario incompleto",
        "institucion": "No especificada",
    }
    assert data["actividad_preferida"] == ["Deportiva"]
    assert data["actividades_detalle"] == ["Ajedrez"]
    otro = padron["beneficiarios"][1]
    assert (
        lector.get(f"/api/web/cdf/beneficiarios/{otro.pk}/").json()["domicilio"][
            "calle"
        ]
        == "Siempreviva "
    )
    otro.delete()
    assert lector.get(f"/api/web/cdf/beneficiarios/{otro.pk}/").status_code == 404
    assert lector.get("/api/web/cdf/beneficiarios/999999/").status_code == 404


def test_responsable_detail_lists_its_links(lector, padron):
    responsable = padron["responsables"][0]

    data = lector.get(f"/api/web/cdf/responsables/{responsable.pk}/").json()

    assert data["nombre_completo"] == "Resp01, Ana"
    assert data["telefono_fijo"] == "No especificado"
    assert data["domicilio"]["piso_vivienda"] == "No especificado"
    assert [v["apellido_nombre"] for v in data["vinculos"]] == [
        "Benef01, Sol",
        "Benef02, Sol",
        "Benef03, Sol",
    ]
    assert data["vinculos"][0]["vinculo_display"] == "Tutor/Tutora"
    assert data["vinculos"][0]["url"].startswith(
        "/centrodefamilia/beneficiarios/beneficiarios/"
    )
    responsable.delete()
    assert lector.get(f"/api/web/cdf/responsables/{responsable.pk}/").status_code == 404


def test_access_has_no_scope_beyond_view_centro(padron):
    sin_permiso = _client(_user("sin_view_benef", view=False))
    for url in (
        "/api/web/cdf/beneficiarios/",
        f"/api/web/cdf/beneficiarios/{padron['beneficiarios'][0].pk}/",
        "/api/web/cdf/beneficiarios/exportar/disponible/",
        "/api/web/cdf/responsables/",
        f"/api/web/cdf/responsables/{padron['responsables'][0].pk}/",
    ):
        assert Client().get(url).status_code == 401, url
        assert sin_permiso.get(url).status_code == 403, url
        assert (
            _client(_user(f"u{abs(hash(url)) % 10**6}")).post(url).status_code == 405
        ), url
    solo_view = _client(_user("solo_view_benef"))
    assert solo_view.get("/api/web/cdf/beneficiarios/").json()["count"] == 12


def test_preview_entries_keep_the_native_guards(tmp_path, padron):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    module = types.ModuleType("cdf_benef_preview_urls")
    module.urlpatterns = cdf_preview_patterns(tmp_path) + list(monolith_patterns)
    lector = _client(_user("preview_benef"))
    sin_permiso = _client(_user("preview_sin", view=False))
    beneficiario = padron["beneficiarios"][0].pk
    responsable = padron["responsables"][0].pk
    base = "/centrodefamilia/beneficiarios/"
    for url in (
        f"{base}beneficiarios/",
        f"{base}beneficiarios/{beneficiario}/",
        f"{base}nuevo/",
        f"{base}responsables/",
        f"{base}responsables/{responsable}/",
    ):
        with override_settings(ROOT_URLCONF=module):
            entrada = lector.get(url)
        assert entrada.status_code == 200, url
        assert '/centrodefamilia/react/assets/app-1.js"' in entrada.content.decode()
        assert "no-store" in entrada["Cache-Control"]
    for client, url, params in (
        (Client(), f"{base}beneficiarios/", {}),
        (sin_permiso, f"{base}responsables/", {}),
        (sin_permiso, f"{base}nuevo/", {}),
        (lector, f"{base}beneficiarios/", {"page": "abc"}),
        (lector, f"{base}beneficiarios/", {"page": "999"}),
        (lector, f"{base}responsables/", {"page": "999"}),
        (lector, f"{base}beneficiarios/999999/", {}),
        (lector, f"{base}responsables/999999/", {}),
    ):
        native = client.get(url, params)
        with override_settings(ROOT_URLCONF=module):
            preview = client.get(url, params)
        assert (preview.status_code, preview.get("Location")) == (
            native.status_code,
            native.get("Location"),
        ), (url, params)
