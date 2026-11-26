"""Adaptadores mínimos entre Celery y los servicios de PAS."""

from celery import shared_task

from pas.services.formacion_service import cerrar_periodos_formacion
from pas.services.supervivencia_jobs import (
    process_batch,
    reconcile_jobs,
    schedule_monthly,
)


@shared_task
def schedule_month():
    schedule_monthly()


@shared_task
def reconcile():
    reconcile_jobs()


@shared_task(acks_late=True, reject_on_worker_lost=True)
def run_batch(batch_id):
    process_batch(batch_id)


@shared_task
def cerrar_periodo_formacion():
    """Cierra el ciclo de formación vencido y guarda el excedente a arrastrar."""

    return cerrar_periodos_formacion()
