"""Web API (G1 v1) of the DataCalle case ficha (DC02.01, #2785).

``GET /api/web/dispositivos/datacalle/casos/<uuid>/`` projects
``EncuestaDetailView`` for React: ``view_encuesta`` (not
``view_relevamiento``), cases of operativos in the provincial scope, soft
deleted cases 404 and only what the native ficha shows (no raw ``respuestas``,
no case GPS, no ``grupo_id``). Compared with the native page itself.
"""

import datetime
import types

import pytest
from django.contrib.auth.models import Permission, User
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone

from config.urls_all import urlpatterns as monolith_patterns
from core.models import Provincia
from datacalle.models import Encuesta, Relevamiento
from datacalle.services import respuestas_legibles
from datacalle.web_preview import datacalle_preview_patterns
from users.models import ProfileTerritorialScope

API = "/api/web/dispositivos/datacalle/casos/"
NATIVE = "/datacalle/casos/"

pytestmark = pytest.mark.django_db


def _user(username, *codenames, provincia=None, **names):
    user = User.objects.create_user(username, **names)
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.es_usuario_provincial = provincia is not None
    profile.save()
    if provincia is not None:
        ProfileTerritorialScope.objects.create(profile=profile, provincia=provincia)
    user.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="datacalle", codename__in=codenames
        )
    )
    return User.objects.get(pk=user.pk)


def _login(user):
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture(name="geo")
def geo_fixture():
    return {
        "cba": Provincia.objects.create(nombre="Córdoba"),
        "salta": Provincia.objects.create(nombre="Salta"),
    }


def _relevamiento(provincia, nombre="Operativo invierno"):
    return Relevamiento.objects.create(
        denominacion=nombre,
        provincia=provincia,
        fase=Relevamiento.Fase.ESPACIO_PUBLICO,
        area_operativa="Plaza",
        fecha_inicio=datetime.date(2026, 9, 15),
        fecha_fin=datetime.date(2026, 9, 17),
    )


def _caso(relevamiento, **extra):
    datos = {"relevamiento": relevamiento, "estado": "completa"}
    datos.update(extra)
    return Encuesta.objects.create(**datos)


@pytest.fixture(name="lector")
def lector_fixture():
    return _login(_user("lector_casos", "view_encuesta"))


def test_case_ficha_projects_the_native_page(lector, geo):
    relevador = _user("rel", first_name="Ana", last_name="Campo")
    relevamiento = _relevamiento(geo["cba"])
    caso = _caso(
        relevamiento,
        codigo_entrevistado="AB12",
        relevador=relevador,
        origen="app",
        fecha_inicio=timezone.make_aware(datetime.datetime(2026, 9, 16, 10, 5)),
        variante="adolescente",
        respuestas={
            "encuestadorNombre": "Ana",
            "claveDesconocida": "valor crudo",
            "asentamientoOtros": "",
        },
        lat=-31.4,
        lon=-64.2,
        grupo_id="grupo-secreto",
    )
    native = lector.get(f"{NATIVE}{caso.pk}/")
    respuesta = lector.get(f"{API}{caso.pk}/")
    body = respuesta.json()

    assert native.status_code == respuesta.status_code == 200
    assert body["titulo"] == "Caso AB12"
    assert (body["estado"], body["estado_display"]) == ("completa", "Completa")
    assert body["origen_display"] == "App"
    assert body["relevador"] == "Ana Campo"
    assert body["fecha_inicio"] == "16/09/2026 10:05"
    assert body["variante_etiqueta"] == caso.variante_etiqueta
    assert body["es_formulario_menores"] is True
    assert body["sin_entrevista_por_franja"] is False
    paginas = [
        {
            "titulo": p["titulo"],
            "items": [
                {
                    "etiqueta": str(i["etiqueta"]),
                    "valor": i["valor"],
                    "historico": i["historico"],
                }
                for i in p["items"]
            ],
        }
        for p in respuestas_legibles(caso)
    ]
    assert body["respuestas"] == paginas
    items = [i for p in body["respuestas"] for i in p["items"]]
    assert {
        "etiqueta": "claveDesconocida",
        "valor": "valor crudo",
        "historico": False,
    } in items
    assert any(i["historico"] for i in items)
    assert body["breadcrumb"] == [
        {"text": "Relevamientos", "url": "/datacalle/relevamientos/"},
        {
            "text": "Operativo invierno",
            "url": f"/datacalle/relevamientos/{relevamiento.pk}/",
        },
        {"text": "AB12", "url": None},
    ]
    texto = respuesta.content.decode()
    for oculto in ("grupo-secreto", "-31.4", "encuestadorNombre", 'claveDesconocida":'):
        assert oculto not in texto.replace('"etiqueta":"claveDesconocida"', ""), oculto
    assert "Formulario de menores (14 a 17 años)" in native.content.decode()


def test_case_without_code_relevador_or_answers(lector, geo):
    caso = _caso(_relevamiento(geo["cba"]), estado="rechazada", origen="backoffice")
    body = lector.get(f"{API}{caso.pk}/").json()

    assert body["titulo"] == f"Caso {caso.pk}"
    assert body["breadcrumb"][-1] == {"text": str(caso.pk), "url": None}
    assert (body["estado"], body["origen_display"]) == ("rechazada", "Backoffice")
    assert (body["relevador"], body["fecha_inicio"]) == (None, "")
    assert body["respuestas"] == []


def test_case_observed_by_age_band(lector, geo):
    caso = _caso(
        _relevamiento(geo["cba"]),
        estado="rechazada",
        persona_entrevistada="r6a13_varon#1",
    )
    body = lector.get(f"{API}{caso.pk}/").json()

    assert body["sin_entrevista_por_franja"] is True
    assert body["persona_entrevistada_etiqueta"] == caso.persona_entrevistada_etiqueta
    assert body["persona_entrevistada_etiqueta"]
    assert (
        body["persona_entrevistada_etiqueta"]
        in lector.get(f"{NATIVE}{caso.pk}/").content.decode()
    )


def test_case_needs_view_encuesta_and_scope(geo):
    propio = _caso(_relevamiento(geo["cba"]))
    ajeno = _caso(_relevamiento(geo["salta"], "Ajeno"))
    borrado = _caso(_relevamiento(geo["cba"], "Con baja"))
    borrado.delete()
    solo_relevamiento = _login(_user("solo_rel", "view_relevamiento"))
    provincial = _login(_user("prov", "view_encuesta", provincia=geo["cba"]))

    for client, caso, esperado in (
        (solo_relevamiento, propio, 403),
        (provincial, propio, 200),
        (provincial, ajeno, 404),
        (provincial, borrado, 404),
    ):
        assert client.get(f"{API}{caso.pk}/").status_code == esperado
        assert client.get(f"{NATIVE}{caso.pk}/").status_code == esperado
    assert provincial.get(f"{API}123/").status_code == 404
    assert provincial.post(f"{API}{propio.pk}/").status_code == 405


def test_case_preview_entry_keeps_the_native_guards(tmp_path, geo):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(
        '<script src="/v2/sisoc/assets/app.js"></script>', encoding="utf-8"
    )
    module = types.ModuleType("datacalle_casos_preview_urls")
    module.urlpatterns = datacalle_preview_patterns(tmp_path) + list(monolith_patterns)
    caso = _caso(_relevamiento(geo["cba"]))
    ajeno = _caso(_relevamiento(geo["salta"], "Ajeno"))
    provincial = _login(_user("prov", "view_encuesta", provincia=geo["cba"]))
    sin = _login(_user("sin"))
    for client, url in (
        (provincial, f"{NATIVE}{caso.pk}/"),
        (provincial, f"{NATIVE}{ajeno.pk}/"),
        (sin, f"{NATIVE}{caso.pk}/"),
        (Client(), f"{NATIVE}{caso.pk}/"),
    ):
        native = client.get(url).status_code
        with override_settings(ROOT_URLCONF=module):
            preview = client.get(url)
        assert preview.status_code == native, url
    with override_settings(ROOT_URLCONF=module):
        assert (
            "/datacalle/react/assets/app.js"
            in provincial.get(f"{NATIVE}{caso.pk}/").content.decode()
        )


def test_case_url_in_the_operativo_ficha_points_to_the_native_route(geo):
    caso = _caso(_relevamiento(geo["cba"]))
    assert reverse("datacalle_casos_detalle", args=[caso.pk]) == f"{NATIVE}{caso.pk}/"
