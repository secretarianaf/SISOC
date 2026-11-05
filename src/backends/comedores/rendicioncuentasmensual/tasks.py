"""Tareas Celery de rendiciones mensuales; corren en la cola ``comedores``."""

from celery import shared_task

from rendicioncuentasmensual import services_pdf_descarga


@shared_task(name=services_pdf_descarga.PDF_DESCARGA_TAREA)
def generar_pdf_descarga(solicitud_id, token):
    services_pdf_descarga.generar_pdf_descarga(solicitud_id, token)


@shared_task(name="rendicioncuentasmensual.tasks.purgar_pdfs_descarga")
def purgar_pdfs_descarga():
    return services_pdf_descarga.purgar_pdfs_descarga()
