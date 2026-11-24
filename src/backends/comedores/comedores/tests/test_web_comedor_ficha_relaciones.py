"""Nómina card, interventions and observations of the comedor ficha web API (CO07.01).

The blocks are projections of the native context. The creation modals post to the web APIs of
the native create views through the URLs the ficha publishes: these tests check the persisted
effect and that a rejected request leaves the data unchanged.
"""

from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from admisiones.models.admisiones import Admision
from catalogo_intervenciones.models import (
    TipoContacto,
    TipoDestinatario,
    TipoIntervencion,
)
from comedores.models import Comedor, Observacion
from intervenciones.models.intervenciones import Intervencion

pytestmark = pytest.mark.django_db
ROOT = "/api/web/comedores/comedores/"


@pytest.fixture(name="comedor_fixture", autouse=True)
def sin_dobles_del_conftest():
    """Same name as the folder's autouse double: the ficha runs the real services."""


@pytest.fixture(name="admin")
def admin_fixture():
    usuario = get_user_model().objects.create_superuser("admin_rel", password="x")
    profile = usuario.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    client = Client()
    client.force_login(usuario)
    return client


@pytest.fixture(name="comedor")
def comedor_fixture():
    return Comedor.objects.create(nombre="Comedor Norte")


def _ficha(client, comedor, **params):
    return client.get(f"{ROOT}{comedor.pk}/", params).json()


def test_nomina_card_without_admission(admin, comedor):
    nomina = _ficha(admin, comedor)["nomina"]

    assert nomina["ver"] is None
    assert nomina["importar"] is None
    assert nomina["pendiente"] is False
    assert nomina["cifras"] == {
        "asistentes": "0",
        "hombres": "0",
        "mujeres": "0",
        "menores": "0",
        "espera": "0",
        "bajas": "0",
    }


def test_nomina_card_with_admission_links_and_pending_notice(admin, comedor):
    admision = Admision.objects.create(comedor=comedor, activa=True)

    nomina = _ficha(admin, comedor)["nomina"]

    base = f"/comedores/{comedor.pk}/admision/{admision.pk}/nomina"
    assert nomina["ver"] == f"{base}/"
    assert nomina["importar"] == f"{base}/importar/"
    assert nomina["pendiente"] is True


def test_intervenciones_rows_pager_and_modal_data(admin, comedor):
    for dia in range(1, 13):
        Intervencion.objects.create(comedor=comedor, fecha=date(2026, 3, dia))

    primera = _ficha(admin, comedor)["intervenciones"]
    segunda = _ficha(admin, comedor, intervenciones_page=2)["intervenciones"]

    assert primera["encabezados"] == [
        "Fecha",
        "Intervención",
        "Sub intervención",
        "Doc. adjunta",
        "Destinatario",
        "Usuario creador",
        "Acciones",
    ]
    assert len(primera["filas"]) == 10 and len(segunda["filas"]) == 2
    fila = primera["filas"][0]
    assert fila[0] == {"texto": "12/03/2026"}
    assert fila[1] == {"texto": "-"}
    assert fila[3] == {"insignia": "bg-secondary", "texto": "No"}
    assert [a["label"] for a in fila[6]["acciones"]] == ["Ver", "Eliminar"]
    assert primera["resultados"] == 12
    assert primera["paginacion"]["param"] == "intervenciones_page"
    assert primera["paginacion"]["siguiente"] == 2
    assert segunda["paginacion"]["anterior"] == 1
    modal = primera["modal"]
    assert (
        modal["crear"]
        == f"/api/web/comedores/intervenciones/comedor/{comedor.pk}/crear/"
    )
    assert modal["next"] == f"/comedores/{comedor.pk}"
    assert modal["formulario"] == f"/comedores/intervencion/crear/{comedor.pk}"
    assert modal["tipo_intervencion"]["id"] == "id_tipo_intervencion"
    assert modal["documentacion"]["label"] == "Cargar Documentación"


def test_intervenciones_convenio_buttons_are_empty_without_followed_admissions(
    admin, comedor
):
    Admision.objects.create(comedor=comedor, activa=True)

    datos = _ficha(admin, comedor)["intervenciones"]

    # The native selector only lists admissions with an acompañamiento.
    assert datos["convenios"] == []
    assert datos["modal"]["next"] == f"/comedores/{comedor.pk}"


def test_observaciones_rows_and_pager(admin, comedor):
    for i in range(6):
        Observacion.objects.create(
            comedor=comedor, observador="Ana", observacion="x" * 100 + str(i)
        )

    datos = _ficha(admin, comedor)["observaciones"]

    assert datos["encabezados"] == ["Fecha", "Observador", "Observación", "Acciones"]
    assert len(datos["filas"]) == 5
    fila = datos["filas"][0]
    assert fila[1] == {"texto": "Ana"}
    assert len(fila[2]["texto"]) == 80 and fila[2]["texto"].endswith("…")
    assert fila[3]["acciones"][0]["label"] == "Ver"
    assert datos["paginacion"]["param"] == "observaciones_page"
    assert datos["modal"]["campo"]["placeholder"] == "Describa la observación"
    assert datos["modal"]["formulario"].endswith("/observacion/crear")


def test_intervention_modal_post_persists_and_a_rejection_changes_nothing(
    admin, comedor
):
    modal = _ficha(admin, comedor)["intervenciones"]["modal"]
    antes = Intervencion.objects.count()

    rechazo = admin.post(modal["crear"], {"next": modal["next"], "fecha": ""})

    assert rechazo.status_code == 400
    # The 400 body is the create form payload (values and errors) the React create page draws.
    assert rechazo.json()["fields"]["fecha"]["invalid"] is True
    assert Intervencion.objects.count() == antes
    tipo = TipoIntervencion.objects.create(nombre="Entrevista", programa="comedores")
    destinatario = TipoDestinatario.objects.create(nombre="Titular")
    contacto = TipoContacto.objects.create(nombre="Telefonico")
    respuesta = admin.post(
        modal["crear"],
        {
            "next": modal["next"],
            "fecha": "2026-03-05",
            "tipo_intervencion": str(tipo.pk),
            "destinatario": str(destinatario.pk),
            "forma_contacto": str(contacto.pk),
            "observaciones": "Visita",
        },
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["redirect"].startswith(f"/comedores/{comedor.pk}")
    creada = Intervencion.objects.get(comedor=comedor)
    assert creada.fecha.date() == date(2026, 3, 5) and creada.observaciones == "Visita"


def test_observation_modal_post_persists_and_a_rejection_changes_nothing(
    admin, comedor
):
    modal = _ficha(admin, comedor)["observaciones"]["modal"]

    rechazo = admin.post(modal["crear"], {"next": modal["next"], "observacion": ""})

    assert rechazo.status_code == 400
    assert rechazo.json()["errors"]["observacion"]
    assert not Observacion.objects.filter(comedor=comedor).exists()
    respuesta = admin.post(
        modal["crear"], {"next": modal["next"], "observacion": "Todo bien"}
    )
    assert respuesta.status_code == 200
    assert Observacion.objects.get(comedor=comedor).observacion == "Todo bien"
