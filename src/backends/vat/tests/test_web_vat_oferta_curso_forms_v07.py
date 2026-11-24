"""V05.02 (U7): web API and preview entries of the offer and course forms (``/api/web/vat/ofertas-institucionales/``, ``.../cursos-formularios/``). Synthetic data."""

import itertools
import types
from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.test import Client, override_settings
from django.utils.html import escape
from rest_framework.test import APIClient

from config.urls_all import urlpatterns as monolith_patterns
from core.models import Programa, Provincia
from VAT.models import (
    Centro,
    Curso,
    ModalidadCursada,
    OfertaInstitucional,
    PlanVersionCurricular,
    Sector,
    TituloReferencia,
    VoucherParametria,
)
from VAT.web_preview_vat_oferta_curso_forms import oferta_curso_forms_preview_patterns

pytestmark = pytest.mark.django_db

_COUNTER = itertools.count()
OFERTA = "/api/web/vat/ofertas-institucionales/"
CURSO = "/api/web/vat/cursos-formularios/"
INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)
CAMPOS_OFERTA = [
    "plan_curricular",
    "centro",
    "titulo_referencia",
    "programa",
    "ciclo_lectivo",
    "nombre_local",
    "estado",
    "usa_voucher",
    "costo",
    "fecha_publicacion",
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
    modalidad = ModalidadCursada.objects.create(nombre="Presencial")
    plan = PlanVersionCurricular.objects.create(
        nombre="Electricidad",
        provincia=provincia,
        sector=Sector.objects.create(nombre="Industria"),
        modalidad_cursada=modalidad,
        horas_reloj=100,
    )
    programa = Programa.objects.create(nombre="Programa Uno")
    otro_programa = Programa.objects.create(nombre="Programa Dos")
    creador = get_user_model().objects.create_user("creador")

    def voucher(nombre, prog):
        return VoucherParametria.objects.create(
            nombre=nombre,
            programa=prog,
            activa=True,
            cantidad_inicial=10,
            fecha_vencimiento=date(2030, 1, 1),
            creado_por=creador,
        )

    return {
        "centro": Centro.objects.create(
            nombre="CFP 401", codigo="060144900", provincia=provincia
        ),
        "otro": Centro.objects.create(
            nombre="CFP 402", codigo="060144901", provincia=provincia
        ),
        "modalidad": modalidad,
        "plan": plan,
        "titulo": TituloReferencia.objects.create(
            nombre="Electricista", plan_estudio=plan
        ),
        "programa": programa,
        "otro_programa": otro_programa,
        "v1": voucher("Voucher Uno", programa),
        "v2": voucher("Voucher Dos", programa),
        "v3": voucher("Voucher Tres", otro_programa),
    }


@pytest.fixture(name="oferta")
def oferta_fixture(base):
    oferta = OfertaInstitucional.objects.create(
        centro=base["centro"],
        plan_curricular=base["plan"],
        programa=base["programa"],
        ciclo_lectivo=2026,
        nombre_local="Local Uno",
    )
    oferta.voucher_parametrias.add(base["v1"])
    return oferta


@pytest.fixture(name="curso")
def curso_fixture(base):
    curso = Curso.objects.create(
        nombre="Electricidad básica",
        centro=base["centro"],
        plan_estudio=base["plan"],
        modalidad=base["modalidad"],
        usa_voucher=True,
        costo_creditos=7,
    )
    curso.voucher_parametrias.add(base["v1"])
    return curso


def _post_oferta(base, **cambios):
    datos = {
        "plan_curricular": "",
        "centro": base["centro"].pk,
        "titulo_referencia": base["titulo"].pk,
        "programa": base["programa"].pk,
        "ciclo_lectivo": 2027,
        "nombre_local": "Nueva oferta",
        "estado": "planificada",
        "costo": "0",
        "fecha_publicacion": "",
        "observaciones": "Notas",
    }
    datos.update(cambios)
    return datos


def _post_curso(base, **cambios):
    datos = {
        "plan_estudio": base["plan"].pk,
        "nombre": "Curso nuevo",
        "estado": "planificado",
        "observaciones": "Notas",
    }
    datos.update(cambios)
    return datos


def test_access_follows_each_native_route_rule(base, oferta, curso):
    del base
    for modelo, raiz, objeto, alta in (
        ("ofertainstitucional", OFERTA, oferta, "nueva/"),
        ("curso", CURSO, curso, "nuevo/"),
    ):
        rutas = {
            f"{alta}?centro={curso.centro_id}": "add",
            f"{objeto.pk}/editar/": "change",
            f"{objeto.pk}/eliminar/": "delete",
        }
        for sufijo, accion in rutas.items():
            url = raiz + sufijo
            assert APIClient().get(url).status_code == 401
            for otra in {"view", "add", "change", "delete"} - {accion}:
                assert _client(f"{otra}_{modelo}", sse=True).get(url).status_code == 403
            assert _client(f"{accion}_{modelo}", sse=True).get(url).status_code == 200
            if accion != "add":
                # Outside the scope (no global role) the native queryset gives 404.
                assert _client(f"{accion}_{modelo}").get(url).status_code == 404
        faltante = raiz + "999999/editar/"
        assert _client(f"change_{modelo}", sse=True).get(faltante).status_code == 404


def test_offer_form_projects_the_native_fields_and_the_voucher_options(base, oferta):
    api = _client("add_ofertainstitucional", "change_ofertainstitucional", sse=True)
    datos = api.get(OFERTA + "nueva/", {"centro": base["centro"].pk}).json()
    assert datos["editing"] is False
    assert [f["name"] for f in datos["fields"]] == CAMPOS_OFERTA
    centro = next(f for f in datos["fields"] if f["name"] == "centro")
    assert centro["value"] == str(base["centro"].pk) and centro["required"] is True
    assert "select2" in centro["attrs"]["class"]
    oculto = datos["fields"][0]
    assert oculto["attrs"]["type"] == "hidden" and oculto["required"] is False
    vouchers = datos["vouchers"]
    assert vouchers["values"] == [] and vouchers["name"] == "voucher_parametrias"
    assert vouchers["attrs"]["size"] == "7" and "select2" in vouchers["attrs"]["class"]
    assert {(c["label"], c["programa_id"]) for c in vouchers["choices"]} == {
        ("Voucher Uno (Programa Uno)", str(base["programa"].pk)),
        ("Voucher Dos (Programa Uno)", str(base["programa"].pk)),
        ("Voucher Tres (Programa Dos)", str(base["otro_programa"].pk)),
    }
    assert datos["urls"] == {"list": "/vat/ofertas-institucionales/"}
    assert datos["non_field_errors"] == [] and datos["messages"] == []
    edicion = api.get(f"{OFERTA}{oferta.pk}/editar/").json()
    assert edicion["editing"] is True
    assert edicion["vouchers"]["values"] == [str(base["v1"].pk)]
    ciclo = next(f for f in edicion["fields"] if f["name"] == "ciclo_lectivo")
    assert ciclo["value"] == "2026"


def test_offer_create_persists_with_vouchers_and_queues_the_native_message(base):
    client = _client("add_ofertainstitucional", "view_ofertainstitucional", sse=True)
    cuerpo = _post_oferta(
        base,
        usa_voucher="on",
        voucher_parametrias=[base["v1"].pk, base["v2"].pk],
        costo="150.50",
        fecha_publicacion="2026-03-01",
    )
    respuesta = client.post(OFERTA + "nueva/", cuerpo)
    assert respuesta.status_code == 200
    assert respuesta.json() == {"ok": True, "redirect": "/vat/ofertas-institucionales/"}
    creada = OfertaInstitucional.objects.get(nombre_local="Nueva oferta")
    assert (creada.centro_id, creada.plan_curricular_id, creada.usa_voucher) == (
        base["centro"].pk,
        base["plan"].pk,
        True,
    )
    assert str(creada.costo) == "150.50" and creada.fecha_publicacion == date(
        2026, 3, 1
    )
    assert {v.pk for v in creada.voucher_parametrias.all()} == {
        base["v1"].pk,
        base["v2"].pk,
    }
    mensajes = client.get(OFERTA).json()["messages"]
    assert [(m["message"], m["level"]) for m in mensajes] == [
        ("Oferta institucional creada exitosamente.", "success")
    ]
    assert client.get(OFERTA).json()["messages"] == []


def test_invalid_offer_posts_are_400_with_errors_and_write_nothing(base, oferta):
    client = _client("add_ofertainstitucional", "change_ofertainstitucional", sse=True)
    sin_voucher = client.post(OFERTA + "nueva/", _post_oferta(base, usa_voucher="on"))
    assert sin_voucher.status_code == 400
    campos = {f["name"]: f for f in sin_voucher.json()["fields"]}
    assert sin_voucher.json()["vouchers"]["errors"] == [
        "Debés seleccionar al menos un voucher cuando la oferta usa voucher."
    ]
    assert campos["nombre_local"]["value"] == "Nueva oferta"
    ajeno = client.post(
        OFERTA + "nueva/",
        _post_oferta(
            base, usa_voucher="on", voucher_parametrias=[base["v1"].pk, base["v3"].pk]
        ),
    )
    assert ajeno.status_code == 400
    assert ajeno.json()["vouchers"]["errors"] == [
        "Todos los vouchers seleccionados deben pertenecer al programa elegido."
    ]
    assert ajeno.json()["vouchers"]["values"] == [
        str(base["v1"].pk),
        str(base["v3"].pk),
    ]
    vacio = client.post(OFERTA + "nueva/", _post_oferta(base, ciclo_lectivo=""))
    assert vacio.status_code == 400
    assert next(f for f in vacio.json()["fields"] if f["name"] == "ciclo_lectivo")[
        "errors"
    ]
    edicion = client.post(
        f"{OFERTA}{oferta.pk}/editar/",
        _post_oferta(base, nombre_local="Otro", estado="x"),
    )
    assert edicion.status_code == 400
    oferta.refresh_from_db()
    assert oferta.nombre_local == "Local Uno"
    assert OfertaInstitucional.objects.count() == 1


def test_offer_update_and_delete_follow_the_native_views(base, oferta):
    editor = _client("change_ofertainstitucional", sse=True)
    ok = editor.post(
        f"{OFERTA}{oferta.pk}/editar/",
        _post_oferta(
            base, nombre_local="Editada", estado="publicada", ciclo_lectivo=2030
        ),
    )
    assert ok.json() == {"ok": True, "redirect": "/vat/ofertas-institucionales/"}
    oferta.refresh_from_db()
    assert (oferta.nombre_local, oferta.estado, oferta.ciclo_lectivo) == (
        "Editada",
        "publicada",
        2030,
    )
    assert oferta.voucher_parametrias.count() == 0
    assert editor.get(OFERTA).status_code == 403
    ajeno = _client("change_ofertainstitucional")
    assert (
        ajeno.post(f"{OFERTA}{oferta.pk}/editar/", _post_oferta(base)).status_code
        == 404
    )
    borrador = _client("delete_ofertainstitucional", sse=True)
    assert borrador.post(f"{OFERTA}999999/eliminar/").status_code == 404
    assert (
        _client("delete_ofertainstitucional")
        .post(f"{OFERTA}{oferta.pk}/eliminar/")
        .status_code
        == 404
    )
    assert OfertaInstitucional.objects.filter(pk=oferta.pk).exists()
    assert borrador.post(f"{OFERTA}{oferta.pk}/eliminar/").json() == {
        "ok": True,
        "redirect": "/vat/ofertas-institucionales/",
    }
    assert not OfertaInstitucional.objects.filter(pk=oferta.pk).exists()
    assert OfertaInstitucional.all_objects.filter(pk=oferta.pk).exists()


def test_offer_delete_text_is_the_one_the_native_page_prints(oferta):
    api = _client("delete_ofertainstitucional", sse=True)
    nativo = Client()
    nativo.force_login(api.user)
    datos = api.get(f"{OFERTA}{oferta.pk}/eliminar/").json()
    html = nativo.get(
        f"/vat/ofertas-institucionales/{oferta.pk}/eliminar/"
    ).content.decode()
    assert datos["subtitulo"] == "Ciclo 2026 • CFP 401"
    assert escape(datos["titulo"]) in html and "Ciclo 2026 • CFP 401" in html
    assert datos["urls"]["detail"] == f"/vat/ofertas-institucionales/{oferta.pk}/"


def test_locked_fields_of_the_provincial_actor_are_projected_disabled(
    base, oferta, monkeypatch
):
    del base
    monkeypatch.setattr("VAT.forms._is_inet_provincia_actor", lambda actor: True)
    api = _client("change_ofertainstitucional", sse=True)
    campos = {
        f["name"]: f for f in api.get(f"{OFERTA}{oferta.pk}/editar/").json()["fields"]
    }
    for nombre in ("centro", "titulo_referencia", "programa", "ciclo_lectivo"):
        assert campos[nombre]["attrs"]["disabled"] == "disabled", nombre
    assert "disabled" not in campos["nombre_local"]["attrs"]


def test_course_form_projects_only_the_fields_the_native_template_draws(base, curso):
    api = _client("add_curso", "change_curso", sse=True)
    nuevo = api.get(CURSO + "nuevo/", {"centro": base["centro"].pk}).json()
    assert [f["name"] for f in nuevo["fields"]] == [
        "plan_estudio",
        "nombre",
        "estado",
        "inscripcion_libre",
        "observaciones",
    ]
    assert nuevo["editing"] is False
    assert nuevo["urls"] == {"cancel": f"/vat/centros/{base['centro'].pk}/#cursos"}
    plan = nuevo["fields"][0]
    assert "select2" in plan["attrs"]["class"] and plan["required"] is True
    assert plan["help_text"].startswith("Se listan todos los planes")
    edicion = api.get(f"{CURSO}{curso.pk}/editar/").json()
    assert edicion["editing"] is True
    assert edicion["fields"][1]["value"] == "Electricidad básica"


def test_course_create_keeps_the_native_centro_guard_and_persists(base):
    lector = _client("add_curso")
    assert lector.get(CURSO + "nuevo/").status_code == 403
    assert (
        lector.get(CURSO + "nuevo/", {"centro": base["centro"].pk}).status_code == 403
    )
    assert lector.post(CURSO + "nuevo/", _post_curso(base)).status_code == 403
    sse = _client("add_curso", "view_ofertainstitucional", sse=True)
    assert sse.get(CURSO + "nuevo/", {"centro": 999999}).status_code == 403
    assert sse.post(CURSO + "nuevo/", _post_curso(base)).status_code == 403
    assert Curso.objects.count() == 0
    respuesta = sse.post(
        CURSO + f"nuevo/?centro={base['centro'].pk}",
        _post_curso(base, inscripcion_libre="on", usa_voucher="on", costo_creditos="9"),
    )
    assert respuesta.json() == {
        "ok": True,
        "redirect": f"/vat/centros/{base['centro'].pk}/?refresh=1#cursos",
    }
    creado = Curso.objects.get()
    assert (creado.nombre, creado.centro_id, creado.inscripcion_libre) == (
        "Curso nuevo",
        base["centro"].pk,
        True,
    )
    # The voucher fields are hidden and locked in the native form: a posted value is ignored.
    assert (creado.usa_voucher, creado.costo_creditos) == (False, 0)
    assert [(m["message"], m["level"]) for m in sse.get(OFERTA).json()["messages"]] == [
        ("Curso creado exitosamente.", "success")
    ]


def test_invalid_course_posts_are_400_with_errors_and_write_nothing(base, curso):
    sse = _client("add_curso", "change_curso", sse=True)
    nuevo = sse.post(
        CURSO + f"nuevo/?centro={base['centro'].pk}", _post_curso(base, nombre="")
    )
    assert nuevo.status_code == 400
    assert next(f for f in nuevo.json()["fields"] if f["name"] == "nombre")["errors"]
    assert Curso.objects.count() == 1
    edicion = sse.post(
        f"{CURSO}{curso.pk}/editar/", _post_curso(base, nombre="", estado="activo")
    )
    assert edicion.status_code == 400
    curso.refresh_from_db()
    assert curso.nombre == "Electricidad básica"
    # Native model rule: a course with vouchers cannot also be free enrolment.
    libre = sse.post(
        f"{CURSO}{curso.pk}/editar/",
        _post_curso(base, nombre="Otro", inscripcion_libre="on"),
    )
    assert libre.status_code == 400
    assert next(f for f in libre.json()["fields"] if f["name"] == "inscripcion_libre")[
        "errors"
    ] == ["Un curso no puede usar voucher e inscripción libre al mismo tiempo."]
    curso.refresh_from_db()
    assert (curso.nombre, curso.inscripcion_libre) == ("Electricidad básica", False)


def test_course_update_and_delete_follow_the_native_views(base, curso):
    editor = _client("change_curso", sse=True)
    ok = editor.post(
        f"{CURSO}{curso.pk}/editar/",
        _post_curso(base, nombre="Editado", estado="activo"),
    )
    assert ok.json() == {
        "ok": True,
        "redirect": f"/vat/centros/{base['centro'].pk}/?refresh=1#cursos",
    }
    curso.refresh_from_db()
    assert (curso.nombre, curso.estado, curso.inscripcion_libre) == (
        "Editado",
        "activo",
        False,
    )
    assert (curso.usa_voucher, curso.costo_creditos) == (True, 7)
    assert [v.pk for v in curso.voucher_parametrias.all()] == [base["v1"].pk]
    assert (
        _client("change_curso")
        .post(f"{CURSO}{curso.pk}/editar/", _post_curso(base))
        .status_code
        == 404
    )
    api = _client("delete_curso", sse=True)
    nativo = Client()
    nativo.force_login(api.user)
    datos = api.get(f"{CURSO}{curso.pk}/eliminar/").json()
    assert datos["titulo"] == "Editado"
    assert datos["urls"]["detail"] == f"/vat/centros/{base['centro'].pk}/#cursos"
    assert (
        escape(datos["titulo"])
        in nativo.get(f"/vat/cursos/{curso.pk}/eliminar/").content.decode()
    )
    assert (
        _client("delete_curso").post(f"{CURSO}{curso.pk}/eliminar/").status_code == 404
    )
    assert api.post(f"{CURSO}999999/eliminar/").status_code == 404
    baja = api.post(f"{CURSO}{curso.pk}/eliminar/")
    assert baja.json() == {
        "ok": True,
        "redirect": f"/vat/centros/{base['centro'].pk}/?refresh=1#cursos",
    }
    assert not Curso.objects.filter(pk=curso.pk).exists()
    assert Curso.all_objects.filter(pk=curso.pk).exists()


def test_the_modal_variants_never_break_the_api_redirect(base, curso):
    editor = _client("change_curso", sse=True)
    # ``?modal=1`` on the API path (never sent by React) still answers the JSON redirect, not a 500.
    ok = editor.post(
        f"{CURSO}{curso.pk}/editar/?modal=1", _post_curso(base, nombre="Modal")
    )
    assert ok.status_code == 200 and ok.json()["ok"] is True
    assert (
        ok.json()["redirect"] == f"/vat/centros/{base['centro'].pk}/?refresh=1#cursos"
    )
    curso.refresh_from_db()
    assert curso.nombre == "Modal"


def test_rejected_writes_change_nothing(base, oferta, curso):
    assert (
        _client("add_ofertainstitucional", sse=True, csrf=True)
        .post(OFERTA + "nueva/", _post_oferta(base))
        .status_code
        == 403
    )
    assert (
        _client("view_ofertainstitucional", sse=True)
        .post(f"{OFERTA}{oferta.pk}/editar/", _post_oferta(base))
        .status_code
        == 403
    )
    assert (
        _client("delete_ofertainstitucional", sse=True, csrf=True)
        .post(f"{OFERTA}{oferta.pk}/eliminar/")
        .status_code
        == 403
    )
    assert APIClient().post(OFERTA + "nueva/", _post_oferta(base)).status_code == 401
    assert (
        _client("add_curso", sse=True, csrf=True)
        .post(CURSO + f"nuevo/?centro={base['centro'].pk}", _post_curso(base))
        .status_code
        == 403
    )
    assert (
        _client("view_curso", sse=True)
        .post(f"{CURSO}{curso.pk}/editar/", _post_curso(base))
        .status_code
        == 403
    )
    assert (
        _client("delete_curso", sse=True, csrf=True)
        .post(f"{CURSO}{curso.pk}/eliminar/")
        .status_code
        == 403
    )
    assert APIClient().post(f"{CURSO}{curso.pk}/eliminar/").status_code == 401
    assert OfertaInstitucional.objects.count() == 1 and Curso.objects.count() == 1
    curso.refresh_from_db()
    assert curso.nombre == "Electricidad básica"


@pytest.fixture(name="preview")
def preview_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    (tmp_path / "assets" / "app-1.js").write_text("console.log(1);", encoding="utf-8")
    module = types.ModuleType("vat_oferta_curso_forms_preview_test_urls")
    module.urlpatterns = oferta_curso_forms_preview_patterns(tmp_path) + list(
        monolith_patterns
    )
    with override_settings(ROOT_URLCONF=module):
        yield


@pytest.mark.usefixtures("preview")
def test_entries_serve_the_frozen_index_behind_the_native_guards(base, oferta, curso):
    centro = base["centro"].pk
    for url, modelo, accion in (
        ("/vat/ofertas-institucionales/nueva/", "ofertainstitucional", "add"),
        (
            f"/vat/ofertas-institucionales/{oferta.pk}/editar/",
            "ofertainstitucional",
            "change",
        ),
        (
            f"/vat/ofertas-institucionales/{oferta.pk}/eliminar/",
            "ofertainstitucional",
            "delete",
        ),
        (f"/vat/cursos/nuevo/?centro={centro}", "curso", "add"),
        (f"/vat/cursos/{curso.pk}/editar/", "curso", "change"),
        (f"/vat/cursos/{curso.pk}/eliminar/", "curso", "delete"),
    ):
        respuesta = _client(f"{accion}_{modelo}", sse=True).get(url)
        assert respuesta.status_code == 200, url
        cuerpo = respuesta.content.decode()
        assert (
            '/vat/react/assets/app-1.js"' in cuerpo
            and "/v2/sisoc/assets/" not in cuerpo
        )
        assert "no-store" in respuesta["Cache-Control"]
        assert "csrftoken" in respuesta.cookies
        assert Client().get(url).status_code == 403
        assert _client(f"view_{modelo}", sse=True).get(url).status_code == 403
        if accion != "add":
            assert _client(f"{accion}_{modelo}").get(url).status_code == 404
    guarda = _client("add_curso", sse=True)
    assert guarda.get("/vat/cursos/nuevo/").status_code == 403
    assert guarda.get("/vat/cursos/nuevo/?centro=999999").status_code == 403


@pytest.mark.usefixtures("preview")
def test_the_embedded_course_pages_stay_the_native_ones(base, curso):
    editor = _client("add_curso", "change_curso", sse=True)
    for url in (
        f"/vat/cursos/nuevo/?centro={base['centro'].pk}&modal=1",
        f"/vat/cursos/{curso.pk}/editar/?modal=1",
    ):
        cuerpo = editor.get(url).content.decode()
        assert "closeEmbeddedCursoForm" in cuerpo and "/vat/react/assets/" not in cuerpo
    # The native embedded POST keeps its own answer (reload script), not the web API JSON.
    guardado = editor.post(
        f"/vat/cursos/{curso.pk}/editar/?modal=1", _post_curso(base, nombre="Nativo")
    )
    assert (
        guardado.status_code == 200
        and "window.parent.location.reload" in guardado.content.decode()
    )
    curso.refresh_from_db()
    assert curso.nombre == "Nativo"
