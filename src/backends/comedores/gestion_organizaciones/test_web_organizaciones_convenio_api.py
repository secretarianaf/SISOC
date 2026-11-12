"""Web API (G1 v1) of the project convenio (O01).

``/api/web/comedores/organizaciones/proyectos/<id>/convenio/`` runs the native
``ConvenioProyectoView``. The tests pin the persisted effects, the Django
messages verbatim, the redirect targets and today's access
(``organizaciones.view_organizacion`` on the route, no object scope).
"""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.test import Client

from comedores.models import Programas
from core import web_gate
from gestion_organizaciones.models import (
    ConvenioProyecto,
    LineaProyecto,
    ProgramaOrganizacion,
)
from organizaciones.models import Organizacion, ProyectoOrganizacion

VIEW = "organizaciones.view_organizacion"
API = "/api/web/comedores/organizaciones/proyectos/%d/convenio/"

pytestmark = pytest.mark.django_db


def _usuario(nombre, *codes):
    usuario = get_user_model().objects.create_user(nombre)
    profile = usuario.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    for code in codes:
        app, codename = code.split(".")
        if app == "auth":
            permiso = Permission.objects.get_or_create(
                content_type=ContentType.objects.get_for_model(Group),
                codename=codename,
                defaults={"name": codename},
            )[0]
        else:
            permiso = Permission.objects.get(
                content_type__app_label=app, codename=codename
            )
        usuario.user_permissions.add(permiso)
    return usuario


@pytest.fixture(name="web")
def web_fixture():
    client = Client()
    client.force_login(_usuario("convenio_web", VIEW))
    return client


def _proyecto(linea="Abordaje comunitario - Línea Secos", codigo="P-1", **extra):
    organizacion = Organizacion.objects.create(nombre="Org Convenio", cuit=20111111112)
    proyecto = ProyectoOrganizacion.objects.create(
        organizacion=organizacion, codigo=codigo, **extra
    )
    if linea:
        LineaProyecto.objects.create(
            proyecto=proyecto, programa=Programas.objects.create(nombre=linea)
        )
    return proyecto


def _datos(**extra):
    datos = {
        "numero": "CV-1",
        "fecha": "2026-01-15",
        "meses": "12",
        "monto_total": "1000.00",
        "componente_alimentario": "400.00",
        "componente_gastos_generales": "300.00",
        "componente_siph": "200.00",
        "componente_gasto_bancario": "100.00",
    }
    datos.update(extra)
    return datos


def _campos(data):
    return [c["name"] for c in data["form"]["fields"]]


def test_new_convenio_projects_the_header_data_and_the_real_form(web):
    proyecto = _proyecto()

    data = web.get(API % proyecto.pk).json()

    assert data["project"] == {"id": proyecto.pk, "code": "P-1"}
    assert data["organization"] == {
        "id": proyecto.organizacion_id,
        "name": "Org Convenio",
        "cuit": "20111111112",
        "region": "Sin información",
        "subzone": "Sin información",
    }
    assert data["line"] == "Abordaje comunitario - Línea Secos"
    assert data["exists"] is False
    assert data["summary"] is None
    assert data["is_tradicional"] is False
    assert _campos(data) == [
        "numero",
        "fecha",
        "meses",
        "monto_total",
        "componente_alimentario",
        "componente_gastos_generales",
        "componente_siph",
        "componente_gasto_bancario",
    ]
    assert data["form"]["components"] == _campos(data)[4:]
    assert data["urls"]["cancel"] == (
        f"/organizaciones/detalle/{proyecto.organizacion_id}"
        f"?programa={proyecto.linea.programa_id}"
    )


def test_tradicional_adds_imprevistos_and_secos_does_not(web):
    secos = _proyecto()
    tradicional = _proyecto("Abordaje comunitario - Línea Tradicional", "P-2")

    assert "imprevistos" not in _campos(web.get(API % secos.pk).json())
    data = web.get(API % tradicional.pk).json()
    assert data["is_tradicional"] is True
    assert _campos(data)[-1] == "imprevistos"


def test_existing_convenio_is_loaded_and_edited_without_duplicating(web):
    proyecto = _proyecto()
    web.post(API % proyecto.pk, _datos())
    data = web.get(API % proyecto.pk).json()

    assert data["exists"] is True
    valores = {c["name"]: c["value"] for c in data["form"]["fields"]}
    assert valores["numero"] == "CV-1" and valores["fecha"] == "2026-01-15"
    assert valores["monto_total"] == "1000.00"
    assert data["summary"] == {
        "suma": "$1.000",
        "total": "$1.000",
        "diferencia": "$0",
        "coincide": True,
    }

    respuesta = web.post(API % proyecto.pk, _datos(numero="CV-2"))

    assert respuesta.status_code == 200
    assert ConvenioProyecto.objects.filter(proyecto=proyecto).count() == 1
    assert ConvenioProyecto.objects.get(proyecto=proyecto).numero == "CV-2"


def test_valid_post_saves_and_redirects_with_the_native_message(web):
    proyecto = _proyecto()

    respuesta = web.post(API % proyecto.pk, _datos())

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "redirect": (
            f"/organizaciones/detalle/{proyecto.organizacion_id}"
            f"?programa={proyecto.linea.programa_id}"
        ),
        "messages": [{"message": "Datos de convenio guardados.", "level": "success"}],
    }
    convenio = ConvenioProyecto.objects.get(proyecto=proyecto)
    assert convenio.monto_total == Decimal("1000.00")


def test_sum_mismatch_adds_the_native_warning(web):
    proyecto = _proyecto("Abordaje comunitario - Línea Tradicional")

    respuesta = web.post(API % proyecto.pk, _datos(imprevistos="50.00"))

    assert respuesta.json()["messages"] == [
        {"message": "Datos de convenio guardados.", "level": "success"},
        {
            "message": (
                "La suma de los componentes ($1.050) no coincide "
                "con el monto total ($1.000)."
            ),
            "level": "warning",
        },
    ]
    assert ConvenioProyecto.objects.get(proyecto=proyecto).imprevistos == Decimal("50")


def test_invalid_post_returns_django_errors_and_writes_nothing(web):
    proyecto = _proyecto()

    respuesta = web.post(API % proyecto.pk, _datos(numero="", meses="0"))

    assert respuesta.status_code == 400
    errores = respuesta.json()["errors"]
    assert errores["numero"] == ["Este campo es requerido."]
    assert "meses" in errores
    assert not ConvenioProyecto.objects.exists()
    assert respuesta.json()["form"]["fields"][0]["errors"] == errores["numero"]


def test_imprevistos_are_ignored_outside_tradicional(web):
    proyecto = _proyecto()

    respuesta = web.post(API % proyecto.pk, _datos(imprevistos="10.00"))

    assert respuesta.status_code == 200
    assert ConvenioProyecto.objects.get(proyecto=proyecto).imprevistos is None


def test_inactive_or_unknown_project_is_404(web):
    proyecto = _proyecto(activo=False)

    assert web.get(API % proyecto.pk).status_code == 404
    assert web.post(API % proyecto.pk, _datos()).status_code == 404
    assert web.get(API % 999999).status_code == 404


def test_project_without_line_is_409_with_the_native_message_and_target(web):
    proyecto = _proyecto(linea=None)
    esperado = {
        "error": "Asigná una línea al proyecto P-1 antes de cargar el convenio.",
        "redirect": f"/organizaciones/editar/{proyecto.organizacion_id}",
        "messages": [
            {
                "message": "Asigná una línea al proyecto P-1 antes de cargar el convenio.",
                "level": "error",
            }
        ],
    }

    for metodo in (web.get, lambda url: web.post(url, _datos())):
        respuesta = metodo(API % proyecto.pk)
        assert respuesta.status_code == 409
        assert respuesta.json() == esperado
    assert not ConvenioProyecto.objects.exists()
    # The queued native message was consumed by the answer.
    assert web.get("/api/web/comedores/organizaciones/listado/").json()["messages"] == []


def test_access_is_today_s_anonymous_401_no_permission_403_and_csrf_403():
    proyecto = _proyecto()

    anonimo = Client().get(API % proyecto.pk)
    assert anonimo.status_code == 401
    assert anonimo.json() == {"detail": web_gate.DETAIL_UNAUTHENTICATED}
    sin_permiso = Client()
    sin_permiso.force_login(_usuario("convenio_sin"))
    assert sin_permiso.get(API % proyecto.pk).status_code == 403
    assert sin_permiso.post(API % proyecto.pk, _datos()).status_code == 403
    con_csrf = Client(enforce_csrf_checks=True)
    con_csrf.force_login(_usuario("convenio_csrf", VIEW))
    assert con_csrf.post(API % proyecto.pk, _datos()).status_code == 403
    assert not ConvenioProyecto.objects.exists()


def test_legajo_delivers_the_convenios_summary_as_a_section(web):
    proyecto = _proyecto()
    web.post(API % proyecto.pk, _datos(componente_siph="150.00"))
    url = (
        f"/api/web/comedores/organizaciones/{proyecto.organizacion_id}/"
        f"?programa={proyecto.linea.programa_id}"
    )
    ProgramaOrganizacion.objects.create(
        organizacion=proyecto.organizacion, programa=proyecto.linea.programa
    )

    data = web.get(url).json()

    secciones = [s for s in data["sections"] if s["kind"] == "convenios"]
    assert len(secciones) == 1
    seccion = secciones[0]
    assert seccion["program"] == "Abordaje comunitario - Línea Secos"
    assert seccion["can_manage"] is True
    fila = seccion["rows"][0]
    assert fila["project"]["code"] == "P-1"
    assert fila["convenio"]["number"] == "CV-1"
    assert fila["convenio"]["date"] == "15/01/2026"
    assert fila["summary"]["coincide"] is False
    assert fila["url"] == f"/organizaciones/proyectos/{proyecto.pk}/convenio/"
    marcador = f'<div data-legajo-seccion="{data["sections"].index(seccion)}"></div>'
    assert marcador in data["html"]
    assert "Datos de Convenio" not in data["html"]
