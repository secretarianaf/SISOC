"""V06.01: web API de contactos de institución (``/api/web/vat/institucion/contactos/``). Datos sintéticos."""

import itertools

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from rest_framework.test import APIClient

from core.models import Localidad, Municipio, Provincia
from VAT.models import Centro, InstitucionContacto

pytestmark = pytest.mark.django_db

ROOT = "/api/web/vat/institucion/contactos/"
NATIVA = "/vat/institucion/contactos/"
_COUNTER = itertools.count()


def _client(*codes, csrf=False):
    user = get_user_model().objects.create_user(f"ic{next(_COUNTER)}")
    user.user_permissions.add(
        *Permission.objects.filter(content_type__app_label="VAT", codename__in=codes)
    )
    client = APIClient(enforce_csrf_checks=csrf)
    client.force_login(user)
    return client


@pytest.fixture(name="centro")
def centro_fixture():
    provincia = Provincia.objects.create(nombre="Buenos Aires")
    municipio = Municipio.objects.create(nombre="La Plata", provincia=provincia)
    localidad = Localidad.objects.create(nombre="Tolosa", municipio=municipio)
    return Centro.objects.create(
        nombre="CFP 401",
        codigo="060144900",
        provincia=provincia,
        municipio=municipio,
        localidad=localidad,
    )


@pytest.fixture(name="contacto")
def contacto_fixture(centro):
    return InstitucionContacto.objects.create(
        centro=centro,
        tipo="email",
        valor="cfp@example.com",
        es_principal=True,
        observaciones="Atiende de lunes a viernes",
    )


def test_access_follows_each_native_route_rule(contacto):
    rutas = {
        ROOT: "view",
        f"{ROOT}{contacto.pk}/": "view",
        f"{ROOT}nuevo/": "add",
        f"{ROOT}{contacto.pk}/editar/": "change",
        f"{ROOT}{contacto.pk}/eliminar/": "delete",
    }
    for url, accion in rutas.items():
        assert APIClient().get(url).status_code == 401
        for otra in {"view", "add", "change", "delete"} - {accion}:
            assert _client(f"{otra}_institucioncontacto").get(url).status_code == 403
        assert _client(f"{accion}_institucioncontacto").get(url).status_code == 200
    assert _client("view_institucioncontacto").get(f"{ROOT}999999/").status_code == 404


def test_list_projects_the_native_rows_and_filters(contacto, centro):
    otro = InstitucionContacto.objects.create(
        centro=centro, tipo="telefono", valor="221 555"
    )
    client = _client("view_institucioncontacto", "change_institucioncontacto")
    data = client.get(ROOT).json()
    assert data["permisos"] == {"editar": True, "eliminar": False}
    assert data["urls"] == {"list": NATIVA, "create": f"{NATIVA}nuevo/"}
    fila = {r["id"]: r for r in data["results"]}[contacto.pk]
    assert fila["centro"] == "CFP 401"
    assert (fila["tipo"], fila["valor"], fila["es_principal"]) == (
        "Email",
        "cfp@example.com",
        True,
    )
    assert fila["update_url"] == f"{NATIVA}{contacto.pk}/editar/"
    por_tipo = client.get(ROOT, {"tipo": "telefono"}).json()["results"]
    assert [r["id"] for r in por_tipo] == [otro.pk]
    por_texto = client.get(ROOT, {"busqueda": "cfp@"}).json()
    assert [r["id"] for r in por_texto["results"]] == [contacto.pk]
    assert por_texto["busqueda"] == "cfp@"
    assert client.get(ROOT, {"page": 9}).status_code == 404


def test_detail_projects_the_native_context(contacto):
    data = _client("view_institucioncontacto").get(f"{ROOT}{contacto.pk}/").json()
    assert data["centro"] == "CFP 401"
    assert (data["tipo"], data["valor"]) == ("Email", "cfp@example.com")
    assert data["vigencia_hasta"] == "Vigente"
    assert data["observaciones"] == "Atiende de lunes a viernes"
    assert data["urls"]["delete"] == f"{NATIVA}{contacto.pk}/eliminar/"
    assert data["messages"] == []


def test_form_projects_the_native_widgets_and_the_locked_centro(contacto, centro):
    client = _client("change_institucioncontacto", "add_institucioncontacto")
    data = client.get(f"{ROOT}{contacto.pk}/editar/").json()
    assert data["editing"] is True
    por_nombre = {f["name"]: f for f in data["fields"]}
    assert list(por_nombre) == [
        "centro",
        "nombre_contacto",
        "rol_area",
        "documento",
        "telefono_contacto",
        "email_contacto",
        "es_principal",
    ]
    assert por_nombre["centro"]["value"] == str(centro.pk)
    assert por_nombre["documento"]["attrs"]["maxlength"] == "20"
    libre = client.get(f"{ROOT}nuevo/").json()
    assert libre["editing"] is False
    assert "disabled" not in libre["fields"][0]["attrs"]
    bloqueado = client.get(f"{ROOT}nuevo/", {"centro": centro.pk}).json()
    assert bloqueado["fields"][0]["attrs"]["disabled"] == "disabled"
    assert bloqueado["fields"][0]["value"] == str(centro.pk)


def test_create_persists_queues_the_message_and_rejection_keeps_data(centro):
    client = _client("add_institucioncontacto", "view_institucioncontacto")
    rechazo = client.post(
        f"{ROOT}nuevo/", {"centro": centro.pk, "nombre_contacto": "Ana"}
    )
    assert rechazo.status_code == 400
    assert InstitucionContacto.objects.count() == 0
    respuesta = client.post(
        f"{ROOT}nuevo/",
        {
            "centro": centro.pk,
            "nombre_contacto": "Ana Gómez",
            "email_contacto": "ana@example.com",
            "es_principal": "on",
        },
        format="multipart",
    )
    assert respuesta.status_code == 200
    assert respuesta.json() == {"ok": True, "redirect": NATIVA}
    nuevo = InstitucionContacto.objects.get()
    assert (nuevo.nombre_contacto, nuevo.es_principal) == ("Ana Gómez", True)
    assert client.get(ROOT).json()["messages"] == [
        {"message": "Contacto creado exitosamente.", "level": "success"}
    ]


def test_update_persists_and_rejection_keeps_the_stored_data(contacto, centro):
    client = _client("change_institucioncontacto")
    url = f"{ROOT}{contacto.pk}/editar/"
    assert client.post(url, {"centro": ""}, format="multipart").status_code == 400
    contacto.refresh_from_db()
    assert contacto.valor == "cfp@example.com"
    respuesta = client.post(
        url,
        {"centro": centro.pk, "nombre_contacto": "Beto", "telefono_contacto": "221"},
        format="multipart",
    )
    assert respuesta.status_code == 200
    contacto.refresh_from_db()
    assert contacto.nombre_contacto == "Beto"


def test_delete_shows_the_summary_and_removes_through_the_native_view(contacto):
    client = _client("delete_institucioncontacto", "view_institucioncontacto")
    url = f"{ROOT}{contacto.pk}/eliminar/"
    assert client.get(url).json() == {
        "valor": "cfp@example.com",
        "tipo": "Email",
        "centro": "CFP 401",
        "urls": {"detail": f"{NATIVA}{contacto.pk}/"},
    }
    assert InstitucionContacto.objects.count() == 1
    assert client.post(url).json() == {"ok": True, "redirect": NATIVA}
    assert InstitucionContacto.objects.count() == 0
    assert client.post(url).status_code == 404


def test_writes_require_csrf_and_the_write_permission(contacto, centro):
    todos = (
        "add_institucioncontacto",
        "change_institucioncontacto",
        "delete_institucioncontacto",
    )
    sin_csrf = _client(*todos, csrf=True)
    assert sin_csrf.post(f"{ROOT}nuevo/", {"centro": centro.pk}).status_code == 403
    assert sin_csrf.post(f"{ROOT}{contacto.pk}/eliminar/").status_code == 403
    lector = _client("view_institucioncontacto")
    assert lector.post(f"{ROOT}nuevo/", {"centro": centro.pk}).status_code == 403
    assert lector.post(f"{ROOT}{contacto.pk}/eliminar/").status_code == 403
    assert (
        lector.post(f"{ROOT}{contacto.pk}/editar/", {"centro": centro.pk}).status_code
        == 403
    )
    assert InstitucionContacto.objects.count() == 1
