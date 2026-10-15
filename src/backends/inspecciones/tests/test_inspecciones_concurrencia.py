"""Cierres y anulaciones simultáneos con transacciones reales (MySQL).

En SQLite ``select_for_update`` no bloquea filas: estos tests sólo tienen
sentido contra MySQL (marker ``mysql_compat``, como en CI).
"""

import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from django.core.exceptions import ValidationError
from django.db import close_old_connections, connection
from django.utils import timezone

from inspecciones.models import Acta, EventoInspeccion, Inspeccion, SecuenciaActa
from inspecciones.services.anulacion import anular_acta
from inspecciones.services.cierre import finalizar_inspeccion

HILOS = 8


def _cerrar_en_hilo(barrera, user, inspeccion_uuid, datos):
    close_old_connections()
    try:
        barrera.wait(timeout=30)
        return finalizar_inspeccion(user, inspeccion_uuid, datos)
    finally:
        close_old_connections()


def _en_paralelo(user, uuids, datos):
    barrera = Barrier(len(uuids))
    with ThreadPoolExecutor(max_workers=len(uuids)) as executor:
        futuros = [
            executor.submit(_cerrar_en_hilo, barrera, user, u, datos) for u in uuids
        ]
        return [f.result(timeout=60) for f in futuros]


@pytest.mark.mysql_compat
@pytest.mark.django_db(transaction=True)
def test_cierres_simultaneos_reciben_numeros_distintos_y_consecutivos(
    inspector_a, payload
):
    if connection.vendor != "mysql":
        pytest.skip("El bloqueo de filas requiere MySQL real.")
    uuids = [str(uuid.uuid4()) for _ in range(HILOS)]

    resultados = _en_paralelo(inspector_a, uuids, payload())

    anio = timezone.localdate().year
    numeros = sorted(r["numero"] for r in resultados)
    assert numeros == [f"ACTA-{anio}-{n:06d}" for n in range(1, HILOS + 1)]
    assert SecuenciaActa.objects.get(anio=anio).ultimo == HILOS
    assert Acta.objects.count() == HILOS


@pytest.mark.mysql_compat
@pytest.mark.django_db(transaction=True)
def test_cierres_simultaneos_del_mismo_uuid_devuelven_la_misma_acta(
    inspector_a, payload
):
    if connection.vendor != "mysql":
        pytest.skip("El bloqueo de filas requiere MySQL real.")
    mismo = str(uuid.uuid4())

    resultados = _en_paralelo(inspector_a, [mismo] * HILOS, payload())

    assert len({(r["numero"], r["cerrada_at"]) for r in resultados}) == 1
    assert Acta.objects.count() == 1
    assert Inspeccion.objects.filter(uuid=mismo).count() == 1
    assert SecuenciaActa.objects.get(anio=timezone.localdate().year).ultimo == 1


def _anular_en_hilo(barrera, acta, motivo, actor):
    close_old_connections()
    try:
        barrera.wait(timeout=30)
        try:
            anular_acta(acta, motivo, actor)
        except ValidationError:
            return False
        return True
    finally:
        close_old_connections()


@pytest.mark.mysql_compat
@pytest.mark.django_db(transaction=True)
def test_anulaciones_simultaneas_anulan_una_sola_vez(
    inspector_a, coordinacion, payload
):
    if connection.vendor != "mysql":
        pytest.skip("El bloqueo de filas requiere MySQL real.")
    numero = finalizar_inspeccion(inspector_a, str(uuid.uuid4()), payload())["numero"]
    acta = Acta.objects.get(numero=numero)
    barrera = Barrier(HILOS)

    with ThreadPoolExecutor(max_workers=HILOS) as executor:
        futuros = [
            executor.submit(
                _anular_en_hilo, barrera, acta, f"Motivo de anulación {n}", coordinacion
            )
            for n in range(HILOS)
        ]
        resultados = [f.result(timeout=60) for f in futuros]

    assert resultados.count(True) == 1
    acta.refresh_from_db()
    assert acta.estado == Acta.Estado.ANULADA
    assert acta.eventos.filter(accion=EventoInspeccion.Accion.ANULADA).count() == 1
