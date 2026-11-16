"""V03.02 (U3): inscripciones, acciones de estado y buscador por ciudadano por la API web (vistas nativas). Datos sintéticos."""

import itertools
import types
from datetime import date, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.test import Client, override_settings
from rest_framework.test import APIClient

from ciudadanos.models import Ciudadano
from config.urls_all import urlpatterns as monolith_patterns
from core.models import Localidad, Municipio, Programa, Provincia
from VAT.models import (
    Centro,
    Comision,
    ComisionCurso,
    Curso,
    Inscripcion,
    InstitucionUbicacion,
    ModalidadCursada,
    OfertaInstitucional,
    PlanVersionCurricular,
    Sector,
)
from VAT.web_preview_vat_inscripcion_persona import (
    inscripcion_persona_preview_patterns,
)

pytestmark = pytest.mark.django_db

ROOT = "/api/web/vat/inscripciones-persona/"
_COUNTER = itertools.count()
INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)


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
    programa = Programa.objects.create(nombre="Programa Sintetico")
    oferta = OfertaInstitucional.objects.create(
        centro=centro, plan_curricular=plan, programa=programa, ciclo_lectivo=2026
    )
    comision = Comision.objects.create(
        oferta=oferta,
        codigo_comision="COM-001",
        nombre="Comision Uno",
        fecha_inicio=date.today() + timedelta(days=1),
        fecha_fin=date.today() + timedelta(days=60),
        cupo=10,
    )
    curso = Curso.objects.create(
        nombre="Electricidad básica",
        centro=centro,
        plan_estudio=plan,
        modalidad=modalidad,
        inscripcion_libre=True,
    )
    comision_curso = ComisionCurso.objects.create(
        curso=curso,
        ubicacion=ubicacion,
        cupo_total=5,
        fecha_inicio=date.today() + timedelta(days=1),
        fecha_fin=date.today() + timedelta(days=40),
    )
    return {
        "programa": programa,
        "comision": comision,
        "comision_curso": comision_curso,
        "ana": _ciudadano("30111222", "Pérez", "Ana"),
        "luis": _ciudadano("30333444", "Gómez", "Luis"),
    }


@pytest.fixture(name="inscripcion")
def inscripcion_fixture(base):
    return Inscripcion.objects.create(
        ciudadano=base["ana"],
        comision=base["comision"],
        programa=base["programa"],
        estado="pre_inscripta",
        origen_canal="backoffice",
        observaciones="Obs sintetica",
    )


def _datos(base, **extra):
    return {
        "ciudadano": base["luis"].pk,
        "comision": base["comision"].pk,
        "programa": base["programa"].pk,
        "estado": "inscripta",
        "origen_canal": "backoffice",
        "observaciones": "Alta de prueba",
        **extra,
    }


def test_access_follows_each_native_route_rule(base, inscripcion):
    rutas = {
        ROOT: "view_inscripcion",
        f"{ROOT}{inscripcion.pk}/": "view_inscripcion",
        f"{ROOT}nueva/": "add_inscripcion",
        f"{ROOT}{inscripcion.pk}/editar/": "change_inscripcion",
        f"{ROOT}{inscripcion.pk}/eliminar/": "delete_inscripcion",
    }
    for url, codigo in rutas.items():
        assert APIClient().get(url).status_code == 401
        sin_permiso = "view_voucher"
        assert _client(sin_permiso).get(url).status_code == 403
        assert _client(codigo).get(url).status_code == 200
    assert _client("view_inscripcion").get(f"{ROOT}999999/").status_code == 404
    assert _client("change_inscripcion").get(f"{ROOT}999999/editar/").status_code == 404
    assert (
        _client("delete_inscripcion").get(f"{ROOT}999999/eliminar/").status_code == 404
    )
    assert _client("view_inscripcion").get(f"{ROOT}?page=9").status_code == 404
    buscador = "/api/web/vat/buscador-ciudadano/"
    assert APIClient().get(buscador).status_code == 401
    assert _client("add_inscripcion").get(buscador).status_code == 403
    assert _client("view_inscripcion").get(buscador).status_code == 200
    assert _client("view_centro").get(buscador).status_code == 200


def test_list_projects_the_native_rows_buttons_and_search(base, inscripcion):
    Inscripcion.objects.create(
        ciudadano=base["luis"],
        comision_curso=base["comision_curso"],
        programa=base["programa"],
        estado="rechazada",
        origen_canal="api",
    )
    data = _client("view_inscripcion").get(ROOT).json()
    assert data["permisos"] == {"editar": False, "eliminar": False}
    assert data["page"]["count"] == 2
    por_nombre = {r["ciudadano"]: r for r in data["results"]}
    ana = por_nombre[base["ana"].nombre_completo]
    assert (ana["comision"], ana["programa"], ana["canal"]) == (
        "COM-001",
        "Programa Sintetico",
        "Backoffice",
    )
    assert ana["fecha"] == inscripcion.fecha_inscripcion.strftime("%d/%m/%Y")
    assert (ana["estado"], ana["estado_label"]) == ("pre_inscripta", "Pre-inscripta")
    assert ana["detail_url"] == f"/vat/inscripciones/{inscripcion.pk}/"
    assert data["urls"] == {
        "list": "/vat/inscripciones/",
        "create": "/vat/inscripciones/nueva/",
    }
    completo = _client("view_inscripcion", "change_inscripcion", "delete_inscripcion")
    assert completo.get(ROOT).json()["permisos"] == {"editar": True, "eliminar": True}
    filtrado = _client("view_inscripcion").get(ROOT, {"busqueda": "Gómez"}).json()
    assert [r["ciudadano"] for r in filtrado["results"]] == [
        base["luis"].nombre_completo
    ]
    assert filtrado["busqueda"] == "Gómez"
    estado = _client("view_inscripcion").get(ROOT, {"estado": "rechazada"}).json()
    assert estado["page"]["count"] == 1


def test_detail_projects_both_kinds_of_commission(base, inscripcion):
    de_curso = Inscripcion.objects.create(
        ciudadano=base["luis"],
        comision_curso=base["comision_curso"],
        programa=base["programa"],
        estado="inscripta",
        origen_canal="api",
    )
    api = _client("view_inscripcion", "change_inscripcion", "delete_inscripcion")
    oferta = api.get(f"{ROOT}{inscripcion.pk}/").json()
    assert oferta["ciudadano"] == base["ana"].nombre_completo
    assert oferta["comision_codigo"] == "COM-001"
    assert oferta["comision_label"] == "COM-001 — Comision Uno"
    assert oferta["observaciones"] == "Obs sintetica"
    assert oferta["fecha_validacion"] == "—"
    assert oferta["permisos"] == {"editar": True, "eliminar": True}
    assert oferta["urls"]["comision"] == f"/vat/comisiones/{base['comision'].pk}/"
    curso = api.get(f"{ROOT}{de_curso.pk}/").json()
    # The native template hides edit/delete for course enrolments.
    assert curso["permisos"] == {"editar": False, "eliminar": False}
    assert curso["urls"]["comision"].startswith("/vat/cursos/comisiones/")
    lector = _client("view_inscripcion").get(f"{ROOT}{inscripcion.pk}/").json()
    assert lector["permisos"] == {"editar": False, "eliminar": False}


def test_form_projects_the_native_widgets(base, inscripcion):
    data = _client("change_inscripcion").get(f"{ROOT}{inscripcion.pk}/editar/").json()
    assert data["editing"] is True
    por_nombre = {f["name"]: f for f in data["fields"]}
    assert list(por_nombre) == [
        "ciudadano",
        "comision",
        "programa",
        "estado",
        "origen_canal",
        "observaciones",
    ]
    assert por_nombre["ciudadano"]["value"] == str(base["ana"].pk)
    assert por_nombre["estado"]["value"] == "pre_inscripta"
    assert por_nombre["observaciones"]["tag"] == "textarea"
    vacio = (
        _client("add_inscripcion")
        .get(f"{ROOT}nueva/", {"ciudadano": base["luis"].pk})
        .json()
    )
    assert vacio["editing"] is False
    assert {f["name"]: f["value"] for f in vacio["fields"]}["ciudadano"] == str(
        base["luis"].pk
    )


def test_create_persists_through_the_service_and_queues_the_message(base):
    api = _client("add_inscripcion", "view_inscripcion")
    response = api.post(f"{ROOT}nueva/", _datos(base))
    assert response.status_code == 200
    assert response.json() == {"ok": True, "redirect": "/vat/inscripciones/"}
    creada = Inscripcion.objects.get(ciudadano=base["luis"])
    assert (creada.comision, creada.estado, creada.origen_canal) == (
        base["comision"],
        "inscripta",
        "backoffice",
    )
    assert creada.observaciones == "Alta de prueba"
    assert "Inscripción creada exitosamente." in [
        m["message"] for m in api.get(ROOT).json()["messages"]
    ]


def test_course_quick_enrolment_goes_to_the_waiting_list(base):
    api = _client("add_inscripcion", "view_inscripcion", sse=True)
    curso = base["comision_curso"]
    curso.cupo_total = 0
    curso.acepta_lista_espera = True
    curso.cupo_lista_espera = 2
    curso.save()
    response = api.post(
        f"{ROOT}cursos/rapida-comision/",
        {"comision": curso.pk, "ciudadano_id": base["luis"].pk},
    )
    assert response.json()["estado"] == "en_espera"
    assert (
        response.json()["message"]
        == f"{base['luis'].nombre_completo} quedó en lista de espera."
    )
    assert Inscripcion.objects.get(ciudadano=base["luis"]).estado == "en_espera"


def test_service_rejection_returns_the_form_with_the_message_and_writes_nothing(base):
    api = _client("add_inscripcion", "view_inscripcion")
    base["comision"].cupo = 0
    base["comision"].save()
    response = api.post(f"{ROOT}nueva/", _datos(base))
    assert response.status_code == 400
    data = response.json()
    assert (
        "No es posible inscribirse: el cupo está completo y la comisión no tiene lista de espera."
        in [m["message"] for m in data["messages"]]
    )
    assert {f["name"]: f["value"] for f in data["fields"]}["ciudadano"] == str(
        base["luis"].pk
    )
    assert Inscripcion.objects.count() == 0


def test_duplicate_enrolment_is_rejected_by_the_form_without_writing(base, inscripcion):
    # The native template prints only per-field errors: the unique-together error is silent.
    response = _client("add_inscripcion").post(
        f"{ROOT}nueva/", _datos(base, ciudadano=base["ana"].pk)
    )
    assert response.status_code == 400
    assert all(not f["errors"] for f in response.json()["fields"])
    assert Inscripcion.objects.count() == 1


def test_invalid_form_returns_the_errors_and_writes_nothing(base):
    response = _client("add_inscripcion").post(
        f"{ROOT}nueva/", _datos(base, estado="inexistente", origen_canal="")
    )
    assert response.status_code == 400
    errores = {f["name"]: f["errors"] for f in response.json()["fields"]}
    assert errores["estado"] and errores["origen_canal"]
    assert Inscripcion.objects.count() == 0


def test_update_persists_and_queues_the_message(base, inscripcion):
    api = _client("change_inscripcion", "view_inscripcion")
    response = api.post(
        f"{ROOT}{inscripcion.pk}/editar/",
        _datos(base, ciudadano=base["ana"].pk, estado="rechazada", observaciones="X"),
    )
    assert response.json() == {"ok": True, "redirect": "/vat/inscripciones/"}
    inscripcion.refresh_from_db()
    assert (inscripcion.estado, inscripcion.observaciones) == ("rechazada", "X")
    assert "Inscripción actualizada exitosamente." in [
        m["message"] for m in api.get(ROOT).json()["messages"]
    ]


def test_delete_soft_deletes_and_rejections_leave_the_row(base, inscripcion):
    url = f"{ROOT}{inscripcion.pk}/eliminar/"
    assert _client("change_inscripcion").post(url).status_code == 403
    assert APIClient().post(url).status_code == 401
    assert _client("delete_inscripcion", csrf=True).post(url).status_code == 403
    assert (
        _client("delete_inscripcion").post(f"{ROOT}999999/eliminar/").status_code == 404
    )
    assert Inscripcion.objects.filter(pk=inscripcion.pk).exists()
    datos = _client("delete_inscripcion").get(url).json()
    assert datos["ciudadano"] == base["ana"].nombre_completo
    assert datos["comision"] == "COM-001"
    assert datos["urls"] == {"detail": f"/vat/inscripciones/{inscripcion.pk}/"}
    response = _client("delete_inscripcion").post(url)
    assert response.json() == {"ok": True, "redirect": "/vat/inscripciones/"}
    assert not Inscripcion.objects.filter(pk=inscripcion.pk).exists()
    assert Inscripcion.all_objects.filter(pk=inscripcion.pk).exists()


def test_rejected_form_writes_leave_everything_unchanged(base, inscripcion):
    for url, codigo_ok in (
        (f"{ROOT}nueva/", "add_inscripcion"),
        (f"{ROOT}{inscripcion.pk}/editar/", "change_inscripcion"),
    ):
        assert _client(codigo_ok, csrf=True).post(url, _datos(base)).status_code == 403
        assert _client("view_inscripcion").post(url, _datos(base)).status_code == 403
        assert APIClient().post(url, _datos(base)).status_code == 401
    inscripcion.refresh_from_db()
    assert inscripcion.estado == "pre_inscripta"
    assert Inscripcion.objects.count() == 1


def test_change_state_persists_and_keeps_the_native_message(base, inscripcion):
    api = _client("change_inscripcion", "view_inscripcion", sse=True)
    url = f"{ROOT}{inscripcion.pk}/cambiar-estado/"
    response = api.post(url, {"estado": "inscripta"})
    assert response.json() == {
        "ok": True,
        "redirect": f"/vat/comisiones/{base['comision'].pk}/",
    }
    inscripcion.refresh_from_db()
    assert inscripcion.estado == "inscripta"
    esperado = (
        f"Inscripción de {base['ana'].nombre_completo} actualizada a 'Inscripta'."
    )
    assert esperado in [m["message"] for m in _flash(api)]
    # Invalid state: nothing changes, the native error is queued.
    api.post(url, {"estado": "no-existe"})
    inscripcion.refresh_from_db()
    assert inscripcion.estado == "inscripta"
    assert "Estado no válido." in [m["message"] for m in _flash(api)]


def _flash(api):
    """Messages queued for the next native page of this session."""
    return api.get(ROOT).json()["messages"]


def test_change_state_rejections_write_nothing(base, inscripcion):
    url = f"{ROOT}{inscripcion.pk}/cambiar-estado/"
    body = {"estado": "inscripta"}
    assert APIClient().post(url, body).status_code == 401
    assert _client("view_inscripcion", sse=True).post(url, body).status_code == 403
    assert (
        _client("change_inscripcion", sse=True, csrf=True).post(url, body).status_code
        == 403
    )
    # Outside the management scope the native lookup answers 404.
    assert _client("change_inscripcion").post(url, body).status_code == 404
    assert (
        _client("change_inscripcion", sse=True)
        .post(f"{ROOT}999999/cambiar-estado/", body)
        .status_code
        == 404
    )
    inscripcion.refresh_from_db()
    assert inscripcion.estado == "pre_inscripta"


def test_course_change_state_and_batch_persist(base):
    ana = Inscripcion.objects.create(
        ciudadano=base["ana"],
        comision_curso=base["comision_curso"],
        programa=base["programa"],
        estado="pre_inscripta",
        origen_canal="api",
    )
    luis = Inscripcion.objects.create(
        ciudadano=base["luis"],
        comision_curso=base["comision_curso"],
        programa=base["programa"],
        estado="pre_inscripta",
        origen_canal="api",
    )
    api = _client("change_inscripcion", "view_inscripcion", sse=True)
    detalle = f"/vat/cursos/comisiones/{base['comision_curso'].pk}/"
    response = api.post(
        f"{ROOT}cursos/{ana.pk}/cambiar-estado/", {"estado": "inscripta"}
    )
    assert response.json() == {"ok": True, "redirect": detalle}
    ana.refresh_from_db()
    assert ana.estado == "inscripta"
    lote = f"{ROOT}cursos/comisiones/{base['comision_curso'].pk}/cambiar-estado-lote/"
    # An unsupported action and an empty selection change nothing.
    for body, mensaje in (
        ({"estado": "completada", "inscripciones": [luis.pk]}, "Acción no válida."),
        (
            {"estado": "inscripta", "inscripciones": []},
            "No seleccionaste ninguna inscripción.",
        ),
    ):
        assert api.post(lote, body).json()["redirect"] == f"{detalle}#inscriptos"
        assert mensaje in [m["message"] for m in _flash(api)]
        luis.refresh_from_db()
        assert luis.estado == "pre_inscripta"
    api.post(lote, {"estado": "rechazada", "inscripciones": [luis.pk]})
    luis.refresh_from_db()
    assert luis.estado == "rechazada"
    assert "1 inscripción rechazada." in [m["message"] for m in _flash(api)]
    assert (
        _client("change_inscripcion").post(lote, {"estado": "inscripta"}).status_code
        == 404
    )


def test_quick_enrolment_creates_and_rejects_duplicates(base):
    api = _client("add_inscripcion", sse=True)
    cuerpo = {"comision": base["comision"].pk, "ciudadano_id": base["luis"].pk}
    ok = api.post(f"{ROOT}rapida-comision/", cuerpo)
    assert ok.status_code == 200
    assert ok.json()["ok"] is True and ok.json()["estado"] == "inscripta"
    creada = Inscripcion.objects.get(ciudadano=base["luis"])
    assert ok.json()["inscripcion_id"] == creada.pk
    duplicada = api.post(f"{ROOT}rapida-comision/", cuerpo)
    assert duplicada.status_code == 400
    assert duplicada.json() == {
        "ok": False,
        "message": "El ciudadano ya está inscripto en esta comisión.",
    }
    assert Inscripcion.objects.count() == 1
    curso = api.post(
        f"{ROOT}cursos/rapida-comision/",
        {"comision": base["comision_curso"].pk, "ciudadano_id": base["ana"].pk},
    )
    assert curso.status_code == 200
    assert Inscripcion.objects.get(ciudadano=base["ana"]).comision_curso_id == (
        base["comision_curso"].pk
    )


def test_quick_enrolment_creates_a_citizen_and_rejects_bad_data(base):
    api = _client("add_inscripcion", sse=True)
    invalido = api.post(f"{ROOT}rapida-comision/", {"comision": base["comision"].pk})
    assert invalido.status_code == 400
    assert invalido.json()["message"] == "Errores en el formulario de ciudadano."
    assert Inscripcion.objects.count() == 0
    antes = Ciudadano.objects.count()
    nuevo = api.post(
        f"{ROOT}rapida-comision/",
        {
            "comision": base["comision"].pk,
            "apellido": "Nuevo",
            "nombre": "Nora",
            "fecha_nacimiento": "1995-05-05",
            "tipo_documento": "DNI",
            "documento": "40555666",
        },
    )
    assert nuevo.status_code == 200
    assert Ciudadano.objects.count() == antes + 1
    assert Inscripcion.objects.get().ciudadano.documento == 40555666
    assert (
        _client("view_inscripcion", sse=True)
        .post(f"{ROOT}rapida-comision/", {"comision": base["comision"].pk})
        .status_code
        == 403
    )
    assert (
        _client("add_inscripcion")
        .post(f"{ROOT}cursos/rapida-comision/", {"comision": base["comision_curso"].pk})
        .status_code
        == 404
    )


def test_buscador_states_and_projection(base, inscripcion):
    api = _client("view_inscripcion", sse=True)
    url = "/api/web/vat/buscador-ciudadano/"
    inicial = api.get(url).json()
    assert (inicial["estado"], inicial["q"], inicial["inscripciones"]) == (
        "inicial",
        "",
        [],
    )
    assert api.post(url, {"q": "99999999"}).json()["estado"] == "no_encontrado"
    data = api.post(url, {"q": "30111222"}).json()
    assert data["estado"] == "resultado"
    assert data["scope_is_national"] is True
    assert data["ciudadano"]["apellido"] == "Pérez"
    assert data["ciudadano"]["iniciales"] == "AP"
    assert data["ciudadano"]["cuil_cuit"]
    assert data["resumen"]["total"] == "1" and data["resumen"]["pre_inscriptas"] == "1"
    fila = data["inscripciones"][0]
    assert (fila["estado"], fila["origen"], fila["asistencia_pct"]) == (
        "pre_inscripta",
        "Backoffice",
        "",
    )
    assert fila["comision_codigo"] == "COM-001"
    assert fila["comision_url"] is None
    con_permiso = _client("view_inscripcion", "view_comision", sse=True)
    fila = con_permiso.post(url, {"q": "30111222"}).json()["inscripciones"][0]
    assert fila["comision_url"] == f"/vat/comisiones/{base['comision'].pk}/"
    assert data["urls"] == {"buscador": "/vat/buscador-ciudadano/"}


def test_buscador_candidates_and_rejections(base, inscripcion):
    otro = _ciudadano("50000000", "Duplicado", "Dora")
    otro.cuil_cuit = "20-30111222-3"
    otro.save()
    Inscripcion.objects.create(
        ciudadano=otro,
        comision=base["comision"],
        programa=base["programa"],
        estado="inscripta",
        origen_canal="api",
    )
    api = _client("view_inscripcion", sse=True)
    url = "/api/web/vat/buscador-ciudadano/"
    candidatos = api.post(url, {"q": "20-30111222-3"}).json()
    assert candidatos["estado"] == "candidatos"
    assert sorted(c["ciudadano"]["apellido"] for c in candidatos["candidatos"]) == [
        "Duplicado",
        "Pérez",
    ]
    elegido = api.post(url, {"q": "20-30111222-3", "ciudadano_id": otro.pk}).json()
    assert elegido["estado"] == "resultado"
    assert elegido["ciudadano"]["apellido"] == "Duplicado"
    assert APIClient().post(url, {"q": "1"}).status_code == 401
    assert _client("add_inscripcion").post(url, {"q": "1"}).status_code == 403
    assert (
        _client("view_inscripcion", csrf=True).post(url, {"q": "1"}).status_code == 403
    )


@pytest.fixture(name="preview")
def preview_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    (tmp_path / "assets" / "app-1.js").write_text("console.log(1);", encoding="utf-8")
    module = types.ModuleType("vat_inscripcion_persona_preview_test_urls")
    module.urlpatterns = inscripcion_persona_preview_patterns(tmp_path) + list(
        monolith_patterns
    )
    with override_settings(ROOT_URLCONF=module):
        yield


@pytest.mark.usefixtures("preview")
def test_entries_serve_the_frozen_index_behind_the_native_guards(base, inscripcion):
    rutas = {
        "/vat/inscripciones/": "view_inscripcion",
        f"/vat/inscripciones/{inscripcion.pk}/": "view_inscripcion",
        "/vat/inscripciones/nueva/": "add_inscripcion",
        f"/vat/inscripciones/{inscripcion.pk}/editar/": "change_inscripcion",
        f"/vat/inscripciones/{inscripcion.pk}/eliminar/": "delete_inscripcion",
        "/vat/buscador-ciudadano/": "view_inscripcion",
    }
    for url, codigo in rutas.items():
        response = _client(codigo).get(url)
        assert response.status_code == 200
        assert '/vat/react/assets/app-1.js"' in response.content.decode()
        assert "no-store" in response["Cache-Control"]
        assert "csrftoken" in response.cookies
        assert _client("view_voucher").get(url).status_code == 403
        assert Client().get(url).status_code == 403
    assert (
        _client("view_inscripcion").get("/vat/inscripciones/999999/").status_code == 404
    )
    assert (
        _client("view_inscripcion").get("/vat/inscripciones/?page=9").status_code == 404
    )
