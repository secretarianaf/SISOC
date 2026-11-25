"""V02.01: web API y entradas de vista previa de asistencia por sesión (``/api/web/vat/**/sesiones/<pk>/asistencia/``). Datos sintéticos."""

import itertools
import types
from datetime import date, time, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.test import Client, override_settings
from rest_framework.test import APIClient

from ciudadanos.models import Ciudadano
from config.urls_all import urlpatterns as monolith_patterns
from core.models import Dia, Localidad, Municipio, Programa, Provincia
from VAT.models import (
    AsistenciaSesion,
    Centro,
    Comision,
    ComisionCurso,
    ComisionHorario,
    Curso,
    Inscripcion,
    InstitucionUbicacion,
    ModalidadCursada,
    OfertaInstitucional,
    PlanVersionCurricular,
    Sector,
    SesionComision,
)
from VAT.web_preview_vat_asistencia import asistencia_preview_patterns

pytestmark = pytest.mark.django_db

_COUNTER = itertools.count()
INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)
MENSAJE = "Asistencia registrada exitosamente."


def _client(*codes, sse=False, csrf=False):
    user = get_user_model().objects.create_user(f"u{next(_COUNTER)}")
    user.user_permissions.add(
        *Permission.objects.filter(content_type__app_label="VAT", codename__in=codes)
    )
    if sse:
        permiso, _ = Permission.objects.get_or_create(
            content_type=ContentType.objects.get_for_model(Group),
            codename="role_vat_sse",
            defaults={"name": "VAT SSE"},
        )
        user.user_permissions.add(permiso)
    client = APIClient(enforce_csrf_checks=csrf)
    client.force_login(user)
    client.user = user
    return client


def _ciudadano(documento, apellido, nombre):
    return Ciudadano.objects.create(
        nombre=nombre,
        apellido=apellido,
        documento=documento,
        fecha_nacimiento=date(1990, 1, 1),
    )


@pytest.fixture(name="base")
def base_fixture():
    provincia = Provincia.objects.create(nombre="Buenos Aires")
    centro = Centro.objects.create(
        nombre="CFP 401", codigo="060144900", provincia=provincia
    )
    modalidad = ModalidadCursada.objects.create(nombre="Presencial")
    plan = PlanVersionCurricular.objects.create(
        nombre="Electricidad",
        provincia=provincia,
        sector=Sector.objects.create(nombre="Industria"),
        modalidad_cursada=modalidad,
        horas_reloj=100,
    )
    municipio = Municipio.objects.create(nombre="La Plata", provincia=provincia)
    ubicacion = InstitucionUbicacion.objects.create(
        centro=centro,
        localidad=Localidad.objects.create(nombre="Tolosa", municipio=municipio),
        rol_ubicacion="sede_principal",
        domicilio="7 123",
    )
    return {
        "centro": centro,
        "ubicacion": ubicacion,
        "modalidad": modalidad,
        "plan": plan,
        "dia": Dia.objects.create(nombre="Lunes"),
    }


@pytest.fixture(name="curso")
def curso_fixture(base):
    curso = Curso.objects.create(
        nombre="Electricidad básica",
        centro=base["centro"],
        plan_estudio=base["plan"],
        modalidad=base["modalidad"],
        inscripcion_libre=True,
    )
    comision = ComisionCurso.objects.create(
        curso=curso,
        ubicacion=base["ubicacion"],
        cupo_total=5,
        fecha_inicio=date.today() + timedelta(days=1),
        fecha_fin=date.today() + timedelta(days=40),
    )
    horario = ComisionHorario.objects.create(
        comision_curso=comision,
        dia_semana=base["dia"],
        hora_desde=time(9, 0),
        hora_hasta=time(12, 30),
    )
    sesion = SesionComision.objects.create(
        horario=horario,
        comision_curso=comision,
        numero_sesion=3,
        fecha=date(2026, 3, 9),
    )
    ana = Inscripcion.objects.create(
        ciudadano=_ciudadano(30111222, "Prueba", "Ana"),
        comision_curso=comision,
        estado="inscripta",
    )
    beto = Inscripcion.objects.create(
        ciudadano=_ciudadano(30111223, "Ejemplo", "Beto"),
        comision_curso=comision,
        estado="validada_presencial",
    )
    Inscripcion.objects.create(
        ciudadano=_ciudadano(30111224, "Fuera", "Cata"),
        comision_curso=comision,
        estado="preinscripta",
    )
    return {"comision": comision, "sesion": sesion, "ana": ana, "beto": beto}


@pytest.fixture(name="oferta")
def oferta_fixture(base):
    oferta = OfertaInstitucional.objects.create(
        centro=base["centro"],
        plan_curricular=base["plan"],
        programa=Programa.objects.create(nombre="Programa Sintetico"),
        ciclo_lectivo=2026,
    )
    comision = Comision.objects.create(
        oferta=oferta,
        codigo_comision="COM-001",
        nombre="Comision Uno",
        fecha_inicio=date(2026, 3, 1),
        fecha_fin=date(2026, 12, 1),
        cupo=10,
    )
    horario = ComisionHorario.objects.create(
        comision=comision,
        dia_semana=base["dia"],
        hora_desde=time(18, 0),
        hora_hasta=time(20, 0),
    )
    sesion = SesionComision.objects.create(
        horario=horario, comision=comision, numero_sesion=1, fecha=date(2026, 3, 2)
    )
    ana = Inscripcion.objects.create(
        ciudadano=_ciudadano(30222111, "Oferta", "Ana"),
        comision=comision,
        estado="inscripta",
    )
    return {"comision": comision, "sesion": sesion, "ana": ana}


def _urls(curso, oferta):
    return {
        "curso": f"/api/web/vat/cursos/comisiones/sesiones/{curso['sesion'].pk}/asistencia/",
        "oferta": f"/api/web/vat/comisiones/sesiones/{oferta['sesion'].pk}/asistencia/",
    }


def test_access_follows_the_native_route_rule_and_scope(curso, oferta):
    for url in _urls(curso, oferta).values():
        assert APIClient().get(url).status_code == 401
        assert APIClient().post(url).status_code == 401
        assert _client("view_asistenciasesion", sse=True).get(url).status_code == 403
        assert _client("view_asistenciasesion", sse=True).post(url).status_code == 403
        for code in ("add_asistenciasesion", "change_asistenciasesion"):
            assert _client(code, sse=True).get(url).status_code == 200
        # Without a role the native scoped lookup finds no session: 404, not 403.
        assert _client("add_asistenciasesion").get(url).status_code == 404
    assert (
        _client("add_asistenciasesion", sse=True)
        .get("/api/web/vat/cursos/comisiones/sesiones/999999/asistencia/")
        .status_code
        == 404
    )


def test_course_session_projects_the_native_context(curso, oferta):
    url = _urls(curso, oferta)["curso"]
    data = _client("add_asistenciasesion", sse=True).get(url).json()
    assert data["numero_sesion"] == 3
    assert data["comision_label"] == str(curso["sesion"].entidad_comision)
    assert data["curso"] == "Electricidad básica - CFP 401"
    assert data["estado"]
    assert data["horario"] == "09:00 a 12:30 hs"
    print(
        "DIA", repr(data["dia"]), [(f["apellido"], f["nombre"]) for f in data["filas"]]
    )
    assert data["totales"] == {"presentes": "0", "ausentes": "0", "sin_marcar": "2"}
    assert {(f["apellido"], f["nombre"], f["presente"]) for f in data["filas"]} == {
        ("Prueba", "Ana", None),
        ("Ejemplo", "Beto", None),
    }
    assert {f["tipo_alumno"] for f in data["filas"]} == {"Sin Plan"}
    assert not any(f["es_alumno_vat"] for f in data["filas"])
    assert data["messages"] == []


def test_offer_session_keeps_the_native_blanks(curso, oferta):
    data = (
        _client("change_asistenciasesion", sse=True)
        .get(_urls(curso, oferta)["oferta"])
        .json()
    )
    assert data["numero_sesion"] == 1
    assert data["comision_label"] == str(oferta["comision"])
    assert data["curso"] == ""
    assert data["estado"] == ""
    assert data["horario"] == "18:00 a 20:00 hs"
    assert data["totales"] == {"presentes": "", "ausentes": "", "sin_marcar": ""}
    assert [f["apellido"] for f in data["filas"]] == ["Oferta"]


def test_saved_marks_and_notes_are_projected_back(curso, oferta):
    AsistenciaSesion.objects.create(
        sesion=curso["sesion"],
        inscripcion=curso["ana"],
        presente=True,
        observaciones="Llegó tarde",
        registrado_por=get_user_model().objects.create_user("registrador"),
    )
    AsistenciaSesion.objects.create(
        sesion=curso["sesion"],
        inscripcion=curso["beto"],
        presente=False,
        registrado_por=get_user_model().objects.get(username="registrador"),
    )
    data = (
        _client("add_asistenciasesion", sse=True)
        .get(_urls(curso, oferta)["curso"])
        .json()
    )
    por_id = {f["id"]: f for f in data["filas"]}
    assert por_id[curso["ana"].pk]["presente"] is True
    assert por_id[curso["ana"].pk]["observaciones"] == "Llegó tarde"
    assert por_id[curso["beto"].pk]["presente"] is False
    assert data["totales"] == {"presentes": "1", "ausentes": "1", "sin_marcar": "0"}


def test_course_post_persists_every_active_row_and_queues_the_message(curso, oferta):
    client = _client("add_asistenciasesion", sse=True)
    url = _urls(curso, oferta)["curso"]
    response = client.post(
        url,
        {
            f"presente_{curso['ana'].pk}": "1",
            f"obs_{curso['ana'].pk}": " Con certificado ",
            f"presente_{curso['beto'].pk}": "0",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["redirect"] == f"/vat/cursos/comisiones/{curso['comision'].pk}/"
    marcas = {
        a.inscripcion_id: (a.presente, a.observaciones, a.registrado_por_id)
        for a in AsistenciaSesion.objects.filter(sesion=curso["sesion"])
    }
    assert marcas == {
        curso["ana"].pk: (True, "Con certificado", client.user.pk),
        curso["beto"].pk: (False, None, client.user.pk),
    }
    curso["sesion"].refresh_from_db()
    assert curso["sesion"].estado == "realizada"
    again = client.get(url).json()
    assert [m["message"] for m in again["messages"]] == [MENSAJE]
    assert client.get(url).json()["messages"] == []


def test_course_post_without_a_radio_marks_the_row_absent(curso, oferta):
    client = _client("change_asistenciasesion", sse=True)
    client.post(_urls(curso, oferta)["curso"], {f"presente_{curso['ana'].pk}": "1"})
    marcas = {
        a.inscripcion_id: a.presente
        for a in AsistenciaSesion.objects.filter(sesion=curso["sesion"])
    }
    assert marcas == {curso["ana"].pk: True, curso["beto"].pk: False}


def test_offer_post_updates_marks_and_flips_the_session_state(curso, oferta):
    client = _client("add_asistenciasesion", sse=True)
    url = _urls(curso, oferta)["oferta"]
    AsistenciaSesion.objects.create(
        sesion=oferta["sesion"],
        inscripcion=oferta["ana"],
        presente=False,
        registrado_por=get_user_model().objects.create_user("registrador"),
    )
    response = client.post(
        url, {f"presente_{oferta['ana'].pk}": "1", f"obs_{oferta['ana'].pk}": "ok"}
    )
    assert response.json() == {
        "ok": True,
        "redirect": f"/vat/comisiones/{oferta['comision'].pk}/",
    }
    marca = AsistenciaSesion.objects.get(sesion=oferta["sesion"])
    assert (marca.presente, marca.observaciones) == (True, "ok")
    oferta["sesion"].refresh_from_db()
    assert oferta["sesion"].estado == "realizada"
    assert [m["message"] for m in client.get(url).json()["messages"]] == [MENSAJE]


def test_rejected_writes_leave_everything_unchanged(curso, oferta):
    urls = _urls(curso, oferta)
    body = {f"presente_{curso['ana'].pk}": "1"}
    # No CSRF token, no permission, no scope, unknown session.
    assert (
        _client("add_asistenciasesion", sse=True, csrf=True)
        .post(urls["curso"], body)
        .status_code
        == 403
    )
    assert (
        _client("view_asistenciasesion", sse=True).post(urls["curso"], body).status_code
        == 403
    )
    assert _client("add_asistenciasesion").post(urls["curso"], body).status_code == 404
    assert _client("add_asistenciasesion").post(urls["oferta"], body).status_code == 404
    assert (
        _client("add_asistenciasesion", sse=True)
        .post("/api/web/vat/cursos/comisiones/sesiones/999999/asistencia/", body)
        .status_code
        == 404
    )
    assert AsistenciaSesion.objects.count() == 0
    curso["sesion"].refresh_from_db()
    oferta["sesion"].refresh_from_db()
    assert (curso["sesion"].estado, oferta["sesion"].estado) == (
        "programada",
        "programada",
    )


@pytest.mark.parametrize("variante", ["curso", "oferta"])
def test_projected_texts_are_the_ones_the_native_page_prints(variante, curso, oferta):
    from django.utils.html import escape  # pylint: disable=import-outside-toplevel

    api = _client("add_asistenciasesion", sse=True)
    nativo = Client()
    nativo.force_login(api.user)
    ruta = "cursos/comisiones" if variante == "curso" else "comisiones"
    sesion = (curso if variante == "curso" else oferta)["sesion"]
    url = f"sesiones/{sesion.pk}/asistencia/"
    html = nativo.get(f"/vat/{ruta}/{url}").content.decode()
    data = api.get(f"/api/web/vat/{ruta}/{url}").json()
    assert f"Registro de asistencia clase #{data['numero_sesion']}" in html
    assert escape(data["dia"]) in html and escape(data["horario"]) in html
    assert f"<h1>{escape(data['comision_label'])}</h1>" in html
    for fila in data["filas"]:
        assert f"<td>{escape(fila['apellido'])}</td>" in html
        assert f"<td>{escape(fila['nombre'])}</td>" in html
        assert f'name="presente_{fila["id"]}"' in html
    for clave, valor in data["totales"].items():
        etiqueta = {
            "presentes": "Presentes",
            "ausentes": "Ausentes",
            "sin_marcar": "SinMarcar",
        }[clave]
        assert f'id="asisMetric{etiqueta}">{valor}</strong>' in html


@pytest.fixture(name="preview")
def preview_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    (tmp_path / "assets" / "app-1.js").write_text("console.log(1);", encoding="utf-8")
    module = types.ModuleType("vat_asistencia_preview_test_urls")
    module.urlpatterns = asistencia_preview_patterns(tmp_path) + list(monolith_patterns)
    with override_settings(ROOT_URLCONF=module):
        yield


@pytest.mark.usefixtures("preview")
@pytest.mark.parametrize("variante", ["curso", "oferta"])
def test_entries_serve_the_frozen_index_behind_the_native_guards(
    variante, curso, oferta
):
    ruta = "cursos/comisiones" if variante == "curso" else "comisiones"
    sesion = (curso if variante == "curso" else oferta)["sesion"]
    url = f"/vat/{ruta}/sesiones/{sesion.pk}/asistencia/"
    response = _client("add_asistenciasesion", sse=True).get(url)
    assert response.status_code == 200
    body = response.content.decode()
    assert '/vat/react/assets/app-1.js"' in body
    assert "/v2/sisoc/assets/" not in body
    assert "no-store" in response["Cache-Control"]
    assert "csrftoken" in response.cookies
    assert _client("change_asistenciasesion", sse=True).get(url).status_code == 200
    assert _client("view_asistenciasesion", sse=True).get(url).status_code == 403
    assert Client().get(url).status_code == 403
    # The native scoped lookup still answers 404 outside the user's scope.
    assert _client("add_asistenciasesion").get(url).status_code == 404
    missing = f"/vat/{ruta}/sesiones/999999/asistencia/"
    assert _client("add_asistenciasesion", sse=True).get(missing).status_code == 404
