"""V04.02 (U5): web API y entradas de vista previa de las comisiones de oferta y de curso (``/api/web/vat/comisiones-formularios/``). Datos sintéticos."""

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

from config.urls_all import urlpatterns as monolith_patterns
from core.models import Dia, Localidad, Municipio, Programa, Provincia
from VAT.models import (
    Centro,
    Comision,
    ComisionCurso,
    ComisionHorario,
    Curso,
    InstitucionUbicacion,
    ModalidadCursada,
    OfertaInstitucional,
    PlanVersionCurricular,
    Sector,
    SesionComision,
)
from VAT.web_preview_vat_comision_forms import comision_forms_preview_patterns

pytestmark = pytest.mark.django_db

_COUNTER = itertools.count()
INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)
OFERTA = "/api/web/vat/comisiones-formularios/"
CURSO = "/api/web/vat/comisiones-formularios/cursos/"
CAMPOS_OFERTA = [
    "oferta",
    "ubicacion",
    "codigo_comision",
    "nombre",
    "fecha_inicio",
    "fecha_fin",
    "cupo",
    "estado",
    "observaciones",
]
CAMPOS_CURSO = [
    "curso",
    "ubicacion",
    "cupo_total",
    "acepta_lista_espera",
    "cupo_lista_espera",
    "fecha_inicio",
    "fecha_fin",
    "estado",
    "observaciones",
]


def _client(*codes, sse=False, csrf=False):
    user = get_user_model().objects.create_user(f"u{next(_COUNTER)}")
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
    client.user = user
    return client


@pytest.fixture(name="base")
def base_fixture():
    provincia = Provincia.objects.create(nombre="Buenos Aires")
    centro = Centro.objects.create(
        nombre="CFP 401", codigo="060144900", provincia=provincia
    )
    otro = Centro.objects.create(
        nombre="CFP 402", codigo="060144901", provincia=provincia
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
    localidad = Localidad.objects.create(nombre="Tolosa", municipio=municipio)
    ubicacion = InstitucionUbicacion.objects.create(
        centro=centro,
        localidad=localidad,
        rol_ubicacion="sede_principal",
        domicilio="7 123",
    )
    ubicacion_otro = InstitucionUbicacion.objects.create(
        centro=otro,
        localidad=localidad,
        rol_ubicacion="sede_principal",
        domicilio="8 1",
    )
    return {
        "centro": centro,
        "otro": otro,
        "ubicacion": ubicacion,
        "ubicacion_otro": ubicacion_otro,
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
        fecha_inicio=date(2026, 3, 1),
        fecha_fin=date(2026, 6, 30),
    )
    return {"curso": curso, "comision": comision}


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
        fecha_fin=date(2026, 3, 31),
        cupo=10,
    )
    horario = ComisionHorario.objects.create(
        comision=comision,
        dia_semana=base["dia"],
        hora_desde=time(18, 0),
        hora_hasta=time(20, 0),
        vigente=True,
    )
    return {"oferta": oferta, "comision": comision, "horario": horario}


def _post_oferta(base, oferta, **cambios):
    datos = {
        "oferta": oferta["oferta"].pk,
        "ubicacion": base["ubicacion"].pk,
        "codigo_comision": "COM-002",
        "nombre": "Comision Dos",
        "fecha_inicio": "2026-04-01",
        "fecha_fin": "2026-04-30",
        "cupo": 12,
        "estado": "activa",
        "observaciones": "Notas",
    }
    datos.update(cambios)
    return datos


def _post_curso(base, curso, **cambios):
    datos = {
        "curso": curso["curso"].pk,
        "ubicacion": base["ubicacion"].pk,
        "cupo_total": 8,
        "fecha_inicio": "2026-04-01",
        "fecha_fin": "2026-04-30",
        "estado": "planificada",
        "observaciones": "",
    }
    datos.update(cambios)
    return datos


def _mensajes(cliente, curso, oferta):
    urls = (
        f"/api/web/vat/comisiones-detalle/cursos/{curso['comision'].pk}/",
        f"/api/web/vat/comisiones-detalle/{oferta['comision'].pk}/",
    )
    return [
        (m["message"], m["level"])
        for url in urls
        for m in cliente.get(url).json().get("messages", [])
    ]


def _variantes(curso, oferta):
    return (
        ("oferta", OFERTA, "comision", oferta["comision"]),
        ("curso", CURSO, "comisioncurso", curso["comision"]),
    )


def test_access_follows_each_native_route_rule_and_scope(base, curso, oferta):
    del base
    for _nombre, raiz, modelo, objeto in _variantes(curso, oferta):
        rutas = {
            "nueva/": "add",
            f"{objeto.pk}/editar/": "change",
            f"{objeto.pk}/eliminar/": "delete",
        }
        for sufijo, accion in rutas.items():
            url = raiz + sufijo
            assert APIClient().get(url).status_code == 401, url
            for otra in {"add", "change", "delete"} - {accion}:
                assert _client(f"{otra}_{modelo}", sse=True).get(url).status_code == 403
            assert _client(f"{accion}_{modelo}", sse=True).get(url).status_code == 200
            if sufijo != "nueva/":
                # Fuera de alcance (sin rol de alcance global) la vista nativa da 404.
                assert _client(f"{accion}_{modelo}").get(url).status_code == 404
                faltante = raiz + sufijo.replace(str(objeto.pk), "999999")
                assert (
                    _client(f"{accion}_{modelo}", sse=True).get(faltante).status_code
                    == 404
                )


def test_forms_project_the_native_fields_and_the_initial_values(base, curso, oferta):
    del base
    cliente = _client(
        "add_comision",
        "change_comision",
        "add_comisioncurso",
        "change_comisioncurso",
        sse=True,
    )
    nueva = cliente.get(OFERTA + "nueva/", {"oferta": oferta["oferta"].pk}).json()
    assert nueva["editing"] is False and nueva["subtitulo"] == ""
    assert [f["name"] for f in nueva["fields"]] == CAMPOS_OFERTA
    assert nueva["fields"][0]["value"] == str(oferta["oferta"].pk)
    assert "select2" in nueva["fields"][0]["attrs"]["class"]
    assert nueva["urls"] == {"list": "/vat/comisiones/", "detail": ""}
    editar = cliente.get(OFERTA + f"{oferta['comision'].pk}/editar/").json()
    por_nombre = {f["name"]: f for f in editar["fields"]}
    assert editar["editing"] is True and editar["subtitulo"] == "COM-001 — Comision Uno"
    # Defecto nativo conservado: el widget imprime la fecha localizada (``d/m/Y``), que ``<input type="date">`` no admite.
    assert (por_nombre["fecha_inicio"]["value"], por_nombre["cupo"]["value"]) == (
        "01/03/2026",
        "10",
    )
    assert editar["urls"]["detail"] == f"/vat/comisiones/{oferta['comision'].pk}/"
    nueva_curso = cliente.get(CURSO + "nueva/", {"curso": curso["curso"].pk}).json()
    assert [f["name"] for f in nueva_curso["fields"]] == CAMPOS_CURSO
    assert nueva_curso["fields"][0]["value"] == str(curso["curso"].pk)
    assert nueva_curso["urls"]["cancel"] == ""
    editar_curso = cliente.get(CURSO + f"{curso['comision'].pk}/editar/").json()
    assert (
        editar_curso["urls"]["cancel"]
        == f"/vat/centros/{curso['curso'].centro_id}/#cursos"
    )


def test_create_persists_and_queues_the_native_message(base, curso, oferta):
    cliente = _client(
        "add_comision",
        "add_comisioncurso",
        "view_comision",
        "view_comisioncurso",
        sse=True,
    )
    respuesta = cliente.post(OFERTA + "nueva/", _post_oferta(base, oferta))
    assert respuesta.status_code == 200, respuesta.content
    creada = Comision.objects.get(codigo_comision="COM-002")
    assert (creada.cupo, creada.estado, creada.acepta_lista_espera) == (
        12,
        "activa",
        False,
    )
    assert respuesta.json() == {"ok": True, "redirect": f"/vat/comisiones/{creada.pk}/"}
    respuesta = cliente.post(
        CURSO + "nueva/",
        _post_curso(base, curso, acepta_lista_espera="on", cupo_lista_espera=3),
    )
    assert respuesta.status_code == 200, respuesta.content
    nueva = ComisionCurso.objects.exclude(pk=curso["comision"].pk).get()
    assert (nueva.cupo_total, nueva.acepta_lista_espera, nueva.cupo_lista_espera) == (
        8,
        True,
        3,
    )
    assert respuesta.json() == {
        "ok": True,
        "redirect": f"/vat/centros/{base['centro'].pk}/?refresh=1#cursos",
    }
    mensajes = _mensajes(cliente, curso, oferta)
    assert ("Comisión creada exitosamente.", "success") in mensajes
    assert ("Comision del curso creada exitosamente.", "success") in mensajes


def test_invalid_post_is_400_with_errors_and_writes_nothing(base, curso, oferta):
    cliente = _client(
        "add_comision",
        "add_comisioncurso",
        "change_comision",
        "change_comisioncurso",
        sse=True,
    )
    antes = (Comision.objects.count(), ComisionCurso.objects.count())
    rechazo = cliente.post(
        OFERTA + "nueva/", {"oferta": oferta["oferta"].pk, "nombre": "x"}
    )
    assert rechazo.status_code == 400
    errores = {f["name"]: f["errors"] for f in rechazo.json()["fields"]}
    assert errores["codigo_comision"] and errores["cupo"] and not errores["oferta"]
    fechas = cliente.post(
        CURSO + "nueva/",
        _post_curso(base, curso, fecha_inicio="2026-05-01", fecha_fin="2026-04-01"),
    )
    assert fechas.status_code == 400
    assert {f["name"]: f["errors"] for f in fechas.json()["fields"]}["fecha_fin"] == [
        "La fecha de fin debe ser mayor o igual a la fecha de inicio."
    ]
    ajena = cliente.post(
        CURSO + "nueva/", _post_curso(base, curso, ubicacion=base["ubicacion_otro"].pk)
    )
    assert ajena.status_code == 400
    assert (Comision.objects.count(), ComisionCurso.objects.count()) == antes
    rechazo = cliente.post(
        OFERTA + f"{oferta['comision'].pk}/editar/",
        _post_oferta(base, oferta, cupo="x"),
    )
    assert rechazo.status_code == 400
    oferta["comision"].refresh_from_db()
    assert oferta["comision"].cupo == 10


def test_update_regenerates_the_classes_only_when_the_dates_change(base, curso, oferta):
    cliente = _client(
        "change_comision",
        "change_comisioncurso",
        "view_comision",
        "view_comisioncurso",
        sse=True,
    )
    comision = oferta["comision"]
    SesionComision.objects.create(
        horario=oferta["horario"],
        comision=comision,
        numero_sesion=1,
        fecha=date(2026, 3, 2),
    )
    sin_fechas = _post_oferta(
        base,
        oferta,
        codigo_comision="COM-001",
        nombre="Renombrada",
        fecha_inicio="2026-03-01",
        fecha_fin="2026-03-31",
    )
    assert (
        cliente.post(OFERTA + f"{comision.pk}/editar/", sin_fechas).status_code == 200
    )
    comision.refresh_from_db()
    assert (comision.nombre, comision.cupo, comision.estado) == (
        "Renombrada",
        12,
        "activa",
    )
    assert SesionComision.objects.filter(comision=comision).count() == 1
    assert SesionComision.objects.get(comision=comision).fecha == date(2026, 3, 2)
    con_fechas = {**sin_fechas, "fecha_fin": "2026-03-15"}
    respuesta = cliente.post(OFERTA + f"{comision.pk}/editar/", con_fechas)
    assert respuesta.json() == {"ok": True, "redirect": "/vat/comisiones/"}
    fechas = list(
        SesionComision.objects.filter(comision=comision).values_list("fecha", flat=True)
    )
    assert fechas and max(fechas) <= date(2026, 3, 15)
    assert ("Comisión actualizada exitosamente.", "success") in _mensajes(
        cliente, curso, oferta
    )
    editado = cliente.post(
        CURSO + f"{curso['comision'].pk}/editar/",
        _post_curso(base, curso, cupo_total=20),
    )
    assert editado.json() == {
        "ok": True,
        "redirect": f"/vat/centros/{base['centro'].pk}/?refresh=1#cursos",
    }
    curso["comision"].refresh_from_db()
    assert curso["comision"].cupo_total == 20
    assert ("Comision del curso actualizada exitosamente.", "success") in _mensajes(
        cliente, curso, oferta
    )


def test_update_without_acepta_lista_espera_resets_it_like_the_native_page(
    base, curso, oferta
):
    # La plantilla nativa de la oferta no dibuja ``acepta_lista_espera``: al guardar queda en falso (paridad).
    del curso
    oferta["comision"].acepta_lista_espera = True
    oferta["comision"].save()
    cliente = _client("change_comision", sse=True)
    post = _post_oferta(base, oferta, codigo_comision="COM-001", fecha_fin="2026-03-31")
    assert (
        cliente.post(OFERTA + f"{oferta['comision'].pk}/editar/", post).status_code
        == 200
    )
    oferta["comision"].refresh_from_db()
    assert oferta["comision"].acepta_lista_espera is False


def test_delete_is_the_native_soft_delete_and_keeps_the_scope(base, curso, oferta):
    del base
    cliente = _client(
        "delete_comision",
        "delete_comisioncurso",
        "view_comision",
        "view_comisioncurso",
        sse=True,
    )
    ajeno = _client("delete_comision", "delete_comisioncurso")
    assert ajeno.post(OFERTA + f"{oferta['comision'].pk}/eliminar/").status_code == 404
    assert ajeno.post(CURSO + f"{curso['comision'].pk}/eliminar/").status_code == 404
    assert Comision.objects.filter(pk=oferta["comision"].pk).exists()
    baja = cliente.post(OFERTA + f"{oferta['comision'].pk}/eliminar/")
    assert baja.json() == {"ok": True, "redirect": "/vat/comisiones/"}
    assert not Comision.objects.filter(pk=oferta["comision"].pk).exists()
    assert Comision.all_objects.filter(pk=oferta["comision"].pk).exists()
    baja = cliente.post(CURSO + f"{curso['comision'].pk}/eliminar/")
    assert baja.json() == {
        "ok": True,
        "redirect": f"/vat/centros/{curso['curso'].centro_id}/?refresh=1#cursos",
    }
    assert not ComisionCurso.objects.filter(pk=curso["comision"].pk).exists()
    assert cliente.post(OFERTA + "999999/eliminar/").status_code == 404


def test_delete_page_texts_are_the_ones_the_native_page_prints(base, curso, oferta):
    del base
    api = _client("delete_comision", "delete_comisioncurso", sse=True)
    nativo = Client()
    nativo.force_login(api.user)
    datos = api.get(OFERTA + f"{oferta['comision'].pk}/eliminar/").json()
    html = nativo.get(
        f"/vat/comisiones/{oferta['comision'].pk}/eliminar/"
    ).content.decode()
    assert datos["titulo"] == "COM-001 - Comision Uno"
    assert escape(datos["titulo"]) in html and escape(datos["subtitulo"]) in html
    assert datos["urls"]["detail"] == f"/vat/comisiones/{oferta['comision'].pk}/"
    datos = api.get(CURSO + f"{curso['comision'].pk}/eliminar/").json()
    html = nativo.get(
        f"/vat/cursos/comisiones/{curso['comision'].pk}/eliminar/"
    ).content.decode()
    assert escape(datos["titulo"]) in html
    assert datos["urls"]["detail"] == f"/vat/centros/{curso['curso'].centro_id}/#cursos"


def test_course_create_keeps_the_native_curso_guard(base, curso, oferta):
    del oferta
    lector = _client("add_comisioncurso")
    assert lector.get(CURSO + "nueva/", {"curso": curso["curso"].pk}).status_code == 403
    assert lector.post(CURSO + "nueva/", _post_curso(base, curso)).status_code == 403
    sse = _client("add_comisioncurso", sse=True)
    assert sse.get(CURSO + "nueva/", {"curso": 999999}).status_code == 403
    assert sse.get(CURSO + "nueva/").status_code == 200
    assert ComisionCurso.objects.count() == 1


def test_writes_without_csrf_or_login_change_nothing(base, curso, oferta):
    del base
    cliente = _client("delete_comision", "delete_comisioncurso", sse=True, csrf=True)
    for url in (
        OFERTA + f"{oferta['comision'].pk}/eliminar/",
        CURSO + f"{curso['comision'].pk}/eliminar/",
    ):
        assert cliente.post(url).status_code == 403
        assert APIClient().post(url).status_code in (401, 403)
    assert Comision.objects.filter(pk=oferta["comision"].pk).exists()
    assert ComisionCurso.objects.filter(pk=curso["comision"].pk).exists()


@pytest.fixture(name="preview")
def preview_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    (tmp_path / "assets" / "app-1.js").write_text("console.log(1);", encoding="utf-8")
    module = types.ModuleType("vat_comision_forms_preview_test_urls")
    module.urlpatterns = comision_forms_preview_patterns(tmp_path) + list(
        monolith_patterns
    )
    with override_settings(ROOT_URLCONF=module):
        yield


@pytest.mark.usefixtures("preview")
def test_entries_serve_the_frozen_index_behind_the_native_guards(base, curso, oferta):
    del base
    for prefijo, modelo, objeto in (
        ("/vat/comisiones/", "comision", oferta["comision"]),
        ("/vat/cursos/comisiones/", "comisioncurso", curso["comision"]),
    ):
        rutas = {
            "nueva/": "add",
            f"{objeto.pk}/editar/": "change",
            f"{objeto.pk}/eliminar/": "delete",
        }
        for sufijo, accion in rutas.items():
            url = prefijo + sufijo
            respuesta = _client(f"{accion}_{modelo}", sse=True).get(url)
            assert respuesta.status_code == 200, url
            cuerpo = respuesta.content.decode()
            assert '/vat/react/assets/app-1.js"' in cuerpo
            assert "/v2/sisoc/assets/" not in cuerpo
            assert "no-store" in respuesta["Cache-Control"]
            assert "csrftoken" in respuesta.cookies
            assert _client(f"view_{modelo}", sse=True).get(url).status_code == 403
            assert Client().get(url).status_code == 403
            if sufijo != "nueva/":
                assert _client(f"{accion}_{modelo}").get(url).status_code == 404
    guarda = _client("add_comisioncurso", sse=True)
    assert guarda.get("/vat/cursos/comisiones/nueva/?curso=999999").status_code == 403
