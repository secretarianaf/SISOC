"""Issue #2789: operaciones de soporte y listados del admin de VPSL."""

from auditlog.models import LogEntry
from django.contrib import admin
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
import pytest

from core.admin_operaciones import ejecutar_operacion
from core.models import Provincia
from ver_para_ser_libre import admin as vpsl_admin
from ver_para_ser_libre.models import (
    EstadoEvaluacionVPSL,
    EstadoItinerario,
    HistorialEstadoVPSL,
    ItinerarioVPSL,
    JornadaVPSL,
)
from ver_para_ser_libre.services import workflow
from ver_para_ser_libre.tests.test_workflow import (
    crear_itinerario,
    crear_jornada,
    crear_sede,
)

pytestmark = pytest.mark.django_db


def _operacion(model, slug):
    model_admin = admin.site._registry[model]  # pylint: disable=protected-access
    return next(op for op in model_admin.operaciones if op.slug == slug)


def _ejecutar(model, slug, obj, usuario, motivo="Pedido de soporte"):
    return ejecutar_operacion(
        operacion=_operacion(model, slug),
        objetos=[obj],
        usuario=usuario,
        datos={"motivo": motivo},
    )


def _auditado(obj, slug):
    return LogEntry.objects.filter(
        object_pk=str(obj.pk), additional_data__operacion=slug
    ).exists()


@pytest.mark.parametrize(
    "slug, funcion, kwargs",
    [
        ("aprobar", "aprobar_itinerario", {"observacion": "Pedido de soporte"}),
        ("rechazar", "rechazar_itinerario", {"observacion": "Pedido de soporte"}),
        (
            "enviar_subsanacion",
            "enviar_itinerario_a_subsanacion",
            {"observacion": "Pedido de soporte"},
        ),
        ("cerrar", "cerrar_itinerario", {}),
    ],
)
def test_operaciones_de_itinerario_llaman_al_workflow(
    mocker, superuser, slug, funcion, kwargs
):
    itinerario = crear_itinerario()
    servicio = mocker.patch.object(vpsl_admin.workflow, funcion)

    ok, errores = _ejecutar(ItinerarioVPSL, slug, itinerario, superuser)

    assert ok == [itinerario] and errores == []
    servicio.assert_called_once_with(itinerario, usuario=superuser, **kwargs)
    assert _auditado(itinerario, slug)


@pytest.mark.parametrize(
    "slug, funcion",
    [
        ("habilitar", "habilitar_jornada"),
        ("cerrar_definitivamente", "cerrar_jornada_definitivamente"),
    ],
)
def test_operaciones_de_jornada_llaman_al_workflow(mocker, superuser, slug, funcion):
    jornada = crear_jornada()
    servicio = mocker.patch.object(vpsl_admin.workflow, funcion)

    ok, _ = _ejecutar(JornadaVPSL, slug, jornada, superuser)

    assert ok == [jornada]
    servicio.assert_called_once_with(jornada, usuario=superuser)
    assert _auditado(jornada, slug)


def test_transicion_invalida_es_error_y_no_audita(superuser):
    # Un borrador no se aprueba: la guarda del workflow corta la operación.
    itinerario = crear_itinerario()

    ok, errores = _ejecutar(ItinerarioVPSL, "aprobar", itinerario, superuser)

    assert not ok
    assert errores == [(itinerario, "El itinerario debe estar presentado o subsanado.")]
    itinerario.refresh_from_db()
    assert itinerario.estado == EstadoItinerario.BORRADOR
    assert not _auditado(itinerario, "aprobar")


def test_habilitar_jornada_sin_checklist_es_error(superuser):
    jornada = crear_jornada()

    ok, errores = _ejecutar(JornadaVPSL, "habilitar", jornada, superuser)

    assert not ok
    assert "checklist" in errores[0][1]


def test_rechazar_itinerario_por_url_del_admin(auth_client):
    itinerario = crear_itinerario()
    workflow.presentar_itinerario(itinerario)
    itinerario.carta_archivo_estado = EstadoEvaluacionVPSL.RECHAZADO
    itinerario.save(update_fields=["carta_archivo_estado"])
    url = reverse(
        "admin:ver_para_ser_libre_itinerariovpsl_operacion_rechazar",
        args=[itinerario.pk],
    )

    respuesta = auth_client.post(
        url, {"confirmar_operacion": "1", "motivo": "Carta firmada por otra persona"}
    )

    assert respuesta.status_code == 302
    itinerario.refresh_from_db()
    assert itinerario.estado == EstadoItinerario.RECHAZADO
    entrada = LogEntry.objects.get(
        object_pk=str(itinerario.pk), additional_data__operacion="rechazar"
    )
    assert entrada.changes_dict == {
        "estado": [EstadoItinerario.PRESENTADO, EstadoItinerario.RECHAZADO]
    }
    # El motivo también queda en el historial propio del flujo.
    assert HistorialEstadoVPSL.objects.filter(
        object_id=itinerario.pk,
        estado_nuevo=EstadoItinerario.RECHAZADO,
        observacion="Carta firmada por otra persona",
    ).exists()


def test_cambiar_estado_generico_no_se_expone():
    nombres = {
        op.ejecutar.__name__
        for model in (ItinerarioVPSL, JornadaVPSL)
        for op in admin.site._registry[
            model
        ].operaciones  # pylint: disable=protected-access
    }

    assert "cambiar_estado" not in nombres


def test_historiales_son_de_solo_lectura(rf, superuser):
    request = rf.get("/admin/")
    request.user = superuser
    model_admin = admin.site._registry[  # pylint: disable=protected-access
        HistorialEstadoVPSL
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


@pytest.mark.parametrize("modelo", [ItinerarioVPSL, JornadaVPSL])
def test_listados_sin_n_mas_1(auth_client, modelo, django_assert_max_num_queries):
    url = reverse(
        f"admin:ver_para_ser_libre_{modelo._meta.model_name}_changelist"  # pylint: disable=protected-access
    )
    sede = crear_sede()
    provincia = Provincia.objects.create(nombre="Mendoza")

    def _cargar(desde):
        for numero in range(desde, desde + 5):
            itinerario = crear_itinerario(
                codigo=f"VPSL-{numero}", provincia=provincia, sedes=[sede]
            )
            crear_jornada(itinerario=itinerario)

    _cargar(100)
    with django_assert_max_num_queries(20):
        consultas_con_5 = _consultas(auth_client, url)
    _cargar(200)

    assert _consultas(auth_client, url) == consultas_con_5


@pytest.mark.parametrize(
    "modelo",
    [
        "itinerariovpsl",
        "jornadavpsl",
        "historialestadovpsl",
        "historialchecklistsedevpsl",
    ],
)
def test_busqueda_de_texto_no_rompe_el_listado(auth_client, modelo):
    url = reverse(f"admin:ver_para_ser_libre_{modelo}_changelist")

    assert auth_client.get(url, {"q": "abc 123"}).status_code == 200


def test_detalles_con_operaciones_cargan(auth_client):
    jornada = crear_jornada()

    for nombre, obj in (
        ("itinerariovpsl", jornada.itinerario),
        ("jornadavpsl", jornada),
    ):
        url = reverse(f"admin:ver_para_ser_libre_{nombre}_change", args=[obj.pk])
        assert auth_client.get(url).status_code == 200
