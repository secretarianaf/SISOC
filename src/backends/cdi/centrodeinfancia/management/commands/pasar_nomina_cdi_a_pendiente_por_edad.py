from datetime import date

from django.core.management.base import BaseCommand, CommandError

from centrodeinfancia.services import pasar_nomina_a_pendiente_por_edad


class Command(BaseCommand):
    help = (
        "Pasa a Pendiente las fichas activas de la nómina CDI de niños y niñas "
        "que ya cumplieron 4 años (#2925). Pensado para correr una vez por día."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--fecha",
            help="Fecha de referencia AAAA-MM-DD (por defecto, hoy).",
        )

    def handle(self, *args, **options):
        hoy = None
        if options.get("fecha"):
            try:
                hoy = date.fromisoformat(options["fecha"])
            except ValueError as exc:
                raise CommandError("La fecha debe tener formato AAAA-MM-DD.") from exc
        actualizadas = pasar_nomina_a_pendiente_por_edad(hoy=hoy)
        self.stdout.write(f"Fichas pasadas a Pendiente por edad: {actualizadas}")
