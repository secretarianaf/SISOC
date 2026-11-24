"""V06.01: web API de identificadores históricos de institución (``/api/web/vat/institucion/identificadores/``). Datos sintéticos."""

import itertools

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from rest_framework.test import APIClient

from core.models import Localidad, Municipio, Provincia
from VAT.models import Centro, InstitucionIdentificadorHist

pytestmark = pytest.mark.django_db

ROOT = "/api/web/vat/institucion/identificadores/"
NATIVA = "/vat/institucion/identificadores/"
SUFIJO = "institucionidentificadorhist"
_COUNTER = itertools.count()


def _client(*codes, csrf=False):
    user = get_user_model().objects.create_user(f"ii{next(_COUNTER)}")
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


@pytest.fixture(name="identificador")
def identificador_fixture(centro):
    return InstitucionIdentificadorHist.objects.create(
        centro=centro,
        tipo_identificador="cue",
        valor_identificador="0601449",
        es_actual=True,
        motivo="Alta inicial",
    )


def test_access_follows_each_native_route_rule(identificador):
    rutas = {
        ROOT: "view",
        f"{ROOT}{identificador.pk}/": "view",
        f"{ROOT}nuevo/": "add",
        f"{ROOT}{identificador.pk}/editar/": "change",
        f"{ROOT}{identificador.pk}/eliminar/": "delete",
    }
    for url, accion in rutas.items():
        assert APIClient().get(url).status_code == 401
        for otra in {"view", "add", "change", "delete"} - {accion}:
            assert _client(f"{otra}_{SUFIJO}").get(url).status_code == 403
        assert _client(f"{accion}_{SUFIJO}").get(url).status_code == 200
    assert _client(f"view_{SUFIJO}").get(f"{ROOT}999999/").status_code == 404


def test_list_projects_the_native_rows_and_filters(identificador, centro):
    otro = InstitucionIdentificadorHist.objects.create(
        centro=centro,
        tipo_identificador="cuie",
        valor_identificador="ZZ-77",
        es_actual=False,
    )
    client = _client(f"view_{SUFIJO}", f"change_{SUFIJO}")
    data = client.get(ROOT).json()
    assert data["permisos"] == {"editar": True, "eliminar": False}
    assert data["urls"] == {"list": NATIVA, "create": f"{NATIVA}nuevo/"}
    filas = {r["id"]: r for r in data["results"]}
    fila = filas[identificador.pk]
    assert fila["centro"] == "CFP 401"
    assert (fila["valor"], fila["es_actual"]) == ("0601449", True)
    assert fila["rol"] == "—"
    assert filas[otro.pk]["es_actual"] is False
    assert fila["update_url"] == f"{NATIVA}{identificador.pk}/editar/"
    por_tipo = client.get(ROOT, {"tipo_identificador": "cuie"}).json()["results"]
    assert [r["id"] for r in por_tipo] == [otro.pk]
    por_texto = client.get(ROOT, {"busqueda": "0601"}).json()
    assert [r["id"] for r in por_texto["results"]] == [identificador.pk]
    assert por_texto["busqueda"] == "0601"
    assert client.get(ROOT, {"page": 9}).status_code == 404


def test_detail_projects_the_native_context(identificador):
    data = _client(f"view_{SUFIJO}").get(f"{ROOT}{identificador.pk}/").json()
    assert data["centro"] == "CFP 401"
    assert data["valor"] == "0601449"
    assert data["rol"] == "—"
    assert (data["vigencia_hasta"], data["motivo"]) == ("Vigente", "Alta inicial")
    assert data["title"] == str(identificador)
    assert data["urls"]["delete"] == f"{NATIVA}{identificador.pk}/eliminar/"
    assert data["messages"] == []


def test_form_projects_only_the_widgets_the_template_draws(identificador, centro):
    client = _client(f"change_{SUFIJO}", f"add_{SUFIJO}")
    data = client.get(f"{ROOT}{identificador.pk}/editar/").json()
    assert data["editing"] is True
    assert [f["name"] for f in data["fields"]] == [
        "centro",
        "tipo_identificador",
        "valor_identificador",
        "rol_institucional",
        "es_actual",
        "vigencia_hasta",
        "motivo",
    ]
    por_nombre = {f["name"]: f for f in data["fields"]}
    assert por_nombre["centro"]["value"] == str(centro.pk)
    assert por_nombre["vigencia_hasta"]["attrs"]["type"] == "date"
    nuevo = client.get(f"{ROOT}nuevo/", {"centro": centro.pk}).json()
    assert nuevo["editing"] is False
    assert nuevo["fields"][0]["value"] == str(centro.pk)
    assert "disabled" not in nuevo["fields"][0]["attrs"]


def test_create_persists_queues_the_message_and_rejection_keeps_data(centro):
    client = _client(f"add_{SUFIJO}", f"view_{SUFIJO}")
    rechazo = client.post(f"{ROOT}nuevo/", {"centro": centro.pk, "motivo": "x"})
    assert rechazo.status_code == 400
    assert any(f["errors"] for f in rechazo.json()["fields"])
    assert InstitucionIdentificadorHist.objects.count() == 0
    respuesta = client.post(
        f"{ROOT}nuevo/",
        {
            "centro": centro.pk,
            "tipo_identificador": "cue",
            "valor_identificador": "0601449",
            "es_actual": "on",
        },
        format="multipart",
    )
    assert respuesta.status_code == 200
    assert respuesta.json() == {"ok": True, "redirect": NATIVA}
    nuevo = InstitucionIdentificadorHist.objects.get()
    assert (nuevo.valor_identificador, nuevo.es_actual) == ("0601449", True)
    assert client.get(ROOT).json()["messages"] == [
        {"message": "Identificador creado exitosamente.", "level": "success"}
    ]


def test_update_persists_and_rejection_keeps_the_stored_data(identificador, centro):
    client = _client(f"change_{SUFIJO}")
    url = f"{ROOT}{identificador.pk}/editar/"
    assert client.post(url, {"centro": ""}, format="multipart").status_code == 400
    identificador.refresh_from_db()
    assert identificador.valor_identificador == "0601449"
    respuesta = client.post(
        url,
        {
            "centro": centro.pk,
            "tipo_identificador": "cue",
            "valor_identificador": "0601450",
        },
        format="multipart",
    )
    assert respuesta.status_code == 200
    identificador.refresh_from_db()
    assert identificador.valor_identificador == "0601450"
    assert identificador.es_actual is False


def test_delete_shows_the_summary_and_removes_through_the_native_view(identificador):
    client = _client(f"delete_{SUFIJO}", f"view_{SUFIJO}")
    url = f"{ROOT}{identificador.pk}/eliminar/"
    assert client.get(url).json() == {
        "valor": "0601449",
        "tipo": identificador.get_tipo_identificador_display(),
        "centro": "CFP 401",
        "urls": {"detail": f"{NATIVA}{identificador.pk}/"},
    }
    assert InstitucionIdentificadorHist.objects.count() == 1
    assert client.post(url).json() == {"ok": True, "redirect": NATIVA}
    assert InstitucionIdentificadorHist.objects.count() == 0
    assert client.post(url).status_code == 404


def test_writes_require_csrf_and_the_write_permission(identificador, centro):
    todos = (f"add_{SUFIJO}", f"change_{SUFIJO}", f"delete_{SUFIJO}")
    sin_csrf = _client(*todos, csrf=True)
    assert sin_csrf.post(f"{ROOT}nuevo/", {"centro": centro.pk}).status_code == 403
    assert sin_csrf.post(f"{ROOT}{identificador.pk}/eliminar/").status_code == 403
    lector = _client(f"view_{SUFIJO}")
    assert lector.post(f"{ROOT}nuevo/", {"centro": centro.pk}).status_code == 403
    assert lector.post(f"{ROOT}{identificador.pk}/eliminar/").status_code == 403
    assert (
        lector.post(
            f"{ROOT}{identificador.pk}/editar/", {"centro": centro.pk}
        ).status_code
        == 403
    )
    assert InstitucionIdentificadorHist.objects.count() == 1
