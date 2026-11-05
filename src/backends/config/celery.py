"""Aplicación Celery compartida por PAS (cola ``pas``) y comedores (``comedores``)."""

import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
app = Celery("sisoc")
app.config_from_object("django.conf:settings", namespace="CELERY")

# Cada imagen trae solo su backend: se descubren las tareas de las apps
# instaladas en el settings con el que arranca el proceso.
TASK_PACKAGES = ("pas", "rendicioncuentasmensual")


def _task_packages():
    from django.apps import apps  # pylint: disable=import-outside-toplevel

    return [package for package in TASK_PACKAGES if apps.is_installed(package)]


app.autodiscover_tasks(_task_packages)
# Beat corre con la imagen de PAS: las tareas de otros backends se envían por
# nombre a su cola, sin importarlas.
app.conf.beat_schedule = {
    "pas-month-end": {
        "task": "pas.tasks.schedule_month",
        "schedule": crontab(minute=0, hour=2, day_of_month="28-31"),
        "options": {"expires": 3600},
    },
    "pas-reconcile": {
        "task": "pas.tasks.reconcile",
        "schedule": 60.0,
        "options": {"expires": 60},
    },
    "rendiciones-purgar-pdfs-descarga": {
        "task": "rendicioncuentasmensual.tasks.purgar_pdfs_descarga",
        "schedule": crontab(minute=30, hour=3),
        "options": {"queue": "comedores", "expires": 3600},
    },
}
