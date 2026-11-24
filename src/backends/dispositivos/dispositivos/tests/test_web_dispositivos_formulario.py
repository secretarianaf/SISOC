"""Web API (G1 v1) of the Dispositivos create and edit screens (DS03.01, DS03.02).

The API views inherit ``DispositivoCreateView`` / ``DispositivoUpdateView``, so
the form, the geography scope, the uploads and the save are the native ones.
These tests go through the public interface only: status, JSON, permissions,
queued messages and persisted effects. Monolith tests use ``config.settings_all``
(policy evaluated locally); the runtime test switches to
``SISOC_BACKEND="dispositivos"``, where only a request the core signed gets in.
"""

import json

import pytest
from django.conf import settings
from django.contrib.auth.models import Permission, User
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, override_settings
from django.urls import reverse

from core import web_gate
from core.models import Localidad, Municipio, Provincia
from dispositivos.models import Dispositivo
from users.models import ProfileTerritorialScope

ROOT = "/api/web/dispositivos/"
CREAR = ROOT + "crear/"
PERMISOS = ("view_dispositivo", "add_dispositivo", "change_dispositivo")

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _clean_cache():
    cache.clear()
    yield
    cache.clear()


def _user(username, *perms, provincial=False, scopes=()):
    user = User.objects.create_user(username)
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.es_usuario_provincial = provincial
    profile.save()
    for scope in scopes:
        ProfileTerritorialScope.objects.create(profile=profile, **scope)
    user.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="dispositivos", codename__in=perms
        )
    )
    return User.objects.get(pk=user.pk)


def _login(user):
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)
    client.get(ROOT + "listado/")
    return client


def _token(client):
    client.get(CREAR)
    return client.cookies["csrftoken"].value


@pytest.fixture(name="geo")
def geo_fixture():
    provincia = Provincia.objects.create(nombre="Buenos Aires")
    otra = Provincia.objects.create(nombre="Cordoba")
    municipio = Municipio.objects.create(nombre="La Plata", provincia=provincia)
    localidad = Localidad.objects.create(nombre="Tolosa", municipio=municipio)
    fuera = Municipio.objects.create(nombre="Capital", provincia=otra)
    return {
        "provincia": provincia,
        "otra": otra,
        "municipio": municipio,
        "localidad": localidad,
        "fuera": fuera,
    }


@pytest.fixture(name="admin")
def admin_fixture():
    return _user("ds03_admin", *PERMISOS)


@pytest.fixture(name="web")
def web_fixture(admin):
    return _login(admin)


def _datos(geo, **extra):
    datos = {
        "nombre_institucion": "Hogar Sintetico",
        "tipo_gestion": "estatal",
        "cuit_institucion": "20123456789",
        "provincia": str(geo["provincia"].pk),
        "municipio": str(geo["municipio"].pk),
        "calle": "Calle 1",
        "altura": "123",
        "telefono_prefijo": "221",
        "telefono_numero": "1234567",
        "correo_electronico": "hogar@example.com",
        "responsable_nombre_completo": "Ana Lopez",
        "responsable_dni": "12345678",
        "tipo_dispositivo": "refugio",
        "modalidad_funcionamiento": "permanente",
        "capacidad_total_plazas": "16_30",
        "dias_atencion": ["lunes", "martes"],
        "horarios_funcionamiento": ["manana"],
    }
    datos.update(extra)
    return datos


def _existente(geo, **extra):
    datos = {
        "nombre_institucion": "Dispositivo Previo",
        "tipo_gestion": "otra",
        "tipo_gestion_otra": "Cooperativa",
        "cuit_institucion": "20123456789",
        "provincia": geo["provincia"],
        "municipio": geo["municipio"],
        "calle": "Calle 9",
        "altura": "99",
        "telefono_prefijo": "221",
        "telefono_numero": "9876543",
        "responsable_nombre_completo": "Juan Perez",
        "responsable_dni": "87654321",
        "tipo_dispositivo": "refugio",
        "modalidad_funcionamiento": "permanente",
        "capacidad_total_plazas": "0_15",
        "poblacion_destinataria": ["hombres", "otro"],
    }
    datos.update(extra)
    return Dispositivo.objects.create(**datos)


def _post(client, url, datos, **extra):
    return client.post(
        url, datos, HTTP_X_CSRFTOKEN=_token(client), **extra
    )  # multipart by default


def _campo(payload, nombre):
    return next(campo for campo in payload["fields"] if campo["name"] == nombre)


def test_create_projects_the_native_form(web, geo):
    response = web.get(CREAR)

    assert response.status_code == 200
    assert response["Cache-Control"] == "private, no-store"
    data = response.json()
    assert data["is_edit"] is False
    assert data["has_errors"] is False
    assert [item["text"] for item in data["breadcrumb"]] == [
        "Dispositivos",
        "Nuevo dispositivo",
    ]
    nombre = _campo(data, "nombre_institucion")
    assert nombre["label"] == "Nombre completo de la institución"
    assert nombre["required"] is True
    assert nombre["widget"] == "text"
    assert nombre["attrs"]["maxlength"] == "255"
    cuit = _campo(data, "cuit_institucion")
    assert cuit["attrs"]["pattern"] == r"\d{11}"
    assert cuit["help_text"] == "Debe ingresar los 11 dígitos sin puntos ni guiones"
    provincia = _campo(data, "provincia")
    assert provincia["widget"] == "select"
    assert [c["label"] for c in provincia["choices"]] == [
        "---------",
        "Buenos Aires",
        "Cordoba",
    ]
    assert _campo(data, "municipio")["choices"] == [{"value": "", "label": "---------"}]
    assert _campo(data, "observaciones_adicionales")["widget"] == "textarea"
    assert [f["name"] for f in data["files"]] == [
        "documentacion_dispositivo",
        "documentacion_dispositivo_adicional_1",
        "documentacion_dispositivo_adicional_2",
        "documentacion_dispositivo_adicional_3",
        "documentacion_dispositivo_adicional_4",
    ]
    assert all(f["saved"] is None and f["accept"] for f in data["files"])
    assert data["multiples"]["dias_atencion"]["options"][0] == {
        "id": "id_dias_atencion_0",
        "value": "lunes",
        "label": "Lunes",
        "checked": False,
    }
    assert data["urls"] == {
        "listar": reverse("dispositivos_listar"),
        "municipios": reverse("ajax_load_municipios"),
        "localidades": reverse("ajax_load_localidades"),
        "address_preview": reverse("dispositivos_previsualizar_ubicacion"),
        "saved_location": "",
    }
    assert data["messages"] == []


def test_create_saves_with_uploads_and_queues_the_message(web, geo):
    archivo = SimpleUploadedFile(
        "protocolo.pdf", b"%PDF-1.4 sintetico", content_type="application/pdf"
    )

    response = _post(
        web,
        CREAR,
        _datos(
            geo, documentacion_dispositivo=archivo, poblacion_destinataria=["hombres"]
        ),
    )

    assert response.status_code == 200
    dispositivo = Dispositivo.objects.get(nombre_institucion="Hogar Sintetico")
    assert response.json() == {
        "ok": True,
        "redirect": reverse("dispositivos_detalle", kwargs={"pk": dispositivo.pk}),
    }
    assert dispositivo.cuit_institucion == "20123456789"
    assert dispositivo.dias_atencion == ["lunes", "martes"]
    assert dispositivo.poblacion_destinataria == ["hombres"]
    assert dispositivo.documentacion_dispositivo.name.endswith("protocolo.pdf")
    detalle = web.get(f"{ROOT}{dispositivo.pk}/")
    assert detalle.json()["messages"] == [
        {"message": "Dispositivo creado correctamente.", "level": "success"}
    ]
    dispositivo.documentacion_dispositivo.delete(save=False)


def test_create_with_a_url_encoded_body_is_accepted(web, geo):
    response = web.post(
        CREAR,
        _datos(geo),
        HTTP_X_CSRFTOKEN=_token(web),
        content_type="application/x-www-form-urlencoded",
    )

    assert response.status_code in (200, 400)
    assert response.status_code != 415


def test_invalid_create_answers_400_with_the_bound_form(web, geo):
    response = _post(
        web,
        CREAR,
        _datos(
            geo, nombre_institucion="", tipo_dispositivo="otro", dias_atencion=["lunes"]
        ),
    )

    assert response.status_code == 400
    data = response.json()
    assert data["has_errors"] is True
    assert _campo(data, "nombre_institucion")["errors"] == [
        {"message": "Este campo es requerido.", "code": "required"}
    ]
    assert _campo(data, "tipo_dispositivo_otro")["errors"][0]["message"] == (
        "Este campo es obligatorio cuando el tipo de dispositivo es 'Otro'."
    )
    assert _campo(data, "tipo_dispositivo")["value"] == "otro"
    assert _campo(data, "calle")["value"] == "Calle 1"
    assert _campo(data, "municipio")["value"] == str(geo["municipio"].pk)
    assert [o["checked"] for o in data["multiples"]["dias_atencion"]["options"]][
        :2
    ] == [
        True,
        False,
    ]
    assert not Dispositivo.objects.exists()


def test_invalid_upload_extension_is_rejected_and_nothing_is_saved(web, geo):
    archivo = SimpleUploadedFile("x.html", b"<b>x</b>", content_type="text/html")

    response = _post(web, CREAR, _datos(geo, documentacion_dispositivo=archivo))

    assert response.status_code == 400
    assert response.json()["has_errors"] is True
    assert not Dispositivo.objects.exists()


def test_geography_outside_the_actor_scope_is_rejected(geo):
    provincial = _user(
        "ds03_provincial",
        *PERMISOS,
        provincial=True,
        scopes=[{"provincia": geo["provincia"]}],
    )
    client = _login(provincial)

    data = client.get(CREAR).json()
    assert [c["label"] for c in _campo(data, "provincia")["choices"]] == [
        "---------",
        "Buenos Aires",
    ]
    response = _post(
        client,
        CREAR,
        _datos(geo, provincia=str(geo["otra"].pk), municipio=str(geo["fuera"].pk)),
    )
    assert response.status_code == 400
    assert not Dispositivo.objects.exists()


def test_edit_projects_the_saved_values_and_files(web, geo):
    dispositivo = _existente(geo)
    dispositivo.documentacion_dispositivo.save(
        "guardado.pdf", SimpleUploadedFile("guardado.pdf", b"%PDF-1.4"), save=True
    )

    response = web.get(f"{ROOT}{dispositivo.pk}/editar/")

    assert response.status_code == 200
    data = response.json()
    assert data["is_edit"] is True
    assert [item["text"] for item in data["breadcrumb"]] == [
        "Dispositivos",
        "Dispositivo Previo",
        "Editar",
    ]
    assert _campo(data, "tipo_gestion")["value"] == "otra"
    assert _campo(data, "tipo_gestion_otra")["value"] == "Cooperativa"
    assert _campo(data, "municipio")["value"] == str(geo["municipio"].pk)
    assert [
        o["checked"] for o in data["multiples"]["poblacion_destinataria"]["options"]
    ] == [
        True,
        False,
        False,
        False,
        False,
        True,
    ]
    guardado = data["files"][0]["saved"]
    assert guardado["pdf"] is True
    assert guardado["label"].endswith("guardado.pdf")
    assert guardado["url"].endswith("guardado.pdf")
    assert data["files"][1]["saved"] is None
    assert data["urls"]["saved_location"] == reverse(
        "dispositivos_ubicacion", args=[dispositivo.pk]
    )
    dispositivo.documentacion_dispositivo.delete(save=False)


def test_edit_saves_changes_and_clears_a_file(web, geo):
    dispositivo = _existente(geo)
    dispositivo.documentacion_dispositivo.save(
        "borrar.pdf", SimpleUploadedFile("borrar.pdf", b"%PDF-1.4"), save=True
    )
    url = f"{ROOT}{dispositivo.pk}/editar/"

    response = _post(
        web,
        url,
        _datos(
            geo,
            nombre_institucion="Dispositivo Renombrado",
            **{"documentacion_dispositivo-clear": "on"},
        ),
    )

    assert response.status_code == 200
    assert response.json()["redirect"] == reverse(
        "dispositivos_detalle", kwargs={"pk": dispositivo.pk}
    )
    dispositivo.refresh_from_db()
    assert dispositivo.nombre_institucion == "Dispositivo Renombrado"
    assert not dispositivo.documentacion_dispositivo
    assert web.get(f"{ROOT}{dispositivo.pk}/").json()["messages"] == [
        {"message": "Dispositivo actualizado correctamente.", "level": "success"}
    ]


def test_edit_outside_the_scope_is_404(geo):
    dispositivo = _existente(geo, provincia=geo["otra"], municipio=geo["fuera"])
    provincial = _user(
        "ds03_scope",
        *PERMISOS,
        provincial=True,
        scopes=[{"provincia": geo["provincia"]}],
    )
    client = _login(provincial)

    assert client.get(f"{ROOT}{dispositivo.pk}/editar/").status_code == 404
    assert client.get(f"{ROOT}999999/editar/").status_code == 404


def test_anonymous_and_missing_permissions_are_refused(geo):
    dispositivo = _existente(geo)
    anonimo = Client()
    solo_lectura = _login(_user("ds03_lector", "view_dispositivo"))
    solo_alta = _login(_user("ds03_alta", "view_dispositivo", "add_dispositivo"))

    assert anonimo.get(CREAR).status_code == 401
    assert solo_lectura.get(CREAR).status_code == 403
    assert solo_lectura.get(f"{ROOT}{dispositivo.pk}/editar/").status_code == 403
    assert solo_alta.get(f"{ROOT}{dispositivo.pk}/editar/").status_code == 403
    assert solo_alta.get(CREAR).status_code == 200


def test_a_post_without_csrf_and_a_json_body_are_refused(web, geo):
    sin_csrf = web.post(CREAR, _datos(geo))
    json_body = web.post(
        CREAR,
        json.dumps(_datos(geo)),
        content_type="application/json",
        HTTP_X_CSRFTOKEN=_token(web),
    )

    assert sin_csrf.status_code == 403
    assert json_body.status_code == 415
    assert not Dispositivo.objects.exists()


def test_other_methods_are_refused(web):
    assert web.delete(CREAR, HTTP_X_CSRFTOKEN=_token(web)).status_code == 405


@pytest.fixture(name="runtime")
def runtime_fixture():
    with override_settings(
        SISOC_BACKEND="dispositivos",
        ROOT_URLCONF="dispositivos_runtime.urls",
        SISOC_BACKENDS={},
        INTERNAL_IPS=[],
    ):
        yield


def _signed(user, client, target, method="GET"):
    return web_gate.sign(
        audience="dispositivos",
        user_pk=user.pk,
        session_key=client.cookies[settings.SESSION_COOKIE_NAME].value,
        method=method,
        target=target,
        now=None,
    )


@pytest.mark.usefixtures("runtime")
def test_runtime_serves_only_a_request_the_core_signed(web, admin, geo):
    assert web.get(CREAR, RAW_URI=CREAR).status_code == 403
    firmada = web.get(
        CREAR, RAW_URI=CREAR, HTTP_X_SISOC_WEB_GATE=_signed(admin, web, CREAR)
    )

    assert firmada.status_code == 200
    assert firmada.json()["is_edit"] is False
