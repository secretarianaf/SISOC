"""Issue #2789: listados y registros de solo lectura del admin de PAS."""

from datetime import date

from django.contrib import admin
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
import pytest

from core.models import Municipio, Provincia
from pas.models import (
    PasEstado,
    PasHistorialEstado,
    PasInvitacionDDJJ,
    PasPersona,
    PasSupervivenciaBatch,
    PasSupervivenciaRun,
)

pytestmark = pytest.mark.django_db


@pytest.fixture(name="base")
def base_fixture():
    provincia = Provincia.objects.create(nombre="Provincia admin PAS")
    return {
        "provincia": provincia,
        "municipio": Municipio.objects.create(
            nombre="Municipio admin PAS", provincia=provincia
        ),
        "estado": PasEstado.objects.create(nombre="Activo admin PAS"),
    }


def _persona(base, numero):
    return PasPersona.objects.create(
        id_persona=990000 + numero,
        apellidos="Admin",
        nombres=f"Persona {numero}",
        dni=31990000 + numero,
        **base,
    )


@pytest.mark.parametrize("modelo", [PasSupervivenciaRun, PasSupervivenciaBatch])
def test_corridas_y_lotes_son_de_solo_lectura(rf, superuser, modelo):
    request = rf.get("/admin/")
    request.user = superuser
    model_admin = admin.site._registry[modelo]  # pylint: disable=protected-access

    assert not model_admin.has_add_permission(request)
    assert not model_admin.has_change_permission(request)
    assert not model_admin.has_delete_permission(request)
    assert model_admin.has_view_permission(request)


def test_regenerar_token_sigue_funcionando_desde_el_listado(auth_client, base):
    persona = _persona(base, 1)

    respuesta = auth_client.post(
        reverse("admin:pas_paspersona_changelist"),
        {"action": "regenerar_token_ddjj", "_selected_action": [persona.pk]},
    )

    assert respuesta.status_code == 302
    assert PasInvitacionDDJJ.objects.filter(persona=persona).count() == 1


def _consultas(client, url):
    with CaptureQueriesContext(connection) as contexto:
        respuesta = client.get(url)
    assert respuesta.status_code == 200
    return len(contexto.captured_queries)


@pytest.mark.parametrize(
    "modelo", [PasPersona, PasHistorialEstado, PasSupervivenciaBatch]
)
def test_listados_sin_n_mas_1(
    auth_client, base, superuser, modelo, django_assert_max_num_queries
):
    url = reverse(
        f"admin:pas_{modelo._meta.model_name}_changelist"  # pylint: disable=protected-access
    )

    def _cargar(desde, periodo):
        run = PasSupervivenciaRun.objects.create(
            period=periodo, cutoff=periodo, requested_by=superuser
        )
        for numero in range(desde, desde + 5):
            persona = _persona(base, numero)
            PasHistorialEstado.objects.create(
                persona=persona,
                estado_anterior=base["estado"],
                estado_nuevo=base["estado"],
                usuario=superuser,
            )
            PasSupervivenciaBatch.objects.create(run=run, persona_ids=[persona.pk])

    _cargar(100, date(2026, 8, 1))
    with django_assert_max_num_queries(20):
        consultas_con_5 = _consultas(auth_client, url)
    _cargar(200, date(2026, 9, 1))

    assert _consultas(auth_client, url) == consultas_con_5


@pytest.mark.parametrize(
    "modelo", ["passupervivenciarun", "passupervivenciabatch", "paspersona"]
)
def test_busqueda_de_texto_no_rompe_el_listado(auth_client, modelo):
    url = reverse(f"admin:pas_{modelo}_changelist")

    assert auth_client.get(url, {"q": "abc 123"}).status_code == 200
