"""V06.01/V05.01: acciones en página del detalle de un centro (``/api/web/vat/centros-acciones/`` y los ``modales`` del detalle). Datos sintéticos."""

import itertools
from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.urls import resolve
from rest_framework.test import APIClient

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

pytestmark = pytest.mark.django_db

DETALLE = "/api/web/vat/centros-detalle/"
ACCIONES = "/api/web/vat/centros-acciones/"
_COUNTER = itertools.count()


def _client(*codes, sse=True, csrf=False):
    user = get_user_model().objects.create_user(f"ca{next(_COUNTER)}")
    user.user_permissions.add(
        *Permission.objects.filter(content_type__app_label="VAT", codename__in=codes)
    )
    if sse:
        permiso, _ = Permission.objects.get_or_create(
            content_type=ContentType.objects.get_for_model(Group),
            codename="role_vat_sse",
            defaults={"name": "role_vat_sse"},
        )
        user.user_permissions.add(permiso)
    client = APIClient(enforce_csrf_checks=csrf)
    client.force_login(user)
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
    )


@pytest.fixture(name="plan")
def plan_fixture(centro):
    return PlanVersionCurricular.objects.create(
        nombre="Electricidad",
        provincia=centro.provincia,
        sector=Sector.objects.create(nombre=f"Industria {next(_COUNTER)}"),
        modalidad_cursada=ModalidadCursada.objects.create(
            nombre=f"Presencial {next(_COUNTER)}"
        ),
        horas_reloj=100,
        normativa="Res. 12/26",
    )


def _curso(centro, plan, nombre="Electricidad básica"):
    return Curso.objects.create(
        nombre=nombre,
        centro=centro,
        plan_estudio=plan,
        modalidad=plan.modalidad_cursada,
    )


EDITOR = (
    "view_centro",
    "add_institucioncontacto",
    "change_institucioncontacto",
    "add_institucionubicacion",
    "change_institucionubicacion",
    "add_curso",
    "change_curso",
    "change_comisioncurso",
)


def test_detail_carries_the_add_forms_of_the_native_modals_for_an_editable_centro(
    centro,
):
    modales = _client(*EDITOR).get(f"{DETALLE}{centro.pk}/").json()["modales"]
    assert [f["name"] for f in modales["contacto"]["fields"]] == [
        "centro",
        "nombre_contacto",
        "rol_area",
        "documento",
        "telefono_contacto",
        "email_contacto",
        "es_principal",
    ]
    assert {f["name"]: f["required"] for f in modales["contacto"]["fields"]}["centro"]
    assert not {f["name"]: f["required"] for f in modales["contacto"]["fields"]}[
        "documento"
    ]
    # ``form.as_p`` draws every visible field of the form, the one the page template leaves out included
    assert "nombre_ubicacion" in [f["name"] for f in modales["ubicacion"]["fields"]]
    assert modales["contacto"]["crear"] == (
        f"/api/web/vat/institucion/contactos/nuevo/?centro={centro.pk}"
    )
    assert modales["ubicacion"]["localidades"] == "/ajax/load-localidades/"


def test_detail_has_no_modal_forms_for_a_centro_the_user_cannot_edit(centro):
    lector = _client("view_centro", sse=False)
    # outside the native scope the page is a 403; the add forms exist only when ``can_edit_centro``
    assert lector.get(f"{DETALLE}{centro.pk}/").status_code == 403


def test_detail_rows_carry_the_urls_of_their_actions(centro):
    contacto = InstitucionContacto.objects.create(
        centro=centro, nombre_contacto="Ana", telefono_contacto="1"
    )
    ubicacion = InstitucionUbicacion.objects.create(
        centro=centro, localidad=centro.localidad, rol_ubicacion="sede_principal"
    )
    datos = _client(*EDITOR).get(f"{DETALLE}{centro.pk}/").json()
    for fila, base, pk in (
        (datos["contactos"][0], "contactos", contacto.pk),
        (datos["ubicaciones"][0], "ubicaciones", ubicacion.pk),
    ):
        assert fila["urls"] == {
            "form": f"{ACCIONES}{base}/{pk}/editar/",
            "guardar": f"/api/web/vat/institucion/{base}/{pk}/editar/",
            "eliminar": f"/api/web/vat/institucion/{base}/{pk}/eliminar/",
        }
        for url in fila["urls"].values():
            assert resolve(url).func


def test_edit_fragment_endpoints_follow_the_native_permissions(centro):
    contacto = InstitucionContacto.objects.create(
        centro=centro, nombre_contacto="Ana", telefono_contacto="1"
    )
    ubicacion = InstitucionUbicacion.objects.create(
        centro=centro,
        localidad=centro.localidad,
        rol_ubicacion="sede_principal",
        nombre_ubicacion="Anexo",
    )
    url_c = f"{ACCIONES}contactos/{contacto.pk}/editar/"
    url_u = f"{ACCIONES}ubicaciones/{ubicacion.pk}/editar/"
    for url in (url_c, url_u):
        assert APIClient().get(url).status_code == 401
        assert _client("view_centro").get(url).status_code == 403
        assert _client(*EDITOR).post(url).status_code == 405
    campos = _client(*EDITOR).get(url_u).json()["fields"]
    por_nombre = {f["name"]: f for f in campos}
    assert por_nombre["nombre_ubicacion"]["value"] == "Anexo"
    assert por_nombre["localidad"]["value"] == str(centro.localidad_id)
    assert (
        _client(*EDITOR).get(f"{ACCIONES}contactos/999999/editar/").status_code == 404
    )
    nombres = [f["name"] for f in _client(*EDITOR).get(url_c).json()["fields"]]
    assert "nombre_contacto" in nombres


def test_panel_carries_the_modal_forms_and_the_edit_rows(centro, plan):
    curso = _curso(centro, plan)
    curso.tipo = ["a", "b"]
    curso.observaciones = "Nota"
    curso.save()
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
    datos = _client(*EDITOR).get(f"{DETALLE}{centro.pk}/cursos/").json()
    modal = datos["modales"]["curso"]
    assert [f["name"] for f in modal["fields"]] == [
        "plan_estudio",
        "nombre",
        "tipo",
        "estado",
        "inscripcion_libre",
        "observaciones",
    ]
    # the label asterisk is ``field.field.required``: a select with a non-blank first option is required without the attribute
    assert {f["name"]: f["required"] for f in modal["fields"]} == {
        "plan_estudio": True,
        "nombre": True,
        "tipo": False,
        "estado": True,
        "inscripcion_libre": False,
        "observaciones": False,
    }
    assert modal["planes"] == [
        {"id": plan.pk, "etiqueta": "Electricidad", "normativa": "Res. 12/26"}
    ]
    assert modal["crear"] == f"{ACCIONES}cursos/nuevo/?centro={centro.pk}"
    comision_form = datos["modales"]["comision_curso"]["fields"]
    assert [f["name"] for f in comision_form][:3] == [
        "curso",
        "ubicacion",
        "cupo_total",
    ]
    fila = datos["cursos"][0]["edicion"]
    assert fila["tipo"] == ["a", "b"] and fila["observaciones"] == "Nota"
    assert fila["plan_estudio"] == str(plan.pk)
    assert fila["guardar"] == f"{ACCIONES}cursos/{curso.pk}/editar/"
    edicion = datos["comisiones"][0]["edicion"]
    assert edicion["fecha_inicio"] == "2026-03-01"
    assert edicion["cupo_total"] == "20"
    assert edicion["ubicacion"] == str(ubicacion.pk)
    assert edicion["guardar"] == (
        f"/api/web/vat/comisiones-formularios/cursos/{comision.pk}/editar/"
    )
    for url in (fila["guardar"], edicion["guardar"], modal["crear"].split("?")[0]):
        assert resolve(url).func
    # the edit rows follow the permission of the action; the forms follow the native ``can_manage_centro``
    sin_permiso = _client("view_centro", "view_curso", "view_comisioncurso")
    sin = sin_permiso.get(f"{DETALLE}{centro.pk}/cursos/").json()
    assert sin["modales"] is not None
    assert sin["cursos"][0]["edicion"] is None
    assert sin["comisiones"][0]["edicion"] is None
    lector = APIClient()
    visualizador = get_user_model().objects.create_user(f"ca{next(_COUNTER)}")
    visualizador.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="VAT",
            codename__in=["view_centro", "change_curso", "change_comisioncurso"],
        ),
        Permission.objects.get_or_create(
            content_type=ContentType.objects.get_for_model(Group),
            codename="role_inet_admin_visualizador",
            defaults={"name": "role_inet_admin_visualizador"},
        )[0],
    )
    lector.force_login(visualizador)
    ajeno = lector.get(f"{DETALLE}{centro.pk}/cursos/").json()
    assert ajeno["modales"] is None
    assert ajeno["cursos"][0]["edicion"] is None
    assert ajeno["comisiones"][0]["edicion"] is None


def _datos_curso(plan, **extra):
    return {
        "plan_estudio": str(plan.pk),
        "nombre": "Soldadura",
        "estado": "activo",
        **extra,
    }


def test_course_create_runs_the_native_view_and_its_guard(centro, plan):
    url = f"{ACCIONES}cursos/nuevo/"
    assert APIClient().post(url).status_code == 401
    assert _client("view_centro").post(f"{url}?centro={centro.pk}").status_code == 403
    editor = _client(*EDITOR)
    assert editor.get(f"{url}?centro={centro.pk}").status_code == 405
    # the native dispatch: no ``?centro=`` is a 403, and so is a centro out of the user's scope
    assert editor.post(url, _datos_curso(plan)).status_code == 403
    fuera = _client(*EDITOR, sse=False)
    assert (
        fuera.post(f"{url}?centro={centro.pk}", _datos_curso(plan)).status_code == 403
    )
    assert (
        _client(*EDITOR, csrf=True).post(f"{url}?centro={centro.pk}").status_code == 403
    )
    respuesta = editor.post(f"{url}?centro={centro.pk}", _datos_curso(plan))
    assert respuesta.status_code == 200, respuesta.content
    assert respuesta.json()["ok"] is True
    curso = Curso.objects.get(nombre="Soldadura")
    assert curso.centro_id == centro.pk and curso.plan_estudio_id == plan.pk


def test_course_create_rejection_answers_the_bound_form_and_stores_nothing(
    centro, plan
):
    editor = _client(*EDITOR)
    invalido = editor.post(
        f"{ACCIONES}cursos/nuevo/?centro={centro.pk}",
        {"plan_estudio": str(plan.pk), "estado": "activo", "nombre": ""},
    )
    assert invalido.status_code == 400
    datos = invalido.json()
    por_nombre = {f["name"]: f for f in datos["fields"]}
    assert por_nombre["nombre"]["errors"]
    assert datos["planes"][0]["etiqueta"] == "Electricidad"
    assert not Curso.objects.filter(centro=centro).exists()


def test_course_update_saves_through_the_native_view_and_keeps_its_scope(centro, plan):
    curso = _curso(centro, plan)
    editor = _client(*EDITOR)
    url = f"{ACCIONES}cursos/{curso.pk}/editar/"
    assert editor.get(url).status_code == 405
    assert APIClient().post(url).status_code == 401
    assert _client("view_centro").post(url).status_code == 403
    ok = editor.post(url, _datos_curso(plan, nombre="Electricidad avanzada"))
    assert ok.status_code == 200, ok.content
    curso.refresh_from_db()
    assert curso.nombre == "Electricidad avanzada"
    rechazado = editor.post(url, {**_datos_curso(plan), "nombre": ""})
    assert rechazado.status_code == 400
    curso.refresh_from_db()
    assert curso.nombre == "Electricidad avanzada"
    inexistente = editor.post(f"{ACCIONES}cursos/999999/editar/", _datos_curso(plan))
    assert inexistente.status_code == 404
    # a centro outside the user's scope is not in the native queryset
    assert _client(*EDITOR, sse=False).post(url, _datos_curso(plan)).status_code == 404
