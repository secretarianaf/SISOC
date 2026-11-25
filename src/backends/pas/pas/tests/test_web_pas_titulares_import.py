"""Web API (G1 v1) of the PAS titulares import: ``/api/web/pas/titulares/importar/``."""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client

from core import web_gate
from core.models import Municipio, Provincia
from pas.models import PasEstado, PasPersona

URL = "/api/web/pas/titulares/importar/"
CABECERA = "Apellidos;Nombres;DNI;CUIL;Provincia;Municipio\n"
FILA_NUEVA = "Nueva;Beatriz;32123456;27321234560;Buenos Aires;La Plata\n"

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


def _client(user, **kwargs):
    client = Client(**kwargs)
    client.force_login(user)
    return client


def _csv(contenido, nombre="titulares.csv"):
    return SimpleUploadedFile(
        nombre, contenido.encode("utf-8"), content_type="text/csv"
    )


@pytest.fixture(name="importer")
def importer_fixture():
    return _client(_user("titulares_importa", "add_paspersona"))


@pytest.fixture(name="catalogo")
def catalogo_fixture():
    provincia = Provincia.objects.create(nombre="Buenos Aires")
    municipio = Municipio.objects.create(nombre="La Plata", provincia=provincia)
    estado, _ = PasEstado.objects.get_or_create(nombre="Activo")
    return provincia, municipio, estado


def test_anonymous_gets_401_json_on_get_and_post(client):
    assert client.get(URL).status_code == 401
    assert client.get(URL).json() == {"detail": web_gate.DETAIL_UNAUTHENTICATED}
    assert client.post(URL).status_code == 401


def test_needs_add_paspersona_like_the_native_route(catalogo):
    sin_permiso = _client(_user("titulares_ve", "view_paspersona"))

    assert sin_permiso.get(URL).status_code == 403
    envio = sin_permiso.post(URL, {"archivo": _csv(CABECERA + FILA_NUEVA)})
    assert envio.status_code == 403
    assert sin_permiso.get("/pas/titulares/importar").status_code == 403
    assert not PasPersona.objects.exists()


def test_post_without_csrf_is_403_and_other_methods_are_405(importer):
    csrf = Client(enforce_csrf_checks=True)
    csrf.force_login(_user("titulares_csrf", "add_paspersona"))

    assert csrf.post(URL).status_code == 403
    assert importer.put(URL).status_code == 405
    assert importer.delete(URL).status_code == 405


def test_get_projects_the_native_field(importer):
    respuesta = importer.get(URL)

    assert respuesta.status_code == 200
    assert respuesta["Cache-Control"] == "private, no-store"
    assert "Cookie" in respuesta["Vary"]
    assert respuesta.json() == {
        "breadcrumb": [
            {"text": "PAS", "url": "/pas/listar"},
            {"text": "Importar titulares", "url": None},
        ],
        "archivo": {"label": "Archivo CSV", "accept": ".csv"},
    }


def test_post_imports_new_titulares_and_omits_duplicates(importer, catalogo):
    provincia, municipio, estado = catalogo
    PasPersona.objects.create(
        id_persona=10,
        apellidos="Existente",
        nombres="Ana",
        dni=30111222,
        cuit="27301112220",
        provincia=provincia,
        municipio=municipio,
        estado=estado,
    )
    contenido = (
        CABECERA
        + "Existente;Ana;30111222;27301112220;Buenos Aires;La Plata\n"
        + FILA_NUEVA
        + "Rota;Carla;abc;27321234561;Buenos Aires;La Plata\n"
    )

    respuesta = importer.post(URL, {"archivo": _csv(contenido)})

    assert respuesta.status_code == 200
    assert respuesta["Cache-Control"] == "private, no-store"
    resultado = respuesta.json()["resultado"]
    assert resultado["total"] == 3
    assert resultado["creados"] == 1
    assert resultado["duplicados"] == 1
    assert len(resultado["errores"]) == 1
    assert resultado["errores"] == ["Fila 4: DNI y CUIT deben contener números."]
    nueva = PasPersona.objects.get(dni=32123456)
    assert nueva.invitacion_ddjj_vigente is not None
    assert PasPersona.objects.count() == 2


def test_post_service_errors_are_400_with_the_native_text_and_write_nothing(importer):
    respuesta = importer.post(URL, {"archivo": _csv("Apellidos;Nombres\nX;Y\n")})

    assert respuesta.status_code == 400
    mensajes = respuesta.json()["errors"]["archivo"]
    assert mensajes[0].startswith("Faltan columnas obligatorias: ")
    assert not PasPersona.objects.exists()


def test_post_rejects_wrong_extension_missing_file_and_oversize(importer):
    txt = importer.post(URL, {"archivo": _csv("x", nombre="titulares.txt")})
    assert txt.status_code == 400
    assert "archivo" in txt.json()["errors"]

    vacio = importer.post(URL, {})
    assert vacio.status_code == 400
    assert vacio.json()["errors"]["archivo"]

    grande = SimpleUploadedFile(
        "titulares.csv", b"a" * (10 * 1024 * 1024 + 1), content_type="text/csv"
    )
    respuesta = importer.post(URL, {"archivo": grande})
    assert respuesta.status_code == 400
    assert respuesta.json()["errors"] == {
        "archivo": ["El archivo CSV no puede superar los 10 MB."]
    }
    assert not PasPersona.objects.exists()


def test_native_route_still_serves_its_page_and_post(importer, catalogo):
    pagina = importer.get("/pas/titulares/importar")
    assert pagina.status_code == 200
    assert b"Importar titulares" in pagina.content

    respuesta = importer.post(
        "/pas/titulares/importar", {"archivo": _csv(CABECERA + FILA_NUEVA)}
    )
    assert respuesta.status_code == 200
    assert b"Nuevos: 1" in respuesta.content
    assert PasPersona.objects.filter(dni=32123456).exists()
