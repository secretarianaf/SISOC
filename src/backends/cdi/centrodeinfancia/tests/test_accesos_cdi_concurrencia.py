"""Invariantes de los responsables CDI bajo transacciones concurrentes reales."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from django.contrib.auth.models import User
from django.db import close_old_connections, connection, transaction

from centrodeinfancia.models import AccesoCDI, CentroDeInfancia
from centrodeinfancia.services_accesos_cdi import asignar_responsable


@pytest.mark.mysql_compat
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("responsable_inicial", [True, False])
def test_asignaciones_concurrentes_dejan_un_solo_responsable(responsable_inicial):
    if connection.vendor != "mysql":
        pytest.skip("La exclusión por bloqueo de filas requiere MySQL real.")
    centro = CentroDeInfancia.objects.create(nombre="CDI concurrente")
    accesos = [
        AccesoCDI.objects.create(
            centro=centro,
            user=User.objects.create_user(f"referente-concurrente-{numero}"),
            es_responsable=responsable_inicial and numero == 0,
        )
        for numero in range(3)
    ]
    primera_asignada = Event()
    segunda_iniciada = Event()
    permitir_commit = Event()

    def primera_asignacion():
        close_old_connections()
        try:
            with transaction.atomic():
                asignar_responsable(AccesoCDI.objects.get(pk=accesos[1].pk))
                primera_asignada.set()
                assert permitir_commit.wait(30), "No se liberó la primera transacción."
        finally:
            close_old_connections()

    def observar_segunda_operacion(execute, sql, params, many, context):
        # Antes del fix, la segunda asignación ya leyó al responsable antiguo y
        # espera al UPDATE. Con el fix, espera al bloqueo del CDI antes de leerlo.
        consulta = sql.upper()
        bloquea_centro = (
            "FOR UPDATE" in consulta
            and CentroDeInfancia._meta.db_table.upper() in consulta
        )
        actualiza_acceso = consulta.startswith("UPDATE") and (
            AccesoCDI._meta.db_table.upper() in consulta
        )
        if bloquea_centro or actualiza_acceso:
            segunda_iniciada.set()
        return execute(sql, params, many, context)

    def segunda_asignacion():
        close_old_connections()
        try:
            assert primera_asignada.wait(30), "No comenzó la primera asignación."
            with connection.execute_wrapper(observar_segunda_operacion):
                asignar_responsable(AccesoCDI.objects.get(pk=accesos[2].pk))
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        primera = executor.submit(primera_asignacion)
        segunda = executor.submit(segunda_asignacion)
        try:
            assert segunda_iniciada.wait(30), "No comenzó la segunda asignación."
        finally:
            permitir_commit.set()
        primera.result(timeout=30)
        segunda.result(timeout=30)

    responsables = AccesoCDI.objects.filter(centro=centro, es_responsable=True)
    assert list(responsables.values_list("pk", flat=True)) == [accesos[2].pk]
    assert AccesoCDI.objects.filter(centro=centro, activo=True).count() == 3
