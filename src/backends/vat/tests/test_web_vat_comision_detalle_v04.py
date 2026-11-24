"""V04.01: web API y entradas de vista previa del detalle de comisión (``/api/web/vat/comisiones-detalle/``). Datos sintéticos."""

import itertools
import types
from datetime import date, time

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.test import Client, override_settings
from django.utils.html import escape
from rest_framework.test import APIClient

from ciudadanos.models import Ciudadano
from config.urls_all import urlpatterns as monolith_patterns
from core.models import Dia, Localidad, Municipio, Programa, Provincia
from VAT.models import (
    ActaCierreComision,
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
    ProfesorCentro,
    Sector,
    SesionComision,
)
from VAT.web_preview_vat_comision_detalle import comision_detalle_preview_patterns

pytestmark = pytest.mark.django_db

_COUNTER = itertools.count()
INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)


def _client(*codes, sse=False, visualizador=False, csrf=False):
    user = get_user_model().objects.create_user(f"u{next(_COUNTER)}")
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


def _ciudadano(documento, apellido, nombre, **extra):
    return Ciudadano.objects.create(
        nombre=nombre,
        apellido=apellido,
        documento=documento,
        fecha_nacimiento=date(1990, 1, 1),
        **extra,
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
        acepta_lista_espera=True,
        cupo_lista_espera=2,
        fecha_inicio=date(2026, 3, 1),
        fecha_fin=date(2026, 6, 30),
    )
    horario = ComisionHorario.objects.create(
        comision_curso=comision,
        dia_semana=base["dia"],
        hora_desde=time(9, 0),
        hora_hasta=time(12, 30),
        aula_espacio="Aula 2",
    )
    realizada = SesionComision.objects.create(
        horario=horario,
        comision_curso=comision,
        numero_sesion=1,
        fecha=date(2026, 3, 9),
        estado="realizada",
    )
    pendiente = SesionComision.objects.create(
        horario=horario,
        comision_curso=comision,
        numero_sesion=2,
        fecha=date(2026, 3, 16),
    )
    ana = Inscripcion.objects.create(
        ciudadano=_ciudadano(
            30111222, "Prueba", "Ana", email="ana@example.com", telefono="1155550000"
        ),
        comision_curso=comision,
        estado="inscripta",
    )
    beto = Inscripcion.objects.create(
        ciudadano=_ciudadano(30111223, "Ejemplo", "Beto"),
        comision_curso=comision,
        estado="pre_inscripta",
    )
    cata = Inscripcion.objects.create(
        ciudadano=_ciudadano(30111224, "Espera", "Cata"),
        comision_curso=comision,
        estado="en_espera",
    )
    registrador = get_user_model().objects.create_user("registrador")
    AsistenciaSesion.objects.create(
        sesion=realizada, inscripcion=ana, presente=True, registrado_por=registrador
    )
    return {
        "comision": comision,
        "horario": horario,
        "realizada": realizada,
        "pendiente": pendiente,
        "ana": ana,
        "beto": beto,
        "cata": cata,
    }


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
        vigente=False,
    )
    sesion = SesionComision.objects.create(
        horario=horario,
        comision=comision,
        numero_sesion=1,
        fecha=date(2026, 3, 2),
        estado="realizada",
    )
    ana = Inscripcion.objects.create(
        ciudadano=_ciudadano(30222111, "Oferta", "Ana"),
        comision=comision,
        estado="validada_presencial",
    )
    return {"comision": comision, "sesion": sesion, "ana": ana}


def _urls(curso, oferta):
    return {
        "curso": f"/api/web/vat/comisiones-detalle/cursos/{curso['comision'].pk}/",
        "oferta": f"/api/web/vat/comisiones-detalle/{oferta['comision'].pk}/",
    }


def test_access_follows_the_native_route_rule_and_scope(curso, oferta):
    urls = _urls(curso, oferta)
    for variante, url in urls.items():
        codigo = "view_comisioncurso" if variante == "curso" else "view_comision"
        otro = "view_comision" if variante == "curso" else "view_comisioncurso"
        assert APIClient().get(url).status_code == 401
        assert _client(otro, sse=True).get(url).status_code == 403
        assert _client(codigo, sse=True).get(url).status_code == 200
        assert _client(codigo, visualizador=True).get(url).status_code == 200
        # Without a role the native scoped queryset finds nothing: 404, not 403.
        assert _client(codigo).get(url).status_code == 404
        assert _client(codigo, sse=True).post(url).status_code == 405
    assert (
        _client("view_comisioncurso", sse=True)
        .get("/api/web/vat/comisiones-detalle/cursos/999999/")
        .status_code
        == 404
    )


def test_course_projects_the_native_context(curso, oferta):
    data = (
        _client("view_comisioncurso", sse=True)
        .get(_urls(curso, oferta)["curso"])
        .json()
    )
    comision = curso["comision"]
    assert data["tipo"] == "curso"
    assert data["id"] == comision.pk
    assert data["codigo"] == comision.codigo_comision
    assert data["titulo_tipo"] == "Comisión de Curso"
    assert data["subtitulo"] == "Electricidad básica"
    assert data["estado_label"] == comision.get_estado_display()
    assert data["acepta_lista_espera"] is True
    assert (data["cupo"], data["cupo_lista_espera"], data["cupo_ocupado"]) == (
        "5",
        "2",
        "2",
    )
    assert (data["fecha_inicio"], data["fecha_fin"]) == ("01/03/2026", "30/06/2026")
    assert data["ubicacion"] == str(curso["comision"].ubicacion)
    assert (data["clases_dictadas"], data["clases_pendientes"]) == ("1", "1")
    assert data["metricas"] == [
        {"valor": "100%", "label": "Asistencia general"},
        {"valor": "2", "label": "Clases Totales"},
        {"valor": "1", "label": "Clases dictadas"},
        {"valor": "1", "label": "Clases pendientes"},
        {"valor": "5", "label": "Cupo total"},
        {"valor": "2", "label": "Inscriptos"},
    ]
    assert data["horarios"] == [
        {
            "id": curso["horario"].pk,
            "dia": "Lunes",
            "dia_semana_id": curso["horario"].dia_semana_id,
            "desde": "09:00",
            "hasta": "12:30",
            "duracion": "3 hs 30 minutos",
            "aula_espacio": "Aula 2",
            "vigente": True,
            "update_url": f"/vat/cursos/comisiones/horarios/{curso['horario'].pk}/editar/",
            "delete_url": f"/vat/cursos/comisiones/horarios/{curso['horario'].pk}/eliminar/",
        }
    ]
    assert [
        (s["numero"], s["estado"], s["fecha"], s["presentes"], s["ausentes"])
        for s in data["sesiones"]
    ] == [
        (1, "realizada", "09 de marzo", "1", "0"),
        (2, "programada", "16 de marzo", "", ""),
    ]
    assert data["sesiones"][0]["asistencia_url"] == (
        f"/vat/cursos/comisiones/sesiones/{curso['realizada'].pk}/asistencia/"
    )
    por_id = {i["id"]: i for i in data["inscripciones"]}
    assert set(por_id) == {curso["ana"].pk, curso["beto"].pk}
    ana = por_id[curso["ana"].pk]
    assert (ana["apellido"], ana["nombre"], ana["busqueda"]) == (
        "Prueba",
        "Ana",
        "prueba ana",
    )
    assert ana["documento"].endswith("30111222") and ana["documento"].startswith("DNI")
    assert (ana["email"], ana["telefono"], ana["asistencia"]) == (
        "ana@example.com",
        "1155550000",
        "100",
    )
    assert (ana["tipo_alumno"], ana["es_alumno_vat"]) == ("Sin Plan", False)
    assert ana["estado"] == "inscripta" and ana["estado_label"] == "Inscripta"
    assert ana["detail_url"] == f"/vat/inscripciones/{curso['ana'].pk}/"
    beto = por_id[curso["beto"].pk]
    assert (beto["email"], beto["telefono"], beto["asistencia"]) == ("—", "—", None)
    assert [
        (e["id"], e["apellido"], e["fecha"], e["estado_label"])
        for e in data["lista_espera"]
    ] == [
        (
            curso["cata"].pk,
            "Espera",
            curso["cata"].fecha_inscripcion.astimezone().strftime("%d/%m/%Y"),
            "En Espera",
        )
    ]
    assert data["messages"] == []


def test_offer_keeps_the_native_blanks(curso, oferta):
    data = _client("view_comision", sse=True).get(_urls(curso, oferta)["oferta"]).json()
    assert data["tipo"] == "oferta"
    assert data["titulo_tipo"] == "Comisión"
    assert data["codigo"] == "COM-001" and data["nombre"] == "Comision Uno"
    assert data["subtitulo"] == str(oferta["comision"].oferta)
    assert data["acepta_lista_espera"] is False
    assert data["cupo_lista_espera"] == "—"
    assert data["metricas"] == []
    assert (data["clases_dictadas"], data["clases_pendientes"]) == ("", "")
    assert [(s["estado"], s["presentes"], s["ausentes"]) for s in data["sesiones"]] == [
        ("realizada", "", "")
    ]
    assert data["horarios"][0]["vigente"] is False
    assert data["horarios"][0]["aula_espacio"] == ""
    assert data["horarios"][0]["update_url"] == (
        f"/vat/comisiones/horarios/{data['horarios'][0]['id']}/editar/"
    )
    assert data["urls"]["horario_nuevo"] == (
        f"/vat/comisiones/horarios/nuevo/?comision={oferta['comision'].pk}"
    )
    assert data["urls"]["exportar_inscriptos"] is None
    assert data["inscripciones"][0]["asistencia"] is None
    assert data["inscripciones"][0]["estado"] == "validada_presencial"
    assert data["resultados"] is None


def test_permissions_and_urls_follow_the_native_flags(curso, oferta):
    url = _urls(curso, oferta)["curso"]
    solo_lectura = _client("view_comisioncurso", visualizador=True).get(url).json()
    assert not any(solo_lectura["permisos"].values())
    assert solo_lectura["resultados"] is None
    # The exports follow ``view_comisioncurso`` alone, not the management flag.
    assert solo_lectura["urls"]["exportar_inscriptos"] == (
        f"/vat/cursos/comisiones/{curso['comision'].pk}/descargar-nomina-inscriptos/"
    )
    gestor = (
        _client(
            "view_comisioncurso",
            "change_inscripcion",
            "delete_inscripcion",
            "add_comisionhorario",
            "delete_comisioncurso",
            sse=True,
        )
        .get(url)
        .json()
    )
    permisos = gestor["permisos"]
    assert permisos["gestionar_comision"] and permisos["eliminar_comision"]
    assert permisos["cambiar_inscripcion"] and permisos["gestionar_lote_inscriptos"]
    assert permisos["eliminar_inscripcion"] and permisos["gestionar_asistencia"]
    assert permisos["agregar_comision_horario"] and permisos["gestionar_resultados"]
    assert not permisos["editar_comision"] and not permisos["agregar_inscripcion"]
    assert not permisos["editar_comision_horario"]
    assert gestor["urls"]["eliminar"] == (
        f"/vat/cursos/comisiones/{curso['comision'].pk}/eliminar/"
    )
    assert gestor["urls"]["horario_nuevo"] == (
        f"/vat/cursos/comisiones/horarios/nuevo/?comision_curso={curso['comision'].pk}"
    )


def test_results_tab_projects_the_acta_and_the_graded_students(curso, oferta):
    profesor = ProfesorCentro.objects.create(
        centro=curso["comision"].curso.centro,
        apellido="Docente",
        nombre="Dora",
        documento=20111222,
        email="dora@example.com",
    )
    ActaCierreComision.objects.create(
        comision_curso=curso["comision"],
        profesor=profesor,
        fecha_fin=date(2026, 7, 15),
        numero_acta="0245/2026",
        registrado_por=get_user_model().objects.get(username="registrador"),
    )
    curso["ana"].resultado_final = Inscripcion.RESULTADO_APROBADO
    curso["ana"].save(update_fields=["resultado_final"])
    data = (
        _client("view_comisioncurso", "change_inscripcion", sse=True)
        .get(_urls(curso, oferta)["curso"])
        .json()["resultados"]
    )
    assert (data["aprobado"], data["desaprobado"]) == ("aprobado", "desaprobado")
    assert data["resumen"] == {
        "aprobados": "1",
        "desaprobados": "0",
        "sin_calificar": "0",
        "inscriptos": "1",
    }
    assert [(a["id"], a["apellido"], a["resultado"]) for a in data["alumnos"]] == [
        (curso["ana"].pk, "Prueba", "aprobado")
    ]
    assert data["profesor_id"] == profesor.pk
    assert data["profesor_texto"] == "Docente, Dora — DNI 20111222 — dora@example.com"
    assert (data["fecha_fin"], data["numero_acta"]) == ("2026-07-15", "0245/2026")


def test_results_tab_without_acta_preloads_the_commission_end(curso, oferta):
    data = (
        _client("view_comisioncurso", "change_inscripcion", sse=True)
        .get(_urls(curso, oferta)["curso"])
        .json()["resultados"]
    )
    assert data["profesor_id"] is None and data["profesor_texto"] == ""
    assert (data["fecha_fin"], data["numero_acta"]) == ("2026-06-30", "")


def test_queued_messages_are_consumed_once(curso, oferta):
    client = _client("view_comisioncurso", "change_inscripcion", sse=True)
    respuesta = client.post(
        f"/api/web/vat/inscripciones-persona/cursos/{curso['beto'].pk}/cambiar-estado/",
        {"estado": "inscripta"},
    )
    assert respuesta.status_code == 200
    url = _urls(curso, oferta)["curso"]
    mensajes = client.get(url).json()["messages"]
    assert len(mensajes) == 1 and mensajes[0]["level"] == "success"
    assert client.get(url).json()["messages"] == []


@pytest.mark.parametrize("variante", ["curso", "oferta"])
def test_projected_texts_are_the_ones_the_native_page_prints(variante, curso, oferta):
    api = _client("view_comisioncurso", "view_comision", "change_inscripcion", sse=True)
    nativo = Client()
    nativo.force_login(api.user)
    es_curso = variante == "curso"
    comision = (curso if es_curso else oferta)["comision"]
    prefijo = "cursos/" if es_curso else ""
    html = nativo.get(f"/vat/{prefijo}comisiones/{comision.pk}/").content.decode()
    data = api.get(f"/api/web/vat/comisiones-detalle/{prefijo}{comision.pk}/").json()
    assert f"<h1>{escape(data['nombre'])}</h1>" in html
    assert escape(data["subtitulo"]) in html
    assert (
        f'<span class="sisoc-status-pill">{escape(data["estado_label"])}</span>' in html
    )
    for etiqueta, valor in (
        ("Ubicación", data["ubicacion"]),
        ("Fecha de inicio", data["fecha_inicio"]),
        ("Fecha de finalización", data["fecha_fin"]),
        ("Cupo", data["cupo"]),
        ("Inscriptos", data["cupo_ocupado"]),
    ):
        assert f'<p class="sisoc-data-label">{etiqueta}</p>\n' in html
        assert f'<p class="sisoc-data-value">{escape(valor)}</p>' in html
    for metrica in data["metricas"]:
        assert f'<strong class="sisoc-metric-value">{metrica["valor"]}</strong>' in html
    for fila in data["inscripciones"]:
        assert f">{escape(fila['apellido'])}</a>" in html
        assert f"<td>{escape(fila['documento'])}</td>" in html
        assert f'data-nombre="{escape(fila["busqueda"])}"' in html
    for horario in data["horarios"]:
        assert f"{horario['desde']} a {horario['hasta']}" in html
        assert escape(horario["duracion"]) in html
    for sesion in data["sesiones"]:
        assert f"<td>Clase {sesion['numero']}</td>" in html
        assert f"<td>{escape(sesion['fecha'])}</td>" in html
    for fila in data["lista_espera"]:
        assert f"<td>{escape(fila['fecha'])}</td>" in html


def _resultados_url(curso, sufijo="resultados/"):
    return f"/api/web/vat/comisiones-detalle/cursos/{curso['comision'].pk}/{sufijo}"


def _profesor(curso, documento=20111222):
    return ProfesorCentro.objects.create(
        centro=curso["comision"].curso.centro,
        apellido="Docente",
        nombre="Dora",
        documento=documento,
        email="dora@example.com",
    )


def test_modal_forms_are_projected_only_for_who_can_use_them(curso, oferta):
    url = _urls(curso, oferta)["curso"]
    gestor = _client(
        "view_comisioncurso", "add_inscripcion", "change_inscripcion", sse=True
    )
    formularios = gestor.get(url).json()["formularios"]
    assert [c["name"] for c in formularios["rapida"]] == [
        "apellido",
        "nombre",
        "tipo_documento",
        "documento",
        "fecha_nacimiento",
        "sexo",
    ]
    tipo = formularios["rapida"][2]
    assert (tipo["tag"], tipo["value"], tipo["id"]) == (
        "select",
        "DNI",
        "id_tipo_documento",
    )
    assert [c["value"] for c in tipo["choices"]] == ["DNI", "PASAPORTE"]
    assert formularios["rapida"][4]["attrs"]["type"] == "date"
    assert [c["name"] for c in formularios["profesor"]] == [
        "apellido",
        "nombre",
        "documento",
        "email",
    ]
    solo = _client("view_comisioncurso", visualizador=True).get(url).json()
    assert solo["formularios"] == {"rapida": None, "profesor": None}
    sola_rapida = _client("view_comisioncurso", "add_inscripcion", sse=True)
    assert sola_rapida.get(url).json()["formularios"]["profesor"] is None


def test_results_post_saves_the_acta_and_the_grades_and_queues_the_message(curso):
    client = _client("view_comisioncurso", "change_inscripcion", sse=True)
    profesor = _profesor(curso)
    response = client.post(
        _resultados_url(curso),
        {
            "profesor": profesor.pk,
            "fecha_fin": "2026-07-15",
            "numero_acta": " 0245/2026 ",
            f"resultado_{curso['ana'].pk}": "aprobado",
            f"resultado_{curso['beto'].pk}": "desaprobado",
        },
    )
    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "redirect": f"/vat/cursos/comisiones/{curso['comision'].pk}/#resultados",
    }
    acta = ActaCierreComision.objects.get(comision_curso=curso["comision"])
    assert (acta.profesor_id, acta.fecha_fin, acta.numero_acta) == (
        profesor.pk,
        date(2026, 7, 15),
        "0245/2026",
    )
    assert acta.registrado_por_id == client.user.pk
    curso["ana"].refresh_from_db()
    assert curso["ana"].resultado_final == "aprobado"
    mensajes = client.get(_resultados_url(curso, "")).json()["messages"]
    assert [m["message"] for m in mensajes] == [
        "Resultados guardados: 1 calificación actualizada."
    ]


def test_results_post_rejections_leave_everything_unchanged(curso):
    profesor = _profesor(curso)
    body = {"profesor": profesor.pk, "fecha_fin": "2026-07-15"}
    url = _resultados_url(curso)
    assert APIClient().post(url, body).status_code == 401
    assert _client("view_comisioncurso", sse=True).post(url, body).status_code == 403
    assert (
        _client("change_inscripcion", sse=True, csrf=True).post(url, body).status_code
        == 403
    )
    assert _client("change_inscripcion").post(url, body).status_code == 404
    assert _client("change_inscripcion", sse=True).get(url).status_code == 405
    assert (
        _client("change_inscripcion", sse=True)
        .post("/api/web/vat/comisiones-detalle/cursos/999999/resultados/", body)
        .status_code
        == 404
    )
    assert not ActaCierreComision.objects.exists()


def test_results_post_without_teacher_keeps_the_native_error_and_writes_nothing(curso):
    client = _client("view_comisioncurso", "change_inscripcion", sse=True)
    response = client.post(
        _resultados_url(curso),
        {"fecha_fin": "2026-07-15", f"resultado_{curso['ana'].pk}": "aprobado"},
    )
    assert response.json()["redirect"].endswith("#resultados")
    assert not ActaCierreComision.objects.exists()
    curso["ana"].refresh_from_db()
    assert curso["ana"].resultado_final in (None, "")
    mensajes = client.get(_resultados_url(curso, "")).json()["messages"]
    assert [m["level"] for m in mensajes] == ["error"]


def test_teacher_search_returns_the_native_json_inside_the_scope(curso):
    profesor = _profesor(curso)
    otro = _profesor(curso, documento=20999888)
    otro.apellido = "Zapata"
    otro.save()
    client = _client("change_inscripcion", sse=True)
    url = _resultados_url(curso, "profesores/buscar/")
    resultados = client.get(url, {"q": "doc"}).json()["results"]
    assert [r["id"] for r in resultados] == [profesor.pk]
    assert resultados[0]["text"].startswith("Docente, Dora")
    assert [r["id"] for r in client.get(url, {"q": "20999"}).json()["results"]] == [
        otro.pk
    ]
    assert APIClient().get(url).status_code == 401
    assert _client("view_comisioncurso", sse=True).get(url).status_code == 403
    assert _client("change_inscripcion").get(url).status_code == 404
    assert client.post(url).status_code == 405


def test_teacher_creation_persists_and_returns_the_selected_teacher(curso):
    client = _client("change_inscripcion", sse=True)
    url = _resultados_url(curso, "profesores/nuevo/")
    response = client.post(
        url,
        {
            "apellido": "Docente",
            "nombre": "Dora",
            "documento": "20111222",
            "email": "dora@example.com",
        },
    )
    assert response.status_code == 200
    profesor = ProfesorCentro.objects.get()
    assert profesor.centro_id == curso["comision"].curso.centro_id
    assert response.json()["profesor"]["id"] == profesor.pk
    repetido = client.post(
        url,
        {
            "apellido": "Otro",
            "nombre": "Oto",
            "documento": "20111222",
            "email": "o@example.com",
        },
    )
    assert repetido.status_code == 400
    cuerpo = repetido.json()
    assert cuerpo["ok"] is False and "documento" in cuerpo["errors"]
    assert ProfesorCentro.objects.count() == 1
    assert (
        _client("change_inscripcion", sse=True, csrf=True).post(url, {}).status_code
        == 403
    )
    assert _client("change_inscripcion").post(url, {}).status_code == 404
    assert ProfesorCentro.objects.count() == 1


@pytest.fixture(name="preview")
def preview_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    (tmp_path / "assets" / "app-1.js").write_text("console.log(1);", encoding="utf-8")
    module = types.ModuleType("vat_comision_detalle_preview_test_urls")
    module.urlpatterns = comision_detalle_preview_patterns(tmp_path) + list(
        monolith_patterns
    )
    with override_settings(ROOT_URLCONF=module):
        yield


@pytest.mark.usefixtures("preview")
@pytest.mark.parametrize("variante", ["curso", "oferta"])
def test_entries_serve_the_frozen_index_behind_the_native_guards(
    variante, curso, oferta
):
    es_curso = variante == "curso"
    comision = (curso if es_curso else oferta)["comision"]
    codigo, otro = (
        ("view_comisioncurso", "view_comision")
        if es_curso
        else ("view_comision", "view_comisioncurso")
    )
    url = f"/vat/{'cursos/' if es_curso else ''}comisiones/{comision.pk}/"
    response = _client(codigo, sse=True).get(url)
    assert response.status_code == 200
    body = response.content.decode()
    assert '/vat/react/assets/app-1.js"' in body
    assert "/v2/sisoc/assets/" not in body
    assert "no-store" in response["Cache-Control"]
    assert "csrftoken" in response.cookies
    assert _client(otro, sse=True).get(url).status_code == 403
    assert Client().get(url).status_code == 403
    # The native scoped queryset still answers 404 outside the user's scope.
    assert _client(codigo).get(url).status_code == 404
    missing = f"/vat/{'cursos/' if es_curso else ''}comisiones/999999/"
    assert _client(codigo, sse=True).get(missing).status_code == 404


@pytest.mark.usefixtures("preview")
def test_the_sibling_native_screens_are_not_claimed(curso, oferta):
    cliente = _client("view_comisioncurso", "add_asistenciasesion", sse=True)
    pagina = cliente.get(f"/vat/cursos/comisiones/{curso['comision'].pk}/eliminar/")
    assert b"/v2/sisoc/assets/" not in pagina.content
    assert "/vat/react/assets/app-1.js" not in pagina.content.decode()
    asistencia = cliente.get(
        f"/vat/cursos/comisiones/sesiones/{curso['realizada'].pk}/asistencia/"
    )
    assert "/vat/react/assets/app-1.js" not in asistencia.content.decode()
