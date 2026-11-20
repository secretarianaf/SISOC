"""DC02.03 (#2785): the field app consumer does not notice the web migration.

The token API ``api/datacalle/`` stays untouched. What the web API does to an
operativo (create, edit, close, delete) must reach the app exactly as the
native HTML route does: ``mis_relevamientos`` membership, state, ``updated_at``
for ``?desde=`` and the 409 a closed operativo gives to a case upload.
"""

import datetime
import uuid

import pytest
from django.contrib.auth.models import Permission, User
from django.test import Client
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from core.models import Provincia
from datacalle.models import Relevamiento
from users.models import RelevadorCalleProvincia

WEB = "/api/web/dispositivos/datacalle/relevamientos/"
NATIVE = "/datacalle/relevamientos/"

pytestmark = pytest.mark.django_db


def _gestor():
    user = User.objects.create_user("gestor_campo")
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    user.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="datacalle",
            codename__in=[
                "view_relevamiento",
                "add_relevamiento",
                "change_relevamiento",
                "delete_relevamiento",
            ],
        )
    )
    client = Client()
    client.force_login(User.objects.get(pk=user.pk))
    return client


def _entrevistador(provincia, username):
    user = User.objects.create_user(username)
    user.profile.es_relevador_calle = True
    user.profile.datacalle_rol = "entrevistador"
    user.profile.save()
    RelevadorCalleProvincia.objects.create(profile=user.profile, provincia=provincia)
    return user


def _app(user):
    token, _ = Token.objects.get_or_create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client


def _app_rows(user, query=""):
    data = _app(user).get(reverse("api-datacalle-relevamientos-list") + query).json()
    return data["results"] if isinstance(data, dict) else data


def _payload(provincia, team, nombre):
    return {
        "denominacion": nombre,
        "provincia": provincia.id,
        "fase": Relevamiento.Fase.ESPACIO_PUBLICO,
        "area_operativa": "Plaza",
        "fecha_inicio": "2026-09-15",
        "fecha_fin": "2026-09-19",
        "equipo": [u.id for u in team],
    }


@pytest.fixture(name="escenario")
def escenario_fixture():
    provincia = Provincia.objects.create(nombre="Córdoba")
    return {
        "provincia": provincia,
        "ana": _entrevistador(provincia, "ana_campo"),
        "beto": _entrevistador(provincia, "beto_campo"),
        "gestor": _gestor(),
    }


def _shape(row):
    """What the app reads of a task, without per-record identity."""
    clean = {k: v for k, v in row.items() if k not in ("id", "actualizado_en")}
    clean["equipo"] = sorted(m["id"] for m in row["equipo"])
    return clean


def test_created_operativo_reaches_the_app_like_the_native_one(escenario):
    gestor, ana = escenario["gestor"], escenario["ana"]
    datos = _payload(escenario["provincia"], [ana], "Por API web")

    assert gestor.post(WEB + "crear/", datos).status_code == 201
    assert (
        gestor.post(
            NATIVE + "crear/", {**datos, "denominacion": "Por HTML"}
        ).status_code
        == 302
    )

    filas = {f["denominacion"]: f for f in _app_rows(ana)}
    assert set(filas) == {"Por API web", "Por HTML"}
    web, html = filas["Por API web"], filas["Por HTML"]
    assert _shape({**web, "denominacion": ""}) == _shape({**html, "denominacion": ""})
    assert web["estado"] == "planificado"
    assert _app_rows(escenario["beto"]) == []


def test_closing_from_the_web_api_is_what_the_app_sees_after_the_native_close(
    escenario,
):
    gestor, ana = escenario["gestor"], escenario["ana"]
    por_web = Relevamiento.objects.create(
        denominacion="Cierre web",
        provincia=escenario["provincia"],
        fase=Relevamiento.Fase.ESPACIO_PUBLICO,
        area_operativa="Plaza",
        fecha_inicio=datetime.date(2026, 9, 15),
        fecha_fin=datetime.date(2026, 9, 17),
    )
    por_html = Relevamiento.objects.create(
        denominacion="Cierre html",
        provincia=escenario["provincia"],
        fase=Relevamiento.Fase.ESPACIO_PUBLICO,
        area_operativa="Plaza",
        fecha_inicio=datetime.date(2026, 9, 15),
        fecha_fin=datetime.date(2026, 9, 17),
    )
    por_web.equipo.add(ana)
    por_html.equipo.add(ana)
    antes = {r["id"]: r["actualizado_en"] for r in _app_rows(ana)}

    assert gestor.post(f"{WEB}{por_web.pk}/cerrar/").status_code == 200
    assert gestor.post(f"{NATIVE}{por_html.pk}/cerrar/").status_code == 302

    filas = {r["denominacion"]: r for r in _app_rows(ana)}
    assert (
        filas["Cierre web"]["estado"] == filas["Cierre html"]["estado"] == "finalizado"
    )
    assert filas["Cierre web"]["actualizado_en"] > antes[str(por_web.pk)]
    assert {r["denominacion"] for r in _app_rows(ana, "?desde=2000-01-01")} == {
        "Cierre web",
        "Cierre html",
    }
    caso = {
        "relevamiento_id": str(por_web.pk),
        "variante": "completo",
        "estado": "completa",
        "fecha_inicio": "2026-09-16T00:40:00Z",
        "fecha_hora_fin": "2026-09-16T00:52:30Z",
        "respuestas": {"personasObservadas": 1},
    }
    rechazo = _app(ana).put(
        f"/api/datacalle/encuestas/{uuid.uuid4()}/", caso, format="json"
    )
    assert rechazo.status_code == 409
    assert (rechazo.json()["codigo"], rechazo.json()["reintentable"]) == (
        "relevamiento_cerrado",
        False,
    )


def test_deleting_from_the_web_api_removes_the_task_from_the_app(escenario):
    gestor, ana = escenario["gestor"], escenario["ana"]
    relevamiento = Relevamiento.objects.create(
        denominacion="Baja",
        provincia=escenario["provincia"],
        fase=Relevamiento.Fase.ESPACIO_PUBLICO,
        area_operativa="Plaza",
        fecha_inicio=datetime.date(2026, 9, 15),
        fecha_fin=datetime.date(2026, 9, 17),
    )
    relevamiento.equipo.add(ana)
    assert len(_app_rows(ana)) == 1

    assert gestor.post(f"{WEB}{relevamiento.pk}/eliminar/").status_code == 200

    assert _app_rows(ana) == []
    assert Relevamiento.objects.filter(pk=relevamiento.pk).count() == 0


def test_the_token_close_still_belongs_to_the_coordinator(escenario):
    relevamiento = Relevamiento.objects.create(
        denominacion="Solo coordinador",
        provincia=escenario["provincia"],
        fase=Relevamiento.Fase.ESPACIO_PUBLICO,
        area_operativa="Plaza",
        fecha_inicio=datetime.date(2026, 9, 15),
        fecha_fin=datetime.date(2026, 9, 17),
    )
    relevamiento.equipo.add(escenario["ana"])

    rechazo = _app(escenario["ana"]).post(
        f"/api/datacalle/relevamientos/{relevamiento.pk}/cerrar/",
        {"lat": -31.4, "lon": -64.2},
        format="json",
    )

    assert rechazo.status_code == 403
    assert rechazo.json()["codigo"] == "cierre_no_autorizado"
    assert Relevamiento.objects.get(pk=relevamiento.pk).estado != "finalizado"
