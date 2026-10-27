"""Chequea las URLs sin parámetros de SISOC; el resultado se ve en ``/health/urls/``."""

import logging
import time
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from healthcheck import services

logger = logging.getLogger("django")


def _horarios(valor):
    try:
        return [datetime.strptime(h.strip(), "%H:%M").time() for h in valor.split(",")]
    except ValueError as exc:
        raise CommandError(
            f"--horarios inválido ({valor!r}): usar HH:MM separados por coma."
        ) from exc


class Command(BaseCommand):
    help = (
        "Hace un GET a cada URL sin parámetros (salvo admin, logout, borrados y "
        "exportaciones) y guarda los códigos de respuesta para /health/urls/."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--host",
            help="Header Host de los GET; por defecto, el primero de ALLOWED_HOSTS.",
        )
        parser.add_argument(
            "--horarios",
            help=(
                "Queda corriendo y chequea en esos horarios, p. ej. "
                "'06:00,12:00,18:00'. Sin esto, chequea una vez y termina."
            ),
        )

    def handle(self, *args, **options):
        if not options["horarios"]:
            try:
                resultado = services.ejecutar(options["host"])
            except ValueError as exc:
                raise CommandError(str(exc)) from exc
            self.stdout.write(str(resultado["resumen"]))
            return
        horarios = _horarios(options["horarios"])
        while True:
            self.ciclo(horarios, options["host"])

    def ciclo(self, horarios, host):
        """Espera el próximo horario y chequea; un fallo no corta el worker."""
        proximo = services.proximo_horario(timezone.localtime(), horarios)
        logger.info("health/urls: próximo chequeo %s", proximo.isoformat())
        time.sleep(max((proximo - timezone.localtime()).total_seconds(), 0))
        try:
            resultado = services.ejecutar(host)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.exception("health/urls: falló el chequeo")
            services.guardar_error(str(exc))
            return
        logger.info("health/urls: %s", resultado["resumen"])
