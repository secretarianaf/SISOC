"""V06.01: web API de ubicaciones de institución (``/api/web/vat/institucion/ubicaciones/``). Datos sintéticos."""

import itertools
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from rest_framework.test import APIClient

from core.models import Localidad, Municipio, Provincia
from VAT.models import Centro, InstitucionUbicacion

pytestmark = pytest.mark.django_db

ROOT = "/api/web/vat/institucion/ubicaciones/"
NATIVA = "/vat/institucion/ubicaciones/"
SUFIJO = "institucionubicacion"
_COUNTER = itertools.count()


def _client(*codes, sse=False, csrf=False):
    user = get_user_model().objects.create_user(f"iu{next(_COUNTER)}")
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


@pytest.fixture(name="ubicacion")
def ubicacion_fixture(centro):
    return InstitucionUbicacion.objects.create(
        centro=centro,
        localidad=centro.localidad,
        rol_ubicacion="sede_principal",
        domicilio="Calle 12 entre 60 y 61",
        es_principal=True,
        latitud=Decimal("-34.921000"),
        observaciones="Frente a la plaza",
    )


def test_access_follows_each_native_route_rule(ubicacion):
    rutas = {
        ROOT: "view",
        f"{ROOT}{ubicacion.pk}/": "view",
        f"{ROOT}nuevo/": "add",
        f"{ROOT}{ubicacion.pk}/editar/": "change",
        f"{ROOT}{ubicacion.pk}/eliminar/": "delete",
    }
    for url, accion in rutas.items():
        assert APIClient().get(url).status_code == 401
        for otra in {"view", "add", "change", "delete"} - {accion}:
            assert _client(f"{otra}_{SUFIJO}").get(url).status_code == 403
        assert _client(f"{accion}_{SUFIJO}").get(url).status_code == 200
    assert _client(f"view_{SUFIJO}").get(f"{ROOT}999999/").status_code == 404


def test_list_projects_the_native_rows_and_filters(ubicacion, centro):
    otra = InstitucionUbicacion.objects.create(
        centro=centro, localidad=centro.localidad, rol_ubicacion="anexo"
    )
    client = _client(f"view_{SUFIJO}", f"delete_{SUFIJO}")
    data = client.get(ROOT).json()
    assert data["permisos"] == {"editar": False, "eliminar": True}
    assert data["urls"] == {"list": NATIVA, "create": f"{NATIVA}nuevo/"}
    filas = {r["id"]: r for r in data["results"]}
    fila = filas[ubicacion.pk]
    assert (fila["centro"], fila["localidad"]) == ("CFP 401", "Tolosa")
    assert (fila["rol"], fila["es_principal"]) == ("Sede Principal", True)
    assert fila["domicilio"] == "Calle 12 entre 60 y 61"
    assert filas[otra.pk]["domicilio"] == "—"
    assert fila["delete_url"] == f"{NATIVA}{ubicacion.pk}/eliminar/"
    por_rol = client.get(ROOT, {"rol_ubicacion": "anexo"}).json()["results"]
    assert [r["id"] for r in por_rol] == [otra.pk]
    por_texto = client.get(ROOT, {"busqueda": "Calle 12"}).json()
    assert [r["id"] for r in por_texto["results"]] == [ubicacion.pk]
    assert por_texto["busqueda"] == "Calle 12"
    assert client.get(ROOT, {"page": 9}).status_code == 404


def test_list_truncates_the_domicilio_like_the_template(centro):
    larga = InstitucionUbicacion.objects.create(
        centro=centro,
        localidad=centro.localidad,
        rol_ubicacion="anexo",
        domicilio="x" * 60,
    )
    fila = _client(f"view_{SUFIJO}").get(ROOT).json()["results"][0]
    assert fila["id"] == larga.pk
    assert fila["domicilio"] == "x" * 39 + "…"


def test_detail_projects_the_native_context_with_localized_numbers(ubicacion):
    data = _client(f"view_{SUFIJO}").get(f"{ROOT}{ubicacion.pk}/").json()
    assert (data["centro"], data["rol"], data["localidad"]) == (
        "CFP 401",
        "Sede Principal",
        "Tolosa",
    )
    assert (data["latitud"], data["longitud"]) == ("-34,921000", "—")
    assert data["vigencia_hasta"] == "Vigente"
    assert data["observaciones"] == "Frente a la plaza"
    assert data["title"] == str(ubicacion)
    assert data["urls"]["update"] == f"{NATIVA}{ubicacion.pk}/editar/"
    assert data["messages"] == []


def test_form_projects_the_widgets_the_template_draws(ubicacion, centro):
    client = _client(f"change_{SUFIJO}", sse=True)
    otra = Localidad.objects.create(nombre="Gonnet", municipio=centro.municipio)
    data = client.get(f"{ROOT}{ubicacion.pk}/editar/").json()
    assert data["editing"] is True
    assert [f["name"] for f in data["fields"]] == [
        "centro",
        "departamento",
        "localidad",
        "rol_ubicacion",
        "domicilio",
        "es_principal",
        "observaciones",
    ]
    por_nombre = {f["name"]: f for f in data["fields"]}
    assert por_nombre["centro"]["id"] == "id_centro_ubicacion"
    assert por_nombre["departamento"]["value"] == str(centro.municipio_id)
    assert [c["label"] for c in por_nombre["departamento"]["choices"]][1:] == [
        "La Plata"
    ]
    # The localidad select draws only the chosen option; the others come by AJAX.
    assert por_nombre["localidad"]["value"] == str(centro.localidad_id)
    assert [c["value"] for c in por_nombre["localidad"]["choices"]] == [
        "",
        str(centro.localidad_id),
    ]
    assert str(otra.pk) not in [c["value"] for c in por_nombre["localidad"]["choices"]]
    assert data["urls"]["list"] == f"/vat/centros/{centro.pk}/"
    assert data["urls"]["municipios"] == "/vat/ajax/municipios-por-centro/"
    assert data["urls"]["localidades"] == "/ajax/load-localidades/"


def test_create_form_locks_the_centro_and_guards_the_centro_sent(centro):
    client = _client(f"add_{SUFIJO}", sse=True)
    libre = client.get(f"{ROOT}nuevo/").json()
    assert libre["editing"] is False
    assert libre["urls"]["list"] == NATIVA
    assert "disabled" not in libre["fields"][0]["attrs"]
    bloqueado = client.get(f"{ROOT}nuevo/", {"centro": centro.pk}).json()
    assert bloqueado["fields"][0]["attrs"]["disabled"] == "disabled"
    assert bloqueado["fields"][0]["value"] == str(centro.pk)
    assert client.get(f"{ROOT}nuevo/", {"centro": 999999}).status_code == 403
    assert client.get(f"{ROOT}nuevo/", {"centro": "x"}).status_code == 403
    sin_alcance = _client(f"add_{SUFIJO}")
    assert sin_alcance.get(f"{ROOT}nuevo/", {"centro": centro.pk}).status_code == 403
    assert sin_alcance.post(f"{ROOT}nuevo/", {"centro": centro.pk}).status_code == 403


def test_create_persists_queues_the_message_and_rejection_keeps_data(centro):
    client = _client(f"add_{SUFIJO}", f"view_{SUFIJO}", sse=True)
    rechazo = client.post(
        f"{ROOT}nuevo/", {"centro": centro.pk, "domicilio": "Calle 1"}
    )
    assert rechazo.status_code == 400
    assert any(f["errors"] for f in rechazo.json()["fields"])
    assert InstitucionUbicacion.objects.count() == 0
    respuesta = client.post(
        f"{ROOT}nuevo/",
        {
            "centro": centro.pk,
            "localidad": centro.localidad_id,
            "rol_ubicacion": "anexo",
            "domicilio": "Calle 1",
            "es_principal": "on",
        },
        format="multipart",
    )
    assert respuesta.status_code == 200
    assert respuesta.json() == {"ok": True, "redirect": NATIVA}
    nueva = InstitucionUbicacion.objects.get()
    assert (nueva.domicilio, nueva.es_principal, nueva.nombre_ubicacion) == (
        "Calle 1",
        True,
        "",
    )
    assert client.get(ROOT).json()["messages"] == [
        {"message": "Ubicación creada exitosamente.", "level": "success"}
    ]


def test_update_persists_and_rejection_keeps_the_stored_data(ubicacion, centro):
    client = _client(f"change_{SUFIJO}", f"view_{SUFIJO}", sse=True)
    url = f"{ROOT}{ubicacion.pk}/editar/"
    assert client.post(url, {"centro": ""}, format="multipart").status_code == 400
    ubicacion.refresh_from_db()
    assert ubicacion.domicilio == "Calle 12 entre 60 y 61"
    respuesta = client.post(
        url,
        {
            "centro": centro.pk,
            "localidad": centro.localidad_id,
            "rol_ubicacion": "anexo",
            "domicilio": "Calle 13",
        },
        format="multipart",
    )
    assert respuesta.status_code == 200
    assert respuesta.json() == {"ok": True, "redirect": f"/vat/centros/{centro.pk}/"}
    ubicacion.refresh_from_db()
    assert (ubicacion.domicilio, ubicacion.rol_ubicacion) == ("Calle 13", "anexo")
    assert client.get(ROOT).json()["messages"] == [
        {"message": "Ubicación actualizada exitosamente.", "level": "success"}
    ]


def test_delete_shows_the_summary_and_removes_through_the_native_view(ubicacion):
    client = _client(f"delete_{SUFIJO}", f"view_{SUFIJO}")
    url = f"{ROOT}{ubicacion.pk}/eliminar/"
    assert client.get(url).json() == {
        "rol": "Sede Principal",
        "localidad": "Tolosa",
        "centro": "CFP 401",
        "urls": {"detail": f"{NATIVA}{ubicacion.pk}/"},
    }
    assert InstitucionUbicacion.objects.count() == 1
    assert client.post(url).json() == {"ok": True, "redirect": NATIVA}
    assert InstitucionUbicacion.objects.count() == 0
    assert client.post(url).status_code == 404


def test_writes_require_csrf_and_the_write_permission(ubicacion, centro):
    todos = (f"add_{SUFIJO}", f"change_{SUFIJO}", f"delete_{SUFIJO}")
    sin_csrf = _client(*todos, csrf=True, sse=True)
    assert sin_csrf.post(f"{ROOT}nuevo/", {"centro": centro.pk}).status_code == 403
    assert sin_csrf.post(f"{ROOT}{ubicacion.pk}/eliminar/").status_code == 403
    lector = _client(f"view_{SUFIJO}", sse=True)
    assert lector.post(f"{ROOT}nuevo/", {"centro": centro.pk}).status_code == 403
    assert lector.post(f"{ROOT}{ubicacion.pk}/eliminar/").status_code == 403
    assert (
        lector.post(f"{ROOT}{ubicacion.pk}/editar/", {"centro": centro.pk}).status_code
        == 403
    )
    assert InstitucionUbicacion.objects.count() == 1
