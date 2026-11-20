"""Moves the legacy CDI intervention documents out of the shared ``documentacion/`` folder.

Only ``IntervencionCentroInfancia`` rows are selected, so Comedores files in the
same folder are never read or touched. Per row: copy to the private
``cdi/documentacion/`` prefix, verify size and SHA-256, update the stored name and
only then delete the old file. The destination name is deterministic (it carries
the row pk), so an interrupted run resumes without leaving duplicate copies. A
reconciliation pass also removes the old copy of rows that were updated but whose
old file was never deleted. The old file is deleted only when its consumers can be
checked (the Comedores app must be installed) and none uses it.
Dry-run by default; ``--aplicar`` executes.
"""

import hashlib
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


def _sha256(almacen, nombre):
    """Streaming SHA-256 so large files are never loaded in memory."""
    resumen = hashlib.sha256()
    with almacen.open(nombre, "rb") as archivo:
        for bloque in iter(lambda: archivo.read(1024 * 1024), b""):
            resumen.update(bloque)
    return resumen.hexdigest()


def _origen_legado(pk, destino):
    """Legacy name recovered from ``cdi/documentacion/<pk>_<nombre>``, else None."""
    reservado = f"{pk}_"
    base = posixpath.basename(destino)
    if not destino.startswith(PREFIJO_DOCUMENTACION_CDI):
        return None
    if not base.startswith(reservado) or base == reservado:
        return None
    return f"{ORIGEN}{base[len(reservado):]}"


class Command(BaseCommand):
    help = (
        "Mueve los archivos de intervenciones CDI de documentacion/ a "
        "cdi/documentacion/. Sin --aplicar solo informa (dry-run). Debe correr "
        "donde esten instaladas todas las apps (migrator / settings_all) para "
        "poder borrar los archivos viejos."
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pendiente = False

    def add_arguments(self, parser):
        parser.add_argument(
            "--aplicar",
            action="store_true",
            help="Ejecuta el movimiento. Por defecto es dry-run.",
        )

    def handle(self, *args, **options):
        aplicar = options["aplicar"]
        self.stdout.write("Modo: " + ("APLICAR" if aplicar else "dry-run"))
        conteo = dict.fromkeys(
            (
                "movidos",
                "faltantes",
                "conflictos",
                "omitidos",
                "limpiados",
                "pendientes",
            ),
            0,
        )

        # Reconcile first: rows already moved whose old copy was left behind.
        ya_movidas = IntervencionCentroInfancia.all_objects.filter(
            documentacion__startswith=PREFIJO_DOCUMENTACION_CDI
        ).order_by("pk")
        for fila in ya_movidas.iterator():
            resultado = self._reconciliar(fila, aplicar)
            if resultado:
                conteo[resultado] += 1

        filas = IntervencionCentroInfancia.all_objects.filter(
            documentacion__startswith=ORIGEN
        ).order_by("pk")
        for fila in filas.iterator():
            resultado = self._procesar(fila, aplicar)
            conteo[resultado] += 1
            if self._pendiente:
                conteo["pendientes"] += 1

        self.stdout.write(
            "Resumen: "
            f"movidos={conteo['movidos']} faltantes={conteo['faltantes']} "
            f"conflictos={conteo['conflictos']} omitidos={conteo['omitidos']} "
            f"limpiados={conteo['limpiados']} pendientes={conteo['pendientes']}"
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
        if almacen.exists(destino) and _sha256(almacen, destino) != _sha256(
            almacen, origen
        ):
            self.stderr.write(
                f"CONFLICTO pk={fila.pk}: {destino} existe con otro contenido"
            )
            return "conflictos"
        return None

    def _reconciliar(self, fila, aplicar):
        """Delete the legacy copy left by an interrupted run, only when safe."""
        destino = fila.documentacion.name
        origen = _origen_legado(fila.pk, destino)
        if origen is None or ".." in destino.split("/"):
            return None
        almacen = fila.documentacion.storage
        if not almacen.exists(origen):
            return None
        if not almacen.exists(destino) or _sha256(almacen, destino) != _sha256(
            almacen, origen
        ):
            self.stderr.write(
                f"CONFLICTO pk={fila.pk}: {origen} sigue existiendo y no coincide "
                f"con {destino}; no se borra"
            )
            return "conflictos"
        if not aplicar:
            self.stdout.write(f"LIMPIAR pk={fila.pk}: {origen}")
            return "limpiados"
        if self._borrar_origen_sin_uso(almacen, origen, fila.pk):
            self.stdout.write(f"LIMPIADO pk={fila.pk}: {origen}")
            return "limpiados"
        return "pendientes"

    def _procesar(self, fila, aplicar):
        self._pendiente = False
        origen = fila.documentacion.name
        almacen = fila.documentacion.storage
        destino = _destino(fila.pk, origen)
        omitido = self._diagnosticar(fila, almacen, destino)
        if omitido:
            return omitido
        if not aplicar:
            self.stdout.write(f"MOVER pk={fila.pk}: {origen} -> {destino}")
            return "movidos"

        if not almacen.exists(destino) and not self._copiar(
            fila.pk, almacen, origen, destino
        ):
            return "conflictos"
        try:
            actualizadas = self._actualizar(fila.pk, origen, destino)
        except DataError as exc:
            almacen.delete(destino)
            self.stderr.write(f"CONFLICTO pk={fila.pk}: no se pudo actualizar ({exc})")
            return "conflictos"
        if actualizadas:
            self._pendiente = not self._borrar_origen_sin_uso(almacen, origen, fila.pk)
        self.stdout.write(f"MOVIDO pk={fila.pk}: {origen} -> {destino}")
        return "movidos"

    def _copiar(self, pk, almacen, origen, destino):
        """Copy and verify size and hash; on failure remove only our own copy."""
        with almacen.open(origen, "rb") as archivo:
            guardado = almacen.save(destino, File(archivo))
        if (
            guardado == destino
            and almacen.size(destino) == almacen.size(origen)
            and _sha256(almacen, destino) == _sha256(almacen, origen)
        ):
            return True
        self.stderr.write(f"CONFLICTO pk={pk}: copia no verificada")
        almacen.delete(guardado)
        return False

    @staticmethod
    def _actualizar(pk, origen, destino):
        with transaction.atomic():
            return IntervencionCentroInfancia.all_objects.filter(
                pk=pk, documentacion=origen
            ).update(documentacion=destino)

    @staticmethod
    def _otra_fila_usa(origen):
        """True/False when known; None when the consumers cannot be checked.

        Another CDI row, or a Comedores intervention, may still point to the same
        old file. If the Comedores model is not installed in this runtime the
        answer is unknown, never "unused".
        """
        if IntervencionCentroInfancia.all_objects.filter(documentacion=origen).exists():
            return True
        try:
            comedores = apps.get_model("intervenciones", "Intervencion")
        except LookupError:
            return None
        return comedores.all_objects.filter(documentacion=origen).exists()

    def _borrar_origen_sin_uso(self, almacen, origen, pk):
        """Delete the old file if no consumer uses it. False when it is pending."""
        uso = self._otra_fila_usa(origen)
        if uso is None:
            self.stderr.write(
                f"PENDIENTE pk={pk}: no se pudo comprobar si Comedores usa {origen}; "
                "no se borra. Correr donde esten todas las apps instaladas."
            )
            return False
        if not uso:
            almacen.delete(origen)
        return True
