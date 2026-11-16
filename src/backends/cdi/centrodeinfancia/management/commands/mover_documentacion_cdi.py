"""Moves the legacy CDI intervention documents out of the shared ``documentacion/`` folder.

Only ``IntervencionCentroInfancia`` rows are selected, so Comedores files in the
same folder are never read or touched. Per row: copy to the private
``cdi/documentacion/`` prefix, verify the size, update the stored name and only
then delete the old file. The destination name is deterministic (it carries the
row pk), so an interrupted run resumes without leaving duplicate copies.
Dry-run by default; ``--aplicar`` executes.
"""

import posixpath

from django.apps import apps
from django.core.files.base import File
from django.core.management.base import BaseCommand
from django.db import DataError, transaction

from centrodeinfancia.models import IntervencionCentroInfancia
from centrodeinfancia.models_cdi_relaciones import PREFIJO_DOCUMENTACION_CDI

ORIGEN = "documentacion/"


def _destino(pk, nombre):
    """Deterministic name that always fits the FileField ``max_length``."""
    maximo = IntervencionCentroInfancia._meta.get_field("documentacion").max_length
    raiz, extension = posixpath.splitext(posixpath.basename(nombre))
    extension = extension[:10]
    reservado = f"{PREFIJO_DOCUMENTACION_CDI}{pk}_"
    espacio = max(maximo - len(reservado) - len(extension), 1)
    return f"{reservado}{raiz[:espacio]}{extension}"


class Command(BaseCommand):
    help = (
        "Mueve los archivos de intervenciones CDI de documentacion/ a "
        "cdi/documentacion/. Sin --aplicar solo informa (dry-run)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--aplicar",
            action="store_true",
            help="Ejecuta el movimiento. Por defecto es dry-run.",
        )

    def handle(self, *args, **options):
        aplicar = options["aplicar"]
        self.stdout.write("Modo: " + ("APLICAR" if aplicar else "dry-run"))
        conteo = {"movidos": 0, "faltantes": 0, "conflictos": 0, "omitidos": 0}

        filas = IntervencionCentroInfancia.all_objects.filter(
            documentacion__startswith=ORIGEN
        ).order_by("pk")
        for fila in filas.iterator():
            resultado = self._procesar(fila, aplicar)
            conteo[resultado] += 1

        self.stdout.write(
            "Resumen: "
            f"movidos={conteo['movidos']} faltantes={conteo['faltantes']} "
            f"conflictos={conteo['conflictos']} omitidos={conteo['omitidos']}"
        )
        if not aplicar:
            self.stdout.write("Dry-run: no se modifico nada. Usar --aplicar.")

    def _diagnosticar(self, fila, almacen, destino):
        """Return the skip category for a row that cannot be moved, else None."""
        origen = fila.documentacion.name
        if ".." in origen.split("/"):
            self.stderr.write(f"OMITIDO pk={fila.pk}: nombre no seguro {origen!r}")
            return "omitidos"
        if not almacen.exists(origen):
            self.stderr.write(f"FALTANTE pk={fila.pk}: no existe {origen}")
            return "faltantes"
        if almacen.exists(destino) and almacen.size(destino) != almacen.size(origen):
            self.stderr.write(
                f"CONFLICTO pk={fila.pk}: {destino} existe con otro tamano"
            )
            return "conflictos"
        return None

    def _procesar(self, fila, aplicar):
        origen = fila.documentacion.name
        almacen = fila.documentacion.storage
        destino = _destino(fila.pk, origen)
        omitido = self._diagnosticar(fila, almacen, destino)
        if omitido:
            return omitido
        tamano = almacen.size(origen)
        if not aplicar:
            self.stdout.write(f"MOVER pk={fila.pk}: {origen} -> {destino}")
            return "movidos"

        if not almacen.exists(destino):
            with almacen.open(origen, "rb") as archivo:
                guardado = almacen.save(destino, File(archivo))
            if guardado != destino or almacen.size(destino) != tamano:
                self.stderr.write(f"CONFLICTO pk={fila.pk}: copia no verificada")
                if guardado != destino:
                    almacen.delete(guardado)
                return "conflictos"
        try:
            actualizadas = self._actualizar(fila.pk, origen, destino)
        except DataError as exc:
            almacen.delete(destino)
            self.stderr.write(f"CONFLICTO pk={fila.pk}: no se pudo actualizar ({exc})")
            return "conflictos"
        if actualizadas:
            self._borrar_origen_sin_uso(almacen, origen)
        self.stdout.write(f"MOVIDO pk={fila.pk}: {origen} -> {destino}")
        return "movidos"

    @staticmethod
    def _actualizar(pk, origen, destino):
        with transaction.atomic():
            return IntervencionCentroInfancia.all_objects.filter(
                pk=pk, documentacion=origen
            ).update(documentacion=destino)

    @staticmethod
    def _otra_fila_usa(origen):
        # Another CDI row, or a Comedores intervention (when that app is
        # installed), may still point to the same old file; keep it then.
        if IntervencionCentroInfancia.all_objects.filter(documentacion=origen).exists():
            return True
        try:
            comedores = apps.get_model("intervenciones", "Intervencion")
        except LookupError:
            return False
        return comedores.all_objects.filter(documentacion=origen).exists()

    def _borrar_origen_sin_uso(self, almacen, origen):
        if not self._otra_fila_usa(origen):
            almacen.delete(origen)
