"""V04.02 (U5): web API y entradas de vista previa de los horarios de comisión (``/api/web/vat/comisiones-horarios/``). Datos sintéticos."""

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
from VAT.web_preview_vat_comision_horario_forms import (
    comision_horario_preview_patterns,
)

pytestmark = pytest.mark.django_db

_COUNTER = itertools.count()
INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)
OFERTA = "/api/web/vat/comisiones-horarios/"
CURSO = "/api/web/vat/comisiones-horarios/cursos/"
# sufijo de la ruta, permiso que exige
RUTAS = {"nuevo/": "add", "{pk}/editar/": "change", "{pk}/eliminar/": "delete"}


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
        fecha_inicio=date(2026, 3, 1),
        fecha_fin=date(2026, 6, 30),
    )
    horario = ComisionHorario.objects.create(
        comision_curso=comision,
        dia_semana=base["dia"],
        hora_desde=time(9, 0),
        hora_hasta=time(12, 30),
        aula_espacio="Aula 2",
        vigente=True,
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
    return {
        "comision": comision,
        "horario": horario,
        "realizada": realizada,
        "pendiente": pendiente,
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
    return {"comision": comision, "horario": horario}


def _variantes(curso, oferta):
    return (
        ("oferta", OFERTA, oferta["comision"], oferta["horario"]),
        ("curso", CURSO, curso["comision"], curso["horario"]),
    )


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


def test_access_follows_each_native_route_rule_and_scope(base, curso, oferta):
    del base
    for _nombre, raiz, _comision, horario in _variantes(curso, oferta):
        for sufijo, accion in RUTAS.items():
            url = raiz + sufijo.format(pk=horario.pk)
            assert APIClient().get(url).status_code == 401, url
            for otra in {"add", "change", "delete"} - {accion}:
                cliente = _client(f"{otra}_comisionhorario", sse=True)
                assert cliente.get(url).status_code == 403, url
            assert (
                _client(f"{accion}_comisionhorario", sse=True).get(url).status_code
                == 200
            )
            if "{pk}" in sufijo:
                # Fuera de alcance (sin rol de alcance global) la vista nativa da 404.
                assert _client(f"{accion}_comisionhorario").get(url).status_code == 404
                faltante = raiz + sufijo.format(pk=999999)
                assert (
                    _client(f"{accion}_comisionhorario", sse=True)
                    .get(faltante)
                    .status_code
                    == 404
                )


def test_forms_project_the_native_fields_and_the_initial_commission(
    base, curso, oferta
):
    del base
    cliente = _client("add_comisionhorario", "change_comisionhorario", sse=True)
    nueva = cliente.get(OFERTA + "nuevo/", {"comision": oferta["comision"].pk}).json()
    assert nueva["editing"] is False and nueva["campo"] == "comision"
    assert [f["name"] for f in nueva["fields"]] == [
        "comision",
        "dia_semana",
        "hora_desde",
        "hora_hasta",
        "aula_espacio",
        "vigente",
    ]
    assert nueva["fields"][0]["value"] == str(oferta["comision"].pk)
    assert "select2" in nueva["fields"][0]["attrs"]["class"]
    assert nueva["urls"] == {"list": "/vat/comisiones/horarios/"}
    editar = cliente.get(CURSO + f"{curso['horario'].pk}/editar/").json()
    assert editar["editing"] is True and editar["campo"] == "comision_curso"
    por_nombre = {f["name"]: f for f in editar["fields"]}
    assert editar["fields"][0]["name"] == "comision_curso"
    assert por_nombre["comision_curso"]["value"] == str(curso["comision"].pk)
    assert (por_nombre["hora_desde"]["value"], por_nombre["aula_espacio"]["value"]) == (
        "09:00:00",
        "Aula 2",
    )
    assert por_nombre["vigente"]["value"] is True


def test_create_persists_generates_the_classes_and_queues_the_native_message(
    base, curso, oferta
):
    for nombre, raiz, comision, _horario in _variantes(curso, oferta):
        campo = "comision_curso" if nombre == "curso" else "comision"
        cliente = _client(
            "add_comisionhorario", "view_comision", "view_comisioncurso", sse=True
        )
        antes = ComisionHorario.objects.count()
        respuesta = cliente.post(
            raiz + "nuevo/",
            {
                campo: comision.pk,
                "dia_semana": base["dia"].pk,
                "hora_desde": "10:00",
                "hora_hasta": "12:00",
                "aula_espacio": "Aula 9",
                "vigente": "on",
            },
        )
        assert respuesta.status_code == 200, respuesta.content
        creado = ComisionHorario.objects.order_by("-pk").first()
        assert ComisionHorario.objects.count() == antes + 1
        assert (creado.aula_espacio, creado.hora_desde, creado.vigente) == (
            "Aula 9",
            time(10, 0),
            True,
        )
        destino = (
            f"/vat/cursos/comisiones/{comision.pk}/"
            if nombre == "curso"
            else f"/vat/comisiones/{comision.pk}/"
        )
        assert respuesta.json() == {"ok": True, "redirect": destino}
        sesiones = SesionComision.objects.filter(horario=creado).count()
        assert sesiones > 0
        assert (
            f"Horario creado. Se generaron {sesiones} sesiones.",
            "success",
        ) in _mensajes(cliente, curso, oferta)


def test_invalid_post_is_400_with_errors_and_writes_nothing(base, curso, oferta):
    cliente = _client("add_comisionhorario", "change_comisionhorario", sse=True)
    antes = (ComisionHorario.objects.count(), SesionComision.objects.count())
    rechazo = cliente.post(
        OFERTA + "nuevo/",
        {"comision": oferta["comision"].pk, "dia_semana": base["dia"].pk},
    )
    assert rechazo.status_code == 400
    errores = {f["name"]: f["errors"] for f in rechazo.json()["fields"]}
    assert errores["hora_desde"] and errores["hora_hasta"] and not errores["comision"]
    assert (ComisionHorario.objects.count(), SesionComision.objects.count()) == antes
    # Defecto nativo conservado: la plantilla del curso no dibuja ``comision_curso``.
    sin_comision = cliente.post(
        CURSO + f"{curso['horario'].pk}/editar/",
        {"dia_semana": base["dia"].pk, "hora_desde": "08:00", "hora_hasta": "09:00"},
    )
    assert sin_comision.status_code == 400
    curso["horario"].refresh_from_db()
    assert curso["horario"].hora_desde == time(9, 0)


def test_update_regenerates_the_classes_and_delete_removes_them(base, curso, oferta):
    cliente = _client(
        "change_comisionhorario",
        "delete_comisionhorario",
        "view_comision",
        "view_comisioncurso",
        sse=True,
    )
    horario = curso["horario"]
    respuesta = cliente.post(
        CURSO + f"{horario.pk}/editar/",
        {
            "comision_curso": curso["comision"].pk,
            "dia_semana": base["dia"].pk,
            "hora_desde": "14:00",
            "hora_hasta": "16:00",
            "aula_espacio": "",
        },
    )
    assert respuesta.status_code == 200
    horario.refresh_from_db()
    assert (horario.hora_desde, horario.aula_espacio, horario.vigente) == (
        time(14, 0),
        "",
        False,
    )
    # Las sesiones realizadas se conservan; las programadas se regeneran.
    assert SesionComision.objects.filter(pk=curso["realizada"].pk).exists()
    assert not SesionComision.objects.filter(pk=curso["pendiente"].pk).exists()
    nuevas = SesionComision.objects.filter(horario=horario, estado="programada").count()
    assert (
        f"Horario actualizado. {nuevas} sesiones regeneradas.",
        "success",
    ) in _mensajes(cliente, curso, oferta)
    baja = cliente.post(CURSO + f"{horario.pk}/eliminar/")
    assert baja.json() == {
        "ok": True,
        "redirect": f"/vat/cursos/comisiones/{curso['comision'].pk}/",
    }
    assert not ComisionHorario.objects.filter(pk=horario.pk).exists()
    assert ("Horario eliminado exitosamente.", "success") in _mensajes(
        cliente, curso, oferta
    )
    oferta_baja = cliente.post(OFERTA + f"{oferta['horario'].pk}/eliminar/")
    assert oferta_baja.status_code == 200
    assert not ComisionHorario.objects.filter(pk=oferta["horario"].pk).exists()
    assert cliente.post(OFERTA + "999999/eliminar/").status_code == 404


def test_delete_page_texts_are_the_ones_the_native_page_prints(base, curso, oferta):
    del base
    api = _client("delete_comisionhorario", sse=True)
    nativo = Client()
    nativo.force_login(api.user)
    for _nombre, raiz, _comision, horario in _variantes(curso, oferta):
        datos = api.get(raiz + f"{horario.pk}/eliminar/").json()
        nativa = (
            f"/vat/cursos/comisiones/horarios/{horario.pk}/eliminar/"
            if raiz == CURSO
            else f"/vat/comisiones/horarios/{horario.pk}/eliminar/"
        )
        html = nativo.get(nativa).content.decode()
        assert escape(datos["titulo"]) in html and escape(datos["subtitulo"]) in html
        assert datos["urls"]["detail"] == f"/vat/comisiones/horarios/{horario.pk}/"
    assert api.get(OFERTA + f"{oferta['horario'].pk}/eliminar/").json()["titulo"] == (
        "Lunes 18:00-20:00"
    )
    # Defecto nativo conservado: el horario de un curso no tiene ``comision``.
    borrado = api.get(CURSO + f"{curso['horario'].pk}/eliminar/").json()
    assert borrado["subtitulo"] == "None"


def test_writes_without_csrf_or_login_change_nothing(base, curso, oferta):
    del base
    cliente = _client("delete_comisionhorario", sse=True, csrf=True)
    url = OFERTA + f"{oferta['horario'].pk}/eliminar/"
    assert cliente.post(url).status_code == 403
    assert APIClient().post(url).status_code in (401, 403)
    assert ComisionHorario.objects.filter(pk=oferta["horario"].pk).exists()
    assert ComisionHorario.objects.filter(pk=curso["horario"].pk).exists()


@pytest.fixture(name="preview")
def preview_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    (tmp_path / "assets" / "app-1.js").write_text("console.log(1);", encoding="utf-8")
    module = types.ModuleType("vat_comision_horario_preview_test_urls")
    module.urlpatterns = comision_horario_preview_patterns(tmp_path) + list(
        monolith_patterns
    )
    with override_settings(ROOT_URLCONF=module):
        yield


@pytest.mark.usefixtures("preview")
def test_entries_serve_the_frozen_index_behind_the_native_guards(base, curso, oferta):
    del base
    for _nombre, raiz, _comision, horario in _variantes(curso, oferta):
        prefijo = (
            "/vat/cursos/comisiones/horarios/"
            if raiz == CURSO
            else "/vat/comisiones/horarios/"
        )
        for sufijo, accion in RUTAS.items():
            url = prefijo + sufijo.format(pk=horario.pk)
            respuesta = _client(f"{accion}_comisionhorario", sse=True).get(url)
            assert respuesta.status_code == 200, url
            cuerpo = respuesta.content.decode()
            assert '/vat/react/assets/app-1.js"' in cuerpo
            assert "/v2/sisoc/assets/" not in cuerpo
            assert "no-store" in respuesta["Cache-Control"]
            assert "csrftoken" in respuesta.cookies
            assert _client("view_comisionhorario", sse=True).get(url).status_code == 403
            assert Client().get(url).status_code == 403
            if "{pk}" in sufijo:
                assert _client(f"{accion}_comisionhorario").get(url).status_code == 404
