"""Issue #2789: operación de soporte del admin de CDF (baja de participante)."""

from datetime import date

from auditlog.models import LogEntry
from django.contrib import admin
from django.contrib.auth.models import Group
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
import pytest

from centrodefamilia import admin as cdf_admin
from centrodefamilia.models import (
    Actividad,
    ActividadCentro,
    Categoria,
    Centro,
    ParticipanteActividad,
    ParticipanteActividadHistorial,
)
from ciudadanos.models import Ciudadano
from core.admin_operaciones import ejecutar_operacion
from core.constants import UserGroups
from core.models import Provincia

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _grupo_cdf_referente():
    Group.objects.get_or_create(name=UserGroups.CDF_REFERENTE_CENTRO)


@pytest.fixture(name="actividad_centro")
def actividad_centro_fixture():
    centro = Centro.objects.create(
        nombre="CDF Admin",
        provincia=Provincia.objects.create(nombre="Salta"),
        tipo="faro",
        codigo="CDF-ADMIN",
        domicilio_actividad="Calle 1",
        telefono="123",
        celular="456",
        correo="centro@test.com",
        nombre_referente="Ref",
        apellido_referente="Ente",
        telefono_referente="789",
        correo_referente="ref@test.com",
    )
    actividad = Actividad.objects.create(
        nombre="Fútbol", categoria=Categoria.objects.create(nombre="Deportes")
    )
    return ActividadCentro.objects.create(
        centro=centro,
        actividad=actividad,
        cantidad_personas=1,
        horariosdesde="10:00",
    )


def _participante(actividad_centro, documento, estado="inscrito"):
    ciudadano = Ciudadano.objects.create(
        apellido=f"Ape{documento}",
        nombre=f"Nom{documento}",
        fecha_nacimiento=date(2000, 1, 1),
        documento=documento,
    )
    return ParticipanteActividad.objects.create(
        actividad_centro=actividad_centro, ciudadano=ciudadano, estado=estado
    )


def _ejecutar(participante, usuario, motivo="Pedido del centro"):
    model_admin = admin.site._registry[  # pylint: disable=protected-access
        ParticipanteActividad
    ]
    operacion = next(op for op in model_admin.operaciones if op.slug == "dar_de_baja")
    return ejecutar_operacion(
        operacion=operacion,
        objetos=[participante],
        usuario=usuario,
        datos={"motivo": motivo},
    )


def _auditado(obj):
    return LogEntry.objects.filter(
        object_pk=str(obj.pk), additional_data__operacion="dar_de_baja"
    ).exists()


def test_dar_de_baja_llama_al_service(mocker, actividad_centro, superuser):
    participante = _participante(actividad_centro, 60000001)
    servicio = mocker.patch.object(
        cdf_admin.ParticipanteService, "dar_de_baja", return_value=participante
    )

    ok, _ = _ejecutar(participante, superuser)

    assert ok == [participante]
    servicio.assert_called_once_with(participante.pk, superuser)
    assert _auditado(participante)


def test_dar_de_baja_promueve_la_lista_de_espera(actividad_centro, superuser):
    inscripto = _participante(actividad_centro, 60000002)
    en_espera = _participante(actividad_centro, 60000003, estado="lista_espera")

    ok, errores = _ejecutar(inscripto, superuser)

    assert ok == [inscripto] and errores == []
    inscripto.refresh_from_db()
    en_espera.refresh_from_db()
    assert inscripto.estado == "dado_baja"
    assert en_espera.estado == "inscrito"
    assert ParticipanteActividadHistorial.objects.filter(
        participante=inscripto, estado_nuevo="dado_baja", usuario=superuser
    ).exists()


def test_baja_repetida_es_error_y_no_se_audita(mocker, actividad_centro, superuser):
    participante = _participante(actividad_centro, 60000004, estado="dado_baja")
    servicio = mocker.patch.object(cdf_admin.ParticipanteService, "dar_de_baja")

    ok, errores = _ejecutar(participante, superuser)

    assert not ok
    assert errores == [(participante, "El participante ya está dado de baja.")]
    servicio.assert_not_called()
    assert not _auditado(participante)


def test_dar_de_baja_por_url_del_admin(auth_client, actividad_centro):
    participante = _participante(actividad_centro, 60000005)
    url = reverse(
        "admin:centrodefamilia_participanteactividad_operacion_dar_de_baja",
        args=[participante.pk],
    )

    respuesta = auth_client.post(
        url, {"confirmar_operacion": "1", "motivo": "Se mudó de ciudad"}
    )

    assert respuesta.status_code == 302
    participante.refresh_from_db()
    assert participante.estado == "dado_baja"
    entrada = LogEntry.objects.get(
        object_pk=str(participante.pk), additional_data__operacion="dar_de_baja"
    )
    assert entrada.changes_dict == {"estado": ["inscrito", "dado_baja"]}
    assert entrada.additional_data["motivo"] == "Se mudó de ciudad"


def test_historial_es_de_solo_lectura(rf, superuser):
    request = rf.get("/admin/")
    request.user = superuser
    model_admin = admin.site._registry[  # pylint: disable=protected-access
        ParticipanteActividadHistorial
    ]

    assert not model_admin.has_add_permission(request)
    assert not model_admin.has_change_permission(request)
    assert not model_admin.has_delete_permission(request)
    assert model_admin.has_view_permission(request)


def _consultas(client, url):
    with CaptureQueriesContext(connection) as contexto:
        respuesta = client.get(url)
    assert respuesta.status_code == 200
    return len(contexto.captured_queries)


@pytest.mark.parametrize(
    "modelo", [ParticipanteActividad, ParticipanteActividadHistorial]
)
def test_listados_sin_n_mas_1(
    auth_client, actividad_centro, superuser, modelo, django_assert_max_num_queries
):
    url = reverse(
        f"admin:centrodefamilia_{modelo._meta.model_name}_changelist"  # pylint: disable=protected-access
    )

    def _cargar(desde, cantidad):
        for documento in range(desde, desde + cantidad):
            participante = _participante(actividad_centro, documento)
            ParticipanteActividadHistorial.objects.create(
                participante=participante, estado_nuevo="inscrito", usuario=superuser
            )

    _cargar(61000000, 5)
    with django_assert_max_num_queries(10):
        consultas_con_5 = _consultas(auth_client, url)
    _cargar(61000100, 5)

    assert _consultas(auth_client, url) == consultas_con_5
