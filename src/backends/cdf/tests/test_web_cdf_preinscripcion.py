"""Web API (G1 v1) of the CDF preinscription (CDF03.02).

The searches run the native service functions and the POST runs
``procesar_preinscripcion`` (shared with the native view). RENAPER is always
simulated (``consultar_datos_renaper``) and the unmanaged padrón table is
replaced by an in-memory double: no network, no real data.
"""

from datetime import date
from types import SimpleNamespace

import pytest
from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.contrib.messages import get_messages
from django.test import Client

from centrodefamilia.models import (
    Actividad,
    Beneficiario,
    BeneficiarioResponsable,
    BeneficiariosResponsablesRenaper,
    Categoria,
    Centro,
    Responsable,
)
from core.models import Provincia

ROOT = "/api/web/cdf/beneficiarios/"
IMPL = "centrodefamilia.services.beneficiarios_service"

pytestmark = pytest.mark.django_db


def _user(username, *, view=True):
    user = User.objects.create_user(username)
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    if view:
        user.user_permissions.add(
            Permission.objects.get(
                content_type=ContentType.objects.get_for_model(Centro),
                codename="view_centro",
            )
        )
    return User.objects.get(pk=user.pk)


def _client(user, csrf=False):
    client = Client(enforce_csrf_checks=csrf)
    client.force_login(user)
    return client


@pytest.fixture(name="actor")
def actor_fixture():
    return _user("cdf_preinscribe")


@pytest.fixture(name="provincia")
def provincia_fixture():
    return Provincia.objects.create(nombre="Provincia Padrón")


@pytest.fixture(name="actividad")
def actividad_fixture():
    return Actividad.objects.create(
        nombre="Fútbol", categoria=Categoria.objects.create(nombre="Deportes")
    )


class _Padron:
    """In-memory stand-in of the unmanaged ``PadronBeneficiarios`` table."""

    def __init__(self, rows):
        self.rows = rows
        self.objects = self

    def filter(self, cuil):
        return SimpleNamespace(first=lambda: self.rows.get(cuil))


@pytest.fixture(name="padron")
def padron_fixture(monkeypatch):
    fila = SimpleNamespace(
        dni="45111222", genero="F", provincia_tabla="BA", municipio_tabla="Matanza"
    )
    monkeypatch.setattr(f"{IMPL}.PadronBeneficiarios", _Padron({"20451112223": fila}))


DATOS_API = {
    "nombres": "Sofía",
    "apellido": "Pérez",
    "fechaNacimiento": "2012-03-04",
    "calle": "Siempreviva",
    "numero": "742",
    "cpostal": "1754",
    "provincia": "BUENOS AIRES",
    "municipio": "LA MATANZA",
    "ciudad": "SAN JUSTO",
}


@pytest.fixture(name="renaper")
def renaper_fixture(monkeypatch):
    llamadas = []

    def consultar(dni, sexo):
        llamadas.append((str(dni), sexo))
        if str(dni) == "99999999":
            return {"success": False, "error": "No se encontraron datos en RENAPER"}
        return {
            "success": True,
            "datos_api": dict(DATOS_API, dni=str(dni), genero=sexo),
            "data": {"nombre": "Ana", "apellido": "Resp", "dni": str(dni), "cuil": ""},
        }

    monkeypatch.setattr(f"{IMPL}.consultar_datos_renaper", consultar)
    return llamadas


def _responsable(**over):
    datos = {
        "cuil": 27285551113,
        "dni": 28555111,
        "apellido": "Gómez",
        "nombre": "Marta",
        "genero": "F",
        "fecha_nacimiento": date(1980, 5, 12),
        "vinculo_parental": "Padre/Madre",
        "calle": "Calle Vieja",
    }
    datos.update(over)
    return Responsable.objects.create(**datos)


def _post_datos(provincia, actividad=None, **over):
    datos = {
        "beneficiario_nombre": "Sofía",
        "beneficiario_apellido": "Pérez",
        "beneficiario_dni": "45111222",
        "beneficiario_cuil": "20451112223",
        "beneficiario_genero": "F",
        "beneficiario_fecha_nacimiento": "2012-03-04",
        "beneficiario_domicilio": "Siempreviva 742",
        "beneficiario_provincia": str(provincia.pk),
        "beneficiario_calle": "Siempreviva",
        "beneficiario_maximo_nivel_educativo": "Primario incompleto",
        "beneficiario_actividad_preferida": ["Deportiva", "Educativa"],
        "beneficiario_estado_academico": "false",
        "beneficiario_actividades_extracurriculares": "true" if actividad else "false",
        "responsable_nombre": "Ana",
        "responsable_apellido": "Resp",
        "responsable_dni": "30111222",
        "responsable_cuil": "27301112224",
        "responsable_genero": "F",
        "responsable_fecha_nacimiento": "1985-01-02",
        "responsable_vinculo_parental": "Tutor/Tutora",
        "responsable_calle": "Siempreviva",
        "responsable_provincia": str(provincia.pk),
    }
    if actividad:
        datos["beneficiario_actividades_detalle"] = [str(actividad.pk)]
    datos.update(over)
    return {k: v for k, v in datos.items() if v is not None}


# --- options ------------------------------------------------------------------


def test_options_project_only_the_rendered_fields(actor, provincia, actividad):
    respuesta = _client(actor).get(f"{ROOT}preinscripcion/options/")

    assert respuesta.status_code == 200
    assert respuesta["Cache-Control"] == "private, no-store"
    data = respuesta.json()
    beneficiario = {f["name"]: f for f in data["beneficiario"]}
    responsable = {f["name"]: f for f in data["responsable"]}
    assert "creado_por" not in beneficiario and "creado_por" not in responsable
    assert list(beneficiario)[:6] == [
        "nombre",
        "apellido",
        "dni",
        "cuil",
        "genero",
        "fecha_nacimiento",
    ]
    assert beneficiario["nombre"]["attrs"]["readonly"] == ""
    assert (
        beneficiario["nombre"]["attrs"]["class"]
        == "form-control bg-secondary textinput"
    )
    assert beneficiario["genero"]["kind"] == "select"
    assert "disabled" in beneficiario["genero"]["attrs"]
    assert beneficiario["fecha_nacimiento"]["attrs"]["type"] == "date"
    assert beneficiario["actividad_preferida"]["kind"] == "selectmultiple"
    assert [c["value"] for c in beneficiario["actividad_preferida"]["choices"]] == [
        "Deportiva",
        "Cultural/Artística",
        "Educativa",
    ]
    assert beneficiario["actividades_detalle"]["kind"] == "checkboxmultiple"
    assert beneficiario["actividades_detalle"]["choices"] == [
        {"value": str(actividad.pk), "label": "Fútbol"}
    ]
    assert beneficiario["estado_academico"]["kind"] == "checkbox"
    assert beneficiario["provincia"]["required"] is True
    assert beneficiario["municipio"]["required"] is False
    assert {"value": str(provincia.pk), "label": "Provincia Padrón"} in beneficiario[
        "provincia"
    ]["choices"]
    assert [c["label"] for c in responsable["vinculo_parental"]["choices"]][1:] == [
        "Padre/Madre",
        "Tutor/Tutora",
    ]
    assert data["urls"]["municipios"] == "/ajax/load-municipios/"


# --- searches -----------------------------------------------------------------


def test_cuil_search_texts_and_cache(actor, padron, renaper):
    client = _client(actor)
    vacio = client.get(f"{ROOT}buscar-cuil/")
    assert (vacio.status_code, vacio.json()) == (
        400,
        {"status": "error", "message": "Debe ingresar un CUIL"},
    )
    fuera = client.get(f"{ROOT}buscar-cuil/", {"cuil": "20000000001"})
    assert fuera.json() == {
        "status": "not_found",
        "message": "El CUIL ingresado no se encuentra en la base de datos",
    }
    assert "renaper_cache" not in client.session

    posible = client.get(f"{ROOT}buscar-cuil/", {"cuil": "20451112223"})

    assert posible.status_code == 200
    data = posible.json()
    assert data["status"] == "possible"
    assert data["data"]["nombre"] == "Sofía"
    assert data["data"]["domicilio"] == "Siempreviva 742"
    assert data["data"]["provincia_tabla"] == "BA"
    assert renaper == [("45111222", "F")]
    assert (
        client.session["renaper_cache"]["beneficiario_45111222_F"]["apellido"]
        == "Pérez"
    )


def test_cuil_search_existing_and_renaper_failure(
    actor, padron, monkeypatch, provincia
):
    _beneficiario = Beneficiario.objects.create(
        cuil=20451112223,
        dni=45111222,
        apellido="Pérez",
        nombre="Sofía",
        genero="F",
        fecha_nacimiento=date(2012, 3, 4),
        domicilio="D",
        calle="C",
        maximo_nivel_educativo="Primario incompleto",
        responsable=_responsable(),
        provincia=provincia,
    )
    client = _client(actor)
    assert client.get(f"{ROOT}buscar-cuil/", {"cuil": "20451112223"}).json() == {
        "status": "exists",
        "message": "El CUIL ingresado ya se encuentra en el programa.",
    }
    _beneficiario.delete()
    monkeypatch.setattr(
        f"{IMPL}.consultar_datos_renaper", lambda dni, sexo: {"success": False}
    )
    assert client.get(f"{ROOT}buscar-cuil/", {"cuil": "20451112223"}).json() == {
        "status": "not_found",
        "message": "No se encontraron datos en RENAPER",
    }
    assert "renaper_cache" not in client.session

    def falla(dni, sexo):
        raise RuntimeError("caída simulada")

    monkeypatch.setattr(f"{IMPL}.consultar_datos_renaper", falla)
    error = client.get(f"{ROOT}buscar-cuil/", {"cuil": "20451112223"})
    assert (error.status_code, error.json()["message"]) == (
        500,
        "Error al buscar CUIL: caída simulada",
    )


def test_responsable_search_texts_and_cache(actor, renaper, provincia):
    existente = _responsable(provincia=provincia, prefijo_celular="11")
    client = _client(actor)
    falta = client.get(f"{ROOT}buscar-responsable/", {"dni": "28555111"})
    assert (falta.status_code, falta.json()["message"]) == (
        400,
        "Debe ingresar DNI y sexo",
    )

    hay = client.get(f"{ROOT}buscar-responsable/", {"dni": "28555111", "sexo": "F"})
    data = hay.json()
    assert data["status"] == "exists"
    assert data["cantidad_beneficiarios"] == 0
    assert data["message"] == "Este Responsable ya tiene 0 beneficiarios a su cargo"
    assert data["data"]["provincia"] == provincia.pk
    assert data["data"]["fecha_nacimiento"] == "1980-05-12"
    assert renaper == []
    assert existente.pk

    no = client.get(f"{ROOT}buscar-responsable/", {"dni": "99999999", "sexo": "M"})
    assert no.json() == {
        "status": "not_found",
        "message": "No se encontraron datos en RENAPER",
    }
    posible = client.get(f"{ROOT}buscar-responsable/", {"dni": "30111222", "sexo": "F"})
    assert posible.json()["status"] == "possible"
    assert "responsable_30111222_F" in client.session["renaper_cache"]
    assert "responsable_99999999_M" not in client.session["renaper_cache"]


def test_searches_answer_exactly_like_the_native_endpoints(actor, padron, renaper):
    for native, api, params in (
        ("buscar-cuil", "buscar-cuil", {"cuil": "20451112223"}),
        ("buscar-cuil", "buscar-cuil", {}),
        ("buscar-responsable", "buscar-responsable", {"dni": "30111222", "sexo": "F"}),
        ("buscar-responsable", "buscar-responsable", {"dni": "1"}),
    ):
        nativa = _client(actor).get(f"/centrodefamilia/beneficiarios/{native}/", params)
        web = _client(actor).get(f"{ROOT}{api}/", params)
        assert (web.status_code, web.json()) == (nativa.status_code, nativa.json())


# --- POST -----------------------------------------------------------------------


def test_post_creates_both_rows_link_and_renaper_data(
    actor, padron, renaper, provincia, actividad
):
    client = _client(actor)
    client.get(f"{ROOT}buscar-cuil/", {"cuil": "20451112223"})
    client.get(f"{ROOT}buscar-responsable/", {"dni": "30111222", "sexo": "F"})
    llamadas_busqueda = len(renaper)

    respuesta = client.post(f"{ROOT}preinscripcion/", _post_datos(provincia, actividad))

    assert respuesta.status_code == 200
    assert respuesta["Cache-Control"] == "private, no-store"
    assert respuesta.json() == {
        "status": "success",
        "message": "Preinscripción confirmada exitosamente",
        "toast": "Datos cargados con éxito",
    }
    beneficiario = Beneficiario.objects.get(cuil=20451112223)
    responsable = Responsable.objects.get(dni=30111222)
    assert (beneficiario.responsable_id, beneficiario.creado_por_id) == (
        responsable.pk,
        actor.pk,
    )
    assert responsable.creado_por_id == actor.pk
    assert beneficiario.actividad_preferida == ["Deportiva", "Educativa"]
    assert list(beneficiario.actividades_detalle.values_list("pk", flat=True)) == [
        actividad.pk
    ]
    vinculo = BeneficiarioResponsable.objects.get(beneficiario=beneficiario)
    assert (vinculo.responsable_id, vinculo.vinculo_parental) == (
        responsable.pk,
        "Tutor/Tutora",
    )
    renaper_rows = set(
        BeneficiariosResponsablesRenaper.objects.values_list("tipo", "dni", "apellido")
    )
    assert renaper_rows == {
        ("Beneficiario", "45111222", "Pérez"),
        ("Responsable", "30111222", "Pérez"),
    }
    # Both RENAPER records came from the session cache: no new lookup.
    assert len(renaper) == llamadas_busqueda
    assert "renaper_cache" not in client.session
    siguiente = client.get("/centrodefamilia/beneficiarios/beneficiarios/")
    assert not list(get_messages(siguiente.wsgi_request))


def test_post_without_vinculo_answers_400_with_empty_errors(actor, provincia):
    respuesta = _client(actor).post(
        f"{ROOT}preinscripcion/",
        _post_datos(provincia, responsable_vinculo_parental=None),
    )

    assert (respuesta.status_code, respuesta.json()) == (
        400,
        {"status": "error", "errors": {}},
    )
    assert not Beneficiario.objects.exists() and not Responsable.objects.exists()


def test_post_invalid_beneficiario_keeps_the_native_effects(actor, provincia, renaper):
    respuesta = _client(actor).post(
        f"{ROOT}preinscripcion/",
        _post_datos(provincia, beneficiario_maximo_nivel_educativo=None),
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["errors"] == {
        "beneficiario": {"maximo_nivel_educativo": ["Este campo es requerido."]}
    }
    assert not Beneficiario.objects.exists()
    # Native parity: the new responsable is saved before the beneficiary fails.
    assert Responsable.objects.filter(dni=30111222).count() == 1
    assert not BeneficiariosResponsablesRenaper.objects.exists()


def test_post_repeated_fails_on_unique_and_does_not_duplicate(
    actor, provincia, renaper
):
    client = _client(actor)
    assert (
        client.post(f"{ROOT}preinscripcion/", _post_datos(provincia)).status_code == 200
    )

    otra = client.post(f"{ROOT}preinscripcion/", _post_datos(provincia))

    assert otra.status_code == 400
    assert set(otra.json()["errors"]["beneficiario"]) == {"cuil", "dni"}
    assert Beneficiario.objects.count() == 1 and Responsable.objects.count() == 1


def test_post_updates_an_existing_responsable_without_renaper(
    actor, provincia, renaper
):
    existente = _responsable(dni=30111222, cuil=27301112224, calle="Calle Vieja")

    respuesta = _client(actor).post(
        f"{ROOT}preinscripcion/",
        _post_datos(provincia, responsable_calle="Calle Nueva"),
    )

    assert respuesta.status_code == 200
    existente.refresh_from_db()
    assert existente.calle == "Calle Nueva"
    assert existente.creado_por_id is None
    assert Responsable.objects.count() == 1
    tipos = set(BeneficiariosResponsablesRenaper.objects.values_list("tipo", flat=True))
    assert tipos == {"Beneficiario"}


def test_post_error_answers_500_with_the_native_text(actor, provincia, monkeypatch):
    def rompe(*_args):
        raise RuntimeError("boom")

    monkeypatch.setattr(f"{IMPL}.procesar_formularios", rompe)

    respuesta = _client(actor).post(f"{ROOT}preinscripcion/", _post_datos(provincia))

    assert (respuesta.status_code, respuesta.json()) == (
        500,
        {"status": "error", "message": "Error al guardar: boom"},
    )


def test_access_csrf_and_methods(actor, provincia, renaper):
    sin_permiso = _client(_user("sin_view_pre", view=False))
    for url in (
        "preinscripcion/options/",
        "buscar-cuil/?cuil=1",
        "buscar-responsable/",
    ):
        assert Client().get(f"{ROOT}{url}").status_code == 401
        assert sin_permiso.get(f"{ROOT}{url}").status_code == 403
    assert (
        sin_permiso.post(f"{ROOT}preinscripcion/", _post_datos(provincia)).status_code
        == 403
    )
    sin_csrf = _client(actor, csrf=True).post(
        f"{ROOT}preinscripcion/", _post_datos(provincia)
    )
    assert sin_csrf.status_code == 403
    assert not Beneficiario.objects.exists() and not Responsable.objects.exists()
    assert _client(actor).get(f"{ROOT}preinscripcion/").status_code == 405
    assert _client(actor).post(f"{ROOT}preinscripcion/options/").status_code == 405
