"""Diagnóstico (y reparación opcional) de los datos que dañó la app el 28/9/2026.

Por defecto es SOLO LECTURA. Ver ``relevamientos/reparacion_app_2809.py``.

Ejemplos::

    # 1) diagnóstico con los logs de la API (recomendado)
    python manage.py diagnosticar_datos_app_2809 --log /sisoc/logs --formato csv \
        --salida /tmp/diagnostico_2809.csv

    # 2) aplicar exactamente lo listado (el token lo imprime el paso 1)
    python manage.py diagnosticar_datos_app_2809 --log /sisoc/logs \
        --aplicar --confirmar 1a2b3c4d5e6f
"""

import csv
from collections import Counter
from datetime import timezone as dt_timezone

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from relevamientos import reparacion_app_2809 as reparacion

_ANCHO_CELDA = 70
_COLUMNAS_TABLA = (
    "caso",
    "modelo",
    "registro_id",
    "comedor",
    "fecha_evidencia_utc",
    "tecnico",
    "estado_validacion",
    "campo",
    "valor_actual",
    "valor_anterior",
    "valor_propuesto",
    "accion",
)


def _fecha(valor):
    fecha = parse_datetime(valor)
    if fecha is None:
        raise CommandError(f"Fecha inválida: {valor!r} (usar ISO 8601).")
    if timezone.is_naive(fecha):
        fecha = fecha.replace(tzinfo=dt_timezone.utc)
    return fecha.astimezone(dt_timezone.utc)


def _ids(valor):
    try:
        return [int(parte) for parte in valor.replace(" ", ",").split(",") if parte]
    except ValueError as exc:
        raise CommandError(f"Lista de ids inválida: {valor!r}") from exc


def _recortar(valor):
    valor = str(valor)
    if len(valor) <= _ANCHO_CELDA:
        return valor
    return valor[: _ANCHO_CELDA - 1] + "…"


class Command(BaseCommand):
    help = (
        "Diagnostica (solo lectura) los datos que dañaron las versiones 1.1.44 "
        "(2.1.6 invertida) y 1.1.45 (campos vaciados) de la app el 28/9/2026. "
        "Con --aplicar --confirmar <token> repara lo que se puede probar."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--desde",
            default=reparacion.DESDE_DEFAULT.isoformat(),
            help="Inicio de la ventana del caso 1 (ISO; sin zona = UTC).",
        )
        parser.add_argument(
            "--corte",
            default=reparacion.CORTE_DEFAULT.isoformat(),
            help="Fin del caso 1 e inicio del caso 2 (salida de la 1.1.45).",
        )
        parser.add_argument(
            "--hasta",
            default=reparacion.HASTA_DEFAULT.isoformat(),
            help="Fin de la ventana del caso 2 (salida de la 1.1.46).",
        )
        parser.add_argument(
            "--caso", choices=("1", "2", "todos"), default="todos", help="Caso."
        )
        parser.add_argument(
            "--log",
            action="append",
            default=[],
            help=(
                "Archivo o carpeta de logs de la API (info.log, .gz). Repetible. "
                "Es la única señal con hora para los seguimientos."
            ),
        )
        parser.add_argument(
            "--log-tz",
            default=settings.TIME_ZONE,
            help="Zona horaria de asctime en los logs (default: TIME_ZONE).",
        )
        parser.add_argument(
            "--seguimientos",
            default="",
            help="Ids de seguimiento a revisar sin evidencia de log (1,2,3).",
        )
        parser.add_argument(
            "--relevamientos",
            default="",
            help="Ids de relevamiento a revisar sin evidencia de log (1,2,3).",
        )
        parser.add_argument("--formato", choices=("tabla", "csv"), default="tabla")
        parser.add_argument("--salida", help="Escribe el listado en este archivo.")
        parser.add_argument(
            "--aplicar",
            action="store_true",
            help="Aplica los cambios listados (requiere --confirmar).",
        )
        parser.add_argument(
            "--confirmar",
            default="",
            help="Token que imprime el diagnóstico para el conjunto exacto de cambios.",
        )

    def handle(self, *args, **options):
        parametros = self._parametros(options)
        if options["aplicar"]:
            if not options["confirmar"]:
                raise CommandError(
                    "--aplicar requiere --confirmar <token>: corré primero sin "
                    "--aplicar, revisá la lista y copiá el token."
                )
            try:
                diagnostico, mensajes = reparacion.aplicar(
                    parametros, options["confirmar"]
                )
            except (ValueError, reparacion.CambioConcurrenteError) as exc:
                raise CommandError(str(exc)) from exc
            self._reportar(diagnostico, options, aplicado=True)
            for mensaje in mensajes:
                self.stdout.write(mensaje)
            self.stdout.write(
                self.style.SUCCESS(f"Cambios aplicados: {len(mensajes)}.")
                if mensajes
                else "Nada para aplicar (todo lo reparable ya estaba reparado)."
            )
            return
        diagnostico = reparacion.diagnosticar(parametros)
        self._reportar(diagnostico, options, aplicado=False)

    def _parametros(self, options):
        desde, corte, hasta = (
            _fecha(options["desde"]),
            _fecha(options["corte"]),
            _fecha(options["hasta"]),
        )
        if not desde <= corte <= hasta:
            raise CommandError("Se espera --desde <= --corte <= --hasta.")
        try:
            evidencias = reparacion.leer_logs(options["log"], options["log_tz"])
        except (FileNotFoundError, OSError) as exc:
            raise CommandError(str(exc)) from exc
        evidencias += reparacion.evidencias_manuales(
            reparacion.SEGUIMIENTO, _ids(options["seguimientos"])
        )
        evidencias += reparacion.evidencias_manuales(
            reparacion.RELEVAMIENTO, _ids(options["relevamientos"])
        )
        casos = (1, 2) if options["caso"] == "todos" else (int(options["caso"]),)
        self.stdout.write(
            f"Ventana caso 1 (1.1.44): {desde.isoformat()} a {corte.isoformat()}\n"
            f"Ventana caso 2 (1.1.45): {corte.isoformat()} a {hasta.isoformat()}\n"
            f"Evidencias leídas: {len(evidencias)} (logs: {len(options['log'])}, "
            f"zona de los logs: {options['log_tz']})"
        )
        if not options["log"] and not (
            options["seguimientos"] or options["relevamientos"]
        ):
            self.stdout.write(
                self.style.WARNING(
                    "Sin --log ni ids no hay señal en la base para ubicar "
                    "seguimientos en el tiempo: solo se revisa el historial de "
                    "auditlog de relevamientos."
                )
            )
        return reparacion.Parametros(
            desde=desde, corte=corte, hasta=hasta, casos=casos, evidencias=evidencias
        )

    def _reportar(self, diagnostico, options, aplicado):
        for advertencia in diagnostico.advertencias:
            self.stdout.write(self.style.WARNING(advertencia))
        filas = [fila.como_dict() for fila in diagnostico.filas]
        if options["salida"]:
            with open(options["salida"], "w", encoding="utf-8", newline="") as archivo:
                self._escribir(filas, options["formato"], archivo)
            self.stdout.write(f"Listado escrito en {options['salida']}.")
        else:
            self._escribir(filas, options["formato"], self.stdout)

        for clave, cantidad in diagnostico.revisados.items():
            self.stdout.write(f"Revisados {clave}: {cantidad}")
        conteo = Counter((fila.caso, fila.accion) for fila in diagnostico.filas)
        for (caso, accion), cantidad in sorted(conteo.items()):
            self.stdout.write(f"Caso {caso} · {accion}: {cantidad}")
        if aplicado:
            return
        aplicables = diagnostico.aplicables
        if aplicables:
            self.stdout.write(
                self.style.WARNING(
                    f"{len(aplicables)} cambios reparables. Para aplicar EXACTAMENTE "
                    "estos, repetí el comando con los mismos parámetros y "
                    f"--aplicar --confirmar {diagnostico.token()}"
                )
            )
        else:
            self.stdout.write("Nada reparable automáticamente. No se escribió nada.")

    @staticmethod
    def _escribir(filas, formato, destino):
        if formato == "csv":
            writer = csv.DictWriter(
                destino, fieldnames=reparacion.COLUMNAS, lineterminator="\n"
            )
            writer.writeheader()
            writer.writerows(filas)
            return
        if not filas:
            destino.write("Sin candidatos.\n")
            return
        anchos = {
            columna: max(
                len(columna), *(len(_recortar(fila[columna])) for fila in filas)
            )
            for columna in _COLUMNAS_TABLA
        }
        destino.write(
            "  ".join(columna.ljust(anchos[columna]) for columna in _COLUMNAS_TABLA)
            + "\n"
        )
        for fila in filas:
            destino.write(
                "  ".join(
                    _recortar(fila[columna]).ljust(anchos[columna])
                    for columna in _COLUMNAS_TABLA
                )
                + "\n"
            )
