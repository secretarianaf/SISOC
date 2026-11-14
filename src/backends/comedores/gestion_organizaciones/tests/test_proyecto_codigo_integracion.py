"""Corregir el código de un proyecto no rompe legajo, rendiciones ni PWA.

Las rendiciones se vinculan al proyecto por FK (``rendicion.proyecto``) o, en
datos anteriores, por el comedor (``comedor.proyecto`` o el texto
``comedor.codigo_de_proyecto``). Tras cambiar el código, todas las consultas
tienen que seguir encontrando lo mismo con el código nuevo y nada con el viejo.
"""

from datetime import date

import pytest

from comedores.models import Comedor
from gestion_organizaciones.services.legajo import datos_legajo
from gestion_organizaciones.services.proyectos import cambiar_codigo_proyecto
from organizaciones.models import ProyectoOrganizacion, Organizacion
from pwa.models import AccesoComedorPWA
from rendicioncuentasmensual.models import RendicionCuentaMensual
from rendicioncuentasmensual.services import (
    RendicionCuentaMensualService,
    RendicionesOrganizacionService,
)
from tests.test_pwa_comedores_api import (  # pylint: disable=unused-import
    _create_pwa_user,
    _grant_mobile_rendicion_permission,
    _token_client,
    comedores,
)

VIEJO = "AB-0l"
NUEVO = "AB-01"


def _rendicion(comedor, numero, **extra):
    return RendicionCuentaMensual.objects.create(
        comedor=comedor,
        mes=numero,
        anio=2026,
        convenio="CONV-1",
        numero_rendicion=numero,
        periodo_inicio=date(2026, numero, 1),
        periodo_fin=date(2026, numero, 28),
        estado=RendicionCuentaMensual.ESTADO_ELABORACION,
        **extra,
    )


@pytest.fixture
def escenario(comedores):
    """Proyecto con un comedor por FK, otro solo por texto y tres rendiciones."""
    comedor_fk, comedor_texto = comedores
    organizacion = Organizacion.objects.create(
        nombre="Org integración", sin_vencimiento=True
    )
    proyecto = ProyectoOrganizacion.objects.create(
        organizacion=organizacion, codigo=VIEJO
    )
    Comedor.objects.filter(pk=comedor_fk.pk).update(
        organizacion=organizacion, proyecto=proyecto, codigo_de_proyecto=VIEJO
    )
    Comedor.objects.filter(pk=comedor_texto.pk).update(
        organizacion=organizacion, codigo_de_proyecto=VIEJO
    )
    comedor_fk.refresh_from_db()
    comedor_texto.refresh_from_db()
    rendiciones = {
        "por_proyecto": _rendicion(comedor_fk, 1, proyecto=proyecto),
        "por_comedor_fk": _rendicion(comedor_fk, 2),
        "por_comedor_texto": _rendicion(comedor_texto, 3),
    }
    return organizacion, proyecto, comedor_fk, comedor_texto, rendiciones


def _ids(queryset):
    return set(queryset.values_list("pk", flat=True))


@pytest.mark.django_db
def test_rendiciones_de_la_organizacion_siguen_al_codigo_nuevo(escenario):
    organizacion, proyecto, _, _, rendiciones = escenario
    todas = {r.pk for r in rendiciones.values()}
    assert (
        _ids(RendicionesOrganizacionService.obtener_rendiciones(organizacion, VIEJO))
        == todas
    )

    cambiar_codigo_proyecto(proyecto=proyecto, codigo_nuevo=NUEVO)

    assert (
        _ids(RendicionesOrganizacionService.obtener_rendiciones(organizacion, NUEVO))
        == todas
    )
    assert not RendicionesOrganizacionService.obtener_rendiciones(
        organizacion, VIEJO
    ).exists()
    codigos = RendicionesOrganizacionService.obtener_proyectos(organizacion)
    assert NUEVO in codigos
    assert VIEJO not in codigos


@pytest.mark.django_db
def test_rendiciones_del_comedor_no_cambian(escenario):
    _, proyecto, comedor_fk, comedor_texto, _ = escenario
    # pylint: disable=protected-access
    antes = (
        _ids(RendicionCuentaMensualService._get_project_queryset(comedor_fk)),
        _ids(RendicionCuentaMensualService._get_project_queryset(comedor_texto)),
    )

    cambiar_codigo_proyecto(proyecto=proyecto, codigo_nuevo=NUEVO)
    comedor_fk.refresh_from_db()
    comedor_texto.refresh_from_db()

    despues = (
        _ids(RendicionCuentaMensualService._get_project_queryset(comedor_fk)),
        _ids(RendicionCuentaMensualService._get_project_queryset(comedor_texto)),
    )
    assert despues == antes
    assert all(antes)


@pytest.mark.django_db
def test_destinatarios_de_notificacion_de_la_rendicion_no_cambian(escenario):
    _, proyecto, _, _, rendiciones = escenario
    rendicion = rendiciones["por_proyecto"]
    # pylint: disable=protected-access
    antes = {
        c.pk
        for c in RendicionCuentaMensualService._obtener_comedores_destino_notificacion(
            rendicion
        )
    }

    cambiar_codigo_proyecto(proyecto=proyecto, codigo_nuevo=NUEVO)
    rendicion.refresh_from_db()

    despues = {
        c.pk
        for c in RendicionCuentaMensualService._obtener_comedores_destino_notificacion(
            rendicion
        )
    }
    assert despues == antes
    assert len(antes) == 2


@pytest.mark.django_db
def test_pwa_sigue_listando_las_rendiciones_del_comedor(escenario):
    _, proyecto, comedor_fk, comedor_texto, _ = escenario
    clientes = {}
    for comedor in (comedor_fk, comedor_texto):
        usuario = _create_pwa_user(
            comedor=comedor,
            role=AccesoComedorPWA.ROL_REPRESENTANTE,
            username=f"rep_codigo_{comedor.pk}",
        )
        _grant_mobile_rendicion_permission(usuario)
        clientes[comedor.pk] = _token_client(usuario)

    def _listado(comedor):
        respuesta = clientes[comedor.pk].get(
            f"/api/comedores/{comedor.pk}/rendiciones/"
        )
        assert respuesta.status_code == 200, respuesta.data
        return {fila["id"] for fila in respuesta.data["results"]}

    antes = {c.pk: _listado(c) for c in (comedor_fk, comedor_texto)}

    cambiar_codigo_proyecto(proyecto=proyecto, codigo_nuevo=NUEVO)

    despues = {c.pk: _listado(c) for c in (comedor_fk, comedor_texto)}
    assert despues == antes
    assert all(antes.values())


@pytest.mark.django_db
def test_legajo_de_la_organizacion_muestra_el_codigo_nuevo_con_sus_rendiciones(
    escenario,
):
    organizacion, proyecto, _, _, rendiciones = escenario

    cambiar_codigo_proyecto(proyecto=proyecto, codigo_nuevo=NUEVO)

    datos = datos_legajo(organizacion, {"proyecto": NUEVO})
    assert NUEVO in datos["codigos_rendiciones"]
    assert VIEJO not in datos["codigos_rendiciones"]
    assert {r.pk for r in datos["rendiciones_generales"]} == {
        r.pk for r in rendiciones.values()
    }
