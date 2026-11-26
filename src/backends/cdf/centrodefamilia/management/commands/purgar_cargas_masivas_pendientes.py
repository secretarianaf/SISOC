"""Elimina los lotes de carga masiva de preinscriptos pendientes y vencidos.

La pantalla de carga masiva ya lo hace cada vez que se abre el historial; este
comando permite programarlo además en el servidor.

Uso: python manage.py purgar_cargas_masivas_pendientes [--dias 90]
"""

from django.core.management.base import BaseCommand

from centrodefamilia.services.carga_masiva.lotes import (
    DIAS_RETENCION_PENDIENTES,
    purgar_lotes_pendientes_vencidos,
)


class Command(BaseCommand):
    help = (
        "Elimina los lotes de carga masiva de preinscriptos que siguen pendientes "
        "después del plazo de retención de datos de menores."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dias",
            type=int,
            default=DIAS_RETENCION_PENDIENTES,
            help="Antigüedad en días a partir de la cual se elimina un lote pendiente.",
        )

    def handle(self, *args, **options):
        eliminados = purgar_lotes_pendientes_vencidos(options["dias"])
        self.stdout.write(
            self.style.SUCCESS(f"Lotes pendientes eliminados: {eliminados}.")
        )
