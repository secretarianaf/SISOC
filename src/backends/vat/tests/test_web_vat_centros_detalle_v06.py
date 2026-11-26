"""V06.01/V05.01: web API del detalle de un centro y de su panel de cursos (``/api/web/vat/centros-detalle/``). Datos sintéticos."""

import itertools
import types
from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.test import Client, override_settings
from rest_framework.test import APIClient

from config.urls_all import urlpatterns as monolith_patterns
from core.models import Localidad, Municipio, Provincia
from VAT.models import (
    Centro,
    ComisionCurso,
    Curso,
    InstitucionContacto,
    InstitucionUbicacion,
    ModalidadCursada,
    PlanVersionCurricular,
    Sector,
)
from VAT.web_preview_vat_centros_lista import centros_preview_patterns

pytestmark = pytest.mark.django_db

ROOT = "/api/web/vat/centros-detalle/"
_COUNTER = itertools.count()
INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)


def _client(*codes, sse=False, visualizador=False, csrf=False):
    user = get_user_model().objects.create_user(f"cd{next(_COUNTER)}")
    user.user_permissions.add(
        *Permission.objects.filter(content_type__app_label="VAT", codename__in=codes)
    )
    for marcador in (["role_vat_sse"] if sse else []) + (
        ["role_inet_admin_visualizador"] if visualizador else []
    ):
        permiso, _ = Permission.objects.get_or_create(
            content_type=ContentType.objects.get_for_model(Group),
            codename=marcador,
            defaults={"name": marcador},
        )
        user.user_permissions.add(permiso)
    client = APIClient(enforce_csrf_checks=csrf)
    client.force_login(user)
    client.user = user
    return client


@pytest.fixture(name="centro")
def centro_fixture():
    provincia = Provincia.objects.create(nombre="Buenos Aires")
    municipio = Municipio.objects.create(nombre="La Plata", provincia=provincia)
    localidad = Localidad.objects.create(nombre="Tolosa", municipio=municipio)
    return Centro.objects.create(
        nombre="CFP 401",
        codigo="060144900",
        provincia=provincia,
        municipio=municipio,
        localidad=localidad,
        calle="Calle 7",
        numero="1234",
        telefono="221 555 0101",
        correo="cfp@example.com",
        nombre_referente="Lia",
        apellido_referente="Paz",
    )


def _curso_con_comision(centro, nombre="Electricidad básica"):
    provincia = centro.provincia
    plan = PlanVersionCurricular.objects.create(
        nombre="Electricidad",
        provincia=provincia,
        sector=Sector.objects.create(nombre=f"Industria {next(_COUNTER)}"),
        modalidad_cursada=ModalidadCursada.objects.create(
            nombre=f"Presencial {next(_COUNTER)}"
        ),
        horas_reloj=100,
    )
    curso = Curso.objects.create(
        nombre=nombre,
        centro=centro,
        plan_estudio=plan,
        modalidad=plan.modalidad_cursada,
    )
    ubicacion = InstitucionUbicacion.objects.create(
        centro=centro, localidad=centro.localidad, rol_ubicacion="sede_principal"
    )
    comision = ComisionCurso.objects.create(
        curso=curso,
        ubicacion=ubicacion,
        codigo_comision="COM-001",
        nombre="Turno mañana",
        cupo_total=20,
        fecha_inicio=date(2026, 3, 1),
        fecha_fin=date(2026, 6, 30),
    )
    return curso, comision


def test_access_follows_the_route_rule_and_the_native_scope(centro):
    for url in (f"{ROOT}{centro.pk}/", f"{ROOT}{centro.pk}/cursos/"):
        assert APIClient().get(url).status_code == 401
        sin_permiso = get_user_model().objects.create_user(f"cd-sin{next(_COUNTER)}")
        cliente = APIClient()
        cliente.force_login(sin_permiso)
        assert cliente.get(url).status_code == 403
        # the route permission alone does not reach a centro outside the user's scope (native PermissionDenied)
        assert _client("view_centro").get(url).status_code == 403
        assert _client("view_centro", visualizador=True).get(url).status_code == 200
    assert _client("view_centro", sse=True).get(f"{ROOT}999999/").status_code == 404
    assert (
        _client("view_centro", sse=True).get(f"{ROOT}999999/cursos/").status_code == 404
    )
    assert (
        _client("view_centro", sse=True).post(f"{ROOT}{centro.pk}/").status_code == 405
    )


def test_detail_projects_what_the_native_page_prints(centro):
    InstitucionContacto.objects.create(
        centro=centro,
        nombre_contacto="Ana Gómez",
        documento="30111222",
        rol_area="Dirección",
        es_principal=True,
        telefono_contacto="221 555 0202",
        email_contacto="ana@example.com",
    )
    InstitucionUbicacion.objects.create(
        centro=centro,
        localidad=centro.localidad,
        rol_ubicacion="sede_principal",
        domicilio="7 123",
    )
    datos = _client("view_centro", sse=True).get(f"{ROOT}{centro.pk}/").json()
    assert datos["nombre"] == "CFP 401"
    assert datos["codigo"] == "060144900"
    assert datos["activo"] is True
    assert datos["mostrar_datos_administrativos"] is True
    assert datos["domicilio"] == "Calle 7 1234"
    assert datos["celular"] == "-"
    assert datos["correo"] == "cfp@example.com"
    assert datos["mapa"].startswith(
        "https://maps.google.com/maps?hl=es&q=Calle%207+1234,+Tolosa,+Buenos%20Aires,+Argentina+(CFP%20401)"
    )
    # the referente: the centro fields first, then the primary additional contact
    assert datos["referente"]["nombre"] == "Lia Paz"
    assert datos["referente"]["telefono"] == "221 555 0202"
    assert datos["referente"]["dni"] == "30111222"
    assert datos["referente"]["correo"] == "ana@example.com"
    assert datos["referente"]["usuarios"] == []
    assert datos["contactos"] == [
        {
            "id": datos["contactos"][0]["id"],
            "nombre": "Ana Gómez",
            "documento": "30111222",
            "rol": "Dirección",
            "principal": True,
            "telefono": "221 555 0202",
            "urls": {
                "form": f"/api/web/vat/centros-acciones/contactos/{datos['contactos'][0]['id']}/editar/",
                "guardar": f"/api/web/vat/institucion/contactos/{datos['contactos'][0]['id']}/editar/",
                "eliminar": f"/api/web/vat/institucion/contactos/{datos['contactos'][0]['id']}/eliminar/",
            },
        }
    ]
    assert [u["domicilio"] for u in datos["ubicaciones"]] == ["7 123"]
    assert datos["ubicaciones"][0]["localidad"] == "Tolosa"
    assert (
        datos["urls"]["cursos"] == f"/api/web/vat/centros-detalle/{centro.pk}/cursos/"
    )
    assert datos["messages"] == []
    # a centro without a street has no map and falls back to the activity address
    centro.calle = ""
    centro.domicilio_actividad = "Av. 1 y 2"
    centro.save()
    vacio = _client("view_centro", sse=True).get(f"{ROOT}{centro.pk}/").json()
    assert vacio["mapa"] is None
    assert vacio["domicilio"] == "Av. 1 y 2"


def test_detail_permission_flags_follow_the_native_predicates(centro):
    editor = _client(
        "view_centro",
        "add_institucionubicacion",
        "delete_institucioncontacto",
        sse=True,
    )
    permisos = editor.get(f"{ROOT}{centro.pk}/").json()["permisos"]
    assert permisos["editar_centro"] is True
    assert permisos["agregar_ubicacion"] is True
    assert permisos["eliminar_contacto"] is True
    assert permisos["editar_ubicacion"] is False
    lector = _client("view_centro", visualizador=True)
    assert (
        lector.get(f"{ROOT}{centro.pk}/").json()["permisos"]["editar_centro"] is False
    )


def test_cursos_panel_projects_courses_and_commissions(centro):
    curso, comision = _curso_con_comision(centro)
    Curso.objects.create(
        nombre="Sin comisión",
        centro=centro,
        plan_estudio=curso.plan_estudio,
        modalidad=curso.modalidad,
    )
    editor = _client(
        "view_centro",
        "view_curso",
        "view_comisioncurso",
        "add_comisioncurso",
        "delete_curso",
        sse=True,
    )
    datos = editor.get(f"{ROOT}{centro.pk}/cursos/").json()
    por_nombre = {c["nombre"]: c for c in datos["cursos"]}
    assert por_nombre["Electricidad básica"]["comisiones"] == 1
    assert por_nombre["Sin comisión"]["comisiones"] == 0
    assert por_nombre["Electricidad básica"]["plan"]
    assert por_nombre["Electricidad básica"]["urls"] == {
        "detalle": f"/vat/cursos/{curso.pk}/",
        "comision_nueva": f"/vat/cursos/{curso.pk}/comision/nueva/",
        "eliminar": f"/vat/cursos/{curso.pk}/eliminar/",
    }
    fila = datos["comisiones"][0]
    assert fila["codigo_o_nombre"] == "COM-001"
    assert fila["fecha_inicio"] == "01/03/2026"
    assert fila["fecha_fin"] == "30/06/2026"
    assert fila["cupo"] == "20"
    assert fila["curso_id"] == curso.pk
    assert fila["urls"]["detalle"] == f"/vat/cursos/comisiones/{comision.pk}/"
    assert fila["urls"]["eliminar"] is None
    assert datos["permisos"]["gestionar"] is True
    # a read-only profile sees the rows but none of the management links
    lector = _client("view_centro", "view_curso", visualizador=True)
    solo = lector.get(f"{ROOT}{centro.pk}/cursos/").json()
    assert solo["permisos"]["gestionar"] is False
    assert all(
        c["urls"]["comision_nueva"] is None and c["urls"]["eliminar"] is None
        for c in solo["cursos"]
    )
    assert all(c["urls"]["detalle"] for c in solo["cursos"])


@pytest.fixture(name="preview")
def preview_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    (tmp_path / "assets" / "app-1.js").write_text("console.log(1);", encoding="utf-8")
    module = types.ModuleType("vat_centros_detalle_preview_test_urls")
    module.urlpatterns = centros_preview_patterns(tmp_path) + list(monolith_patterns)
    with override_settings(ROOT_URLCONF=module):
        yield


@pytest.mark.usefixtures("preview")
def test_preview_entry_serves_the_frozen_index_behind_the_native_guards(centro):
    url = f"/vat/centros/{centro.pk}/"
    response = _client("view_centro", sse=True).get(url)
    assert response.status_code == 200
    assert '/vat/react/assets/app-1.js"' in response.content.decode()
    assert "no-store" in response["Cache-Control"]
    assert Client().get(url).status_code == 403
    assert _client("view_sector").get(url).status_code == 403
    # inside the permission but outside the scope: the native PermissionDenied
    assert _client("view_centro").get(url).status_code == 403
    assert (
        _client("view_centro", sse=True).get("/vat/centros/999999/").status_code == 404
    )
