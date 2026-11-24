"""Create and edit of a PAS titular through G1 v1 (PAS06.02).

``POST /api/web/pas/personas/crear/`` and ``/personas/<pk>/editar/`` run the native
forms and services under ``permissions_any_required`` of ``pas.add_paspersona``
and ``pas.change_paspersona``; the local React entries keep those rules and the
native POST.
"""

import types

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, override_settings

from config.urls_all import urlpatterns as monolith_patterns
from core import web_gate
from core.models import Municipio, Provincia
from pas.models import (
    PasAviso,
    PasEstado,
    PasHistorialEstado,
    PasInvitacionDDJJ,
    PasPersona,
)
from pas.web_preview_backoffice import backoffice_preview_patterns

ROOT = "/api/web/pas/personas/"
INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)

pytestmark = pytest.mark.django_db


def _user(username, *codenames):
    user = get_user_model().objects.create_user(username)
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    for codename in codenames:
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label="pas", codename=codename)
        )
    return user


def _client(user):
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture(name="alta")
def alta_fixture():
    return _user("alta_pas", "add_paspersona")


@pytest.fixture(name="edita")
def edita_fixture():
    return _user("edita_pas", "change_paspersona")


@pytest.fixture(name="mundo")
def mundo_fixture():
    activo = PasEstado.objects.get_or_create(nombre="Activo")[0]
    baja = PasEstado.objects.get_or_create(nombre="Baja")[0]
    aviso = PasAviso.objects.create(codigo=8301, descripcion="Alta sintética")
    otro = PasAviso.objects.create(codigo=8302, descripcion="Solo baja")
    aviso.estados.add(activo)
    otro.estados.add(baja)
    provincia = Provincia.objects.create(nombre="Provincia A")
    municipio = Municipio.objects.create(nombre="Municipio A", provincia=provincia)
    ajena = Provincia.objects.create(nombre="Provincia B")
    ajeno = Municipio.objects.create(nombre="Municipio B", provincia=ajena)
    return {
        "activo": activo,
        "baja": baja,
        "aviso": aviso,
        "otro": otro,
        "provincia": provincia,
        "municipio": municipio,
        "ajena": ajena,
        "ajeno": ajeno,
    }


def _datos(mundo, **extra):
    datos = {
        "id_persona": 9001,
        "apellidos": "Pérez",
        "nombres": "Ana",
        "dni": 30111222,
        "cuit": "27301112224",
        "genero": "F",
        "provincia": mundo["provincia"].pk,
        "municipio": mundo["municipio"].pk,
        "domicilio": "Calle Falsa 123",
        "correo_electronico": "ana@example.org",
        "telefono_celular": "1155550000",
        "estado": mundo["activo"].pk,
        "avisos": [mundo["aviso"].pk],
    }
    datos.update(extra)
    return datos


@pytest.fixture(name="titular")
def titular_fixture(mundo):
    return PasPersona.objects.create(
        id_persona=1,
        apellidos="Apellido",
        nombres="Nombre",
        dni=30000001,
        provincia=mundo["provincia"],
        municipio=mundo["municipio"],
        estado=mundo["activo"],
        domicilio="Calle 1",
        calle="Calle",
        altura="1",
    )


def test_valid_create_registers_titular_history_notices_and_invitation(alta, mundo):
    respuesta = _client(alta).post(ROOT + "crear/", _datos(mundo))

    assert respuesta.status_code == 201
    assert respuesta["Cache-Control"] == "private, no-store"
    persona = PasPersona.objects.get(dni=30111222)
    assert respuesta.json() == {
        "id": persona.pk,
        "message": "Registro PAS creado correctamente.",
    }
    assert persona.estado == mundo["activo"]
    assert list(persona.avisos.all()) == [mundo["aviso"]]
    assert (persona.calle, persona.altura) == ("Calle Falsa", "123")
    historial = PasHistorialEstado.objects.get(persona=persona)
    assert historial.estado_anterior is None
    assert historial.usuario == alta
    assert PasInvitacionDDJJ.objects.filter(persona=persona).count() == 1


def test_create_rejections_use_the_native_texts_and_write_nothing(alta, mundo, titular):
    web = _client(alta)
    sin_avisos = web.post(ROOT + "crear/", _datos(mundo, avisos=[]))
    assert sin_avisos.status_code == 400
    assert sin_avisos.json()["errors"]["avisos"][0]["message"] == (
        "Este campo es requerido."
    )
    ajeno = web.post(ROOT + "crear/", _datos(mundo, avisos=[mundo["otro"].pk]))
    assert ajeno.status_code == 400
    assert "avisos" in ajeno.json()["errors"]
    otra_provincia = web.post(
        ROOT + "crear/", _datos(mundo, municipio=mundo["ajeno"].pk)
    )
    assert otra_provincia.status_code == 400
    assert "municipio" in otra_provincia.json()["errors"]
    duplicado = web.post(ROOT + "crear/", _datos(mundo, dni=titular.dni, id_persona=1))
    assert duplicado.status_code == 400
    assert {"id_persona", "dni"} <= set(duplicado.json()["errors"])
    assert PasPersona.objects.count() == 1
    assert not PasInvitacionDDJJ.objects.exists()


def test_options_come_from_the_form_querysets(alta, mundo):
    respuesta = _client(alta).get(ROOT + f"opciones/?provincia={mundo['provincia'].pk}")

    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert [p["label"] for p in datos["provincias"]] == ["Provincia A", "Provincia B"]
    assert datos["municipios"] == [
        {"value": str(mundo["municipio"].pk), "label": "Municipio A"}
    ]
    assert {"value": "F", "label": "Femenino"} in datos["generos"]
    assert datos["avisos_por_estado"][str(mundo["activo"].pk)] == [
        {"id": mundo["aviso"].pk, "text": "8301 - Alta sintética"}
    ]
    assert _client(alta).get(ROOT + "opciones/").json()["municipios"] == []


def test_edit_reads_initial_data_and_saves_without_state_or_notices(
    edita, mundo, titular
):
    web = _client(edita)
    lectura = web.get(f"{ROOT}{titular.pk}/")
    assert lectura.status_code == 200
    datos = lectura.json()
    assert datos["id"] == titular.pk
    assert datos["initial"]["apellidos"] == "Apellido"
    assert datos["initial"]["provincia"] == str(mundo["provincia"].pk)
    assert datos["estados"] == []

    respuesta = web.post(
        f"{ROOT}{titular.pk}/editar/",
        _datos(
            mundo,
            id_persona=1,
            dni=30000001,
            domicilio="Calle 1",
            estado=mundo["baja"].pk,
        ),
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "id": titular.pk,
        "message": "Registro PAS actualizado correctamente.",
    }
    titular.refresh_from_db()
    assert titular.apellidos == "Pérez"
    assert titular.estado == mundo["activo"]
    assert (titular.calle, titular.altura) == ("Calle", "1")
    assert not PasHistorialEstado.objects.exists()


def test_edit_rejection_and_unknown_titular(edita, mundo, titular):
    web = _client(edita)
    respuesta = web.post(
        f"{ROOT}{titular.pk}/editar/",
        _datos(mundo, id_persona=1, dni=30000001, apellidos=""),
    )

    assert respuesta.status_code == 400
    assert "apellidos" in respuesta.json()["errors"]
    titular.refresh_from_db()
    assert titular.apellidos == "Apellido"
    assert web.get(f"{ROOT}999999/").status_code == 404
    assert web.post(f"{ROOT}999999/editar/", _datos(mundo)).status_code == 404


def test_permissions_csrf_and_login(alta, edita, mundo, titular):
    assert Client().post(ROOT + "crear/", {}).status_code == 401
    solo_ver = _client(_user("ver_pas", "view_paspersona"))
    for metodo, url in (
        ("post", ROOT + "crear/"),
        ("get", ROOT + "opciones/"),
        ("get", f"{ROOT}{titular.pk}/"),
        ("post", f"{ROOT}{titular.pk}/editar/"),
    ):
        assert getattr(solo_ver, metodo)(url).status_code == 403, url
    assert _client(edita).post(ROOT + "crear/", _datos(mundo)).status_code == 403
    assert (
        _client(alta).post(f"{ROOT}{titular.pk}/editar/", _datos(mundo)).status_code
        == 403
    )
    assert _client(edita).get(ROOT + "opciones/").status_code == 200

    estricto = Client(enforce_csrf_checks=True)
    estricto.force_login(alta)
    assert estricto.post(ROOT + "crear/", _datos(mundo)).status_code == 403
    assert not PasHistorialEstado.objects.exists()
    assert _client(alta).put(ROOT + "crear/").status_code == 405


@pytest.fixture(name="runtime")
def runtime_fixture():
    with override_settings(
        SISOC_BACKEND="pas",
        ROOT_URLCONF="pas_runtime.urls",
        SISOC_BACKENDS={},
        INTERNAL_IPS=[],
    ):
        yield


@pytest.mark.usefixtures("runtime")
def test_runtime_accepts_only_a_post_signed_for_it(alta, mundo):
    web = _client(alta)
    target = ROOT + "crear/"
    for token in (None, "forged"):
        extra = {"RAW_URI": target}
        if token:
            extra["HTTP_X_SISOC_WEB_GATE"] = token
        respuesta = web.post(target, _datos(mundo), **extra)
        assert respuesta.status_code == 403
        assert respuesta.json() == {"detail": web_gate.DETAIL_REJECTED}
    assert not PasPersona.objects.exists()

    firmado = web_gate.sign(
        audience="pas",
        user_pk=alta.pk,
        session_key=web.cookies[settings.SESSION_COOKIE_NAME].value,
        method="POST",
        target=target,
    )
    respuesta = web.post(
        target, _datos(mundo), RAW_URI=target, HTTP_X_SISOC_WEB_GATE=firmado
    )

    assert respuesta.status_code == 201


def test_native_routes_are_unchanged(alta, edita, mundo, titular):
    pagina = _client(alta).get("/pas/crear")
    assert "pas/persona_form.html" in [t.name for t in pagina.templates]
    respuesta = _client(alta).post("/pas/crear", _datos(mundo))
    assert respuesta.status_code == 302
    persona = PasPersona.objects.get(dni=30111222)
    assert respuesta["Location"] == f"/pas/panel-control/{persona.pk}"
    editar = _client(edita).get(f"/pas/{titular.pk}/editar")
    assert "pas/persona_form.html" in [t.name for t in editar.templates]


@pytest.fixture(name="preview")
def preview_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    (tmp_path / "assets" / "app-1.js").write_text("console.log(1);", encoding="utf-8")
    module = types.ModuleType("pas_form_preview_urls")
    module.urlpatterns = backoffice_preview_patterns(tmp_path) + list(monolith_patterns)
    with override_settings(ROOT_URLCONF=module):
        yield


@pytest.mark.usefixtures("preview")
def test_preview_serves_the_index_only_behind_the_native_rules(
    alta, edita, mundo, titular
):
    crear = _client(alta).get("/pas/crear")
    assert crear.status_code == 200
    assert '/pas/react/assets/app-1.js"' in crear.content.decode()
    assert "no-store" in crear["Cache-Control"]
    assert "csrftoken" in crear.cookies
    assert _client(edita).get(f"/pas/{titular.pk}/editar").status_code == 200
    assert _client(edita).head(f"/pas/{titular.pk}/editar").content == b""
    assert _client(edita).get("/pas/999999/editar").status_code == 404
    assert Client().get("/pas/crear").status_code == 403
    assert _client(edita).get("/pas/crear").status_code == 403
    assert _client(alta).get(f"/pas/{titular.pk}/editar").status_code == 403

    nativo = _client(alta).post("/pas/crear", _datos(mundo))
    assert nativo.status_code == 302
    assert PasPersona.objects.filter(dni=30111222).exists()
