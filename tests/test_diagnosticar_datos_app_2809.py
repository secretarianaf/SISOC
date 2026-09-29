"""Tests del comando ``diagnosticar_datos_app_2809`` (datos del 28/9/2026).

Caso 1: la 1.1.44 guardó 2.1.6 invertida en ``elementos_guardados``.
Caso 2: la 1.1.45 vació campos con ``''`` en correcciones derivadas.
"""

import csv
import gzip
from datetime import datetime, timezone as dt_timezone

import pytest
from auditlog.models import LogEntry
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test.utils import CaptureQueriesContext

from comedores.models import Comedor
from relevamientos import reparacion_app_2809 as reparacion
from relevamientos.models import (
    CondicionesHigieneSeguimiento,
    PrimerSeguimiento,
    Relevamiento,
    ServiciosBasicosSeguimiento,
)

UTC = dt_timezone.utc
COMANDO = "diagnosticar_datos_app_2809"


def _linea(hora_local, tipo, pk):
    """Línea del info.log (asctime en hora de Buenos Aires, UTC-3)."""
    return (
        f"[2026-09-28 {hora_local},123] api_views INFO django: "
        f"{tipo} {pk} actualizado correctamente\n"
    )


def _seguimiento(relevamiento, orden, **servicios):
    bloque = ServiciosBasicosSeguimiento.objects.create(**servicios)
    return PrimerSeguimiento.objects.create(
        id_relevamiento=relevamiento,
        numero_orden=orden,
        tecnico="uid-tec",
        servicios_basicos=bloque,
    )


@pytest.fixture
def escenario(tmp_path):
    user = get_user_model().objects.create_user(username="tec_2809", password="x")
    comedor = Comedor.objects.create(nombre="Comedor 2809")
    relevamiento = Relevamiento.objects.create(
        comedor=comedor, territorial_user=user, observacion="texto original"
    )
    # Caso 1: dentro (21:20 UTC), fuera antes (20:00 UTC) y sin respuesta.
    dentro_1 = _seguimiento(
        relevamiento, 1, agua_potable=True, elementos_guardados=True
    )
    fuera = _seguimiento(relevamiento, 2, agua_potable=True, elementos_guardados=True)
    sin_valor = _seguimiento(relevamiento, 3, agua_potable=True)
    # Caso 2 (21:40 UTC): un bloque con datos y campos vaciados, otro intacto.
    dentro_2 = _seguimiento(relevamiento, 4, agua_potable=True, gas_red=None)
    higiene = CondicionesHigieneSeguimiento.objects.create()
    PrimerSeguimiento.objects.filter(pk=dentro_2.pk).update(condiciones_higiene=higiene)
    # Caso 2 fuera de ventana (22:30 UTC, ya con 1.1.46).
    tarde = _seguimiento(relevamiento, 5, agua_potable=True)
    # Caso 1 reenviado más tarde (23:10 UTC): ambiguo, no se invierte.
    reenviado = _seguimiento(
        relevamiento, 6, agua_potable=True, elementos_guardados=True
    )

    # Relevamiento: auditlog registra el vaciado de `observacion` dentro del caso 2.
    relevamiento.observacion = None
    relevamiento.save()
    entrada = LogEntry.objects.get_for_object(relevamiento).latest("pk")
    LogEntry.objects.filter(pk=entrada.pk).update(
        timestamp=datetime(2026, 9, 28, 21, 45, tzinfo=UTC)
    )

    log = tmp_path / "info.log"
    log.write_text(
        _linea("17:00:00", "Primer seguimiento", fuera.pk)
        + _linea("18:20:01", "Primer seguimiento", dentro_1.pk)
        + _linea("18:21:00", "Primer seguimiento", sin_valor.pk)
        + _linea("18:40:00", "Primer seguimiento", dentro_2.pk)
        + _linea("19:30:00", "Primer seguimiento", tarde.pk)
        + _linea("18:25:00", "Primer seguimiento", reenviado.pk)
        + _linea("20:10:00", "Primer seguimiento", reenviado.pk)
        + "[2026-09-28 18:22:00,000] otra cosa INFO django: sin relación\n",
        encoding="utf-8",
    )
    return {
        "log": str(log),
        "relevamiento": relevamiento,
        "dentro_1": dentro_1,
        "fuera": fuera,
        "sin_valor": sin_valor,
        "dentro_2": dentro_2,
        "tarde": tarde,
        "reenviado": reenviado,
    }


def _correr(tmp_path, *args):
    salida = tmp_path / "salida.csv"
    call_command(COMANDO, *args, "--formato", "csv", "--salida", str(salida))
    with salida.open(encoding="utf-8") as archivo:
        return list(csv.DictReader(archivo))


def _snapshot():
    return {
        "servicios": list(
            ServiciosBasicosSeguimiento.objects.order_by("pk").values_list()
        ),
        "seguimientos": list(PrimerSeguimiento.objects.order_by("pk").values_list()),
        "relevamientos": list(Relevamiento.all_objects.order_by("pk").values_list()),
        "logentries": LogEntry.objects.count(),
    }


def _token(escenario_datos):
    parametros = reparacion.Parametros(
        evidencias=reparacion.leer_logs(
            [escenario_datos["log"]], "America/Argentina/Buenos_Aires"
        )
    )
    return reparacion.diagnosticar(parametros).token()


@pytest.mark.django_db
def test_dry_run_lista_candidatos_por_caso(escenario, tmp_path):
    filas = _correr(tmp_path, "--log", escenario["log"])

    caso_1 = [f for f in filas if f["caso"] == "1"]
    assert [int(f["registro_id"]) for f in caso_1] == [
        escenario["dentro_1"].pk,
        escenario["reenviado"].pk,
    ]
    # Reenviado después: el valor pudo corregirse, queda para revisión manual.
    assert caso_1[1]["accion"] == reparacion.ACCION_CONFLICTO
    assert "2026-09-28T23:10:00+00:00" in caso_1[1]["detalle"]
    assert caso_1[0]["valor_actual"] == "True"
    assert caso_1[0]["valor_propuesto"] == "False"
    assert caso_1[0]["accion"] == reparacion.ACCION_INVERTIR
    assert caso_1[0]["comedor"] == "Comedor 2809"
    assert caso_1[0]["fecha_evidencia_utc"] == "2026-09-28T21:20:01+00:00"
    assert "uid-tec" in caso_1[0]["tecnico"] and "tec_2809" in caso_1[0]["tecnico"]

    caso_2_seg = [f for f in filas if f["caso"] == "2" and f["modelo"] == "seguimiento"]
    assert {int(f["registro_id"]) for f in caso_2_seg} == {escenario["dentro_2"].pk}
    # Solo el bloque con datos; el de higiene está entero vacío (no lo tocó la app).
    assert len(caso_2_seg) == 1
    assert caso_2_seg[0]["campo"].startswith("servicios_basicos: ")
    assert "gas_red" in caso_2_seg[0]["campo"]
    assert caso_2_seg[0]["accion"] == reparacion.ACCION_SOLO_REPORTE
    assert caso_2_seg[0]["valor_anterior"] == "(sin historial)"

    caso_2_rel = [f for f in filas if f["modelo"] == "relevamiento"]
    assert len(caso_2_rel) == 1
    assert caso_2_rel[0]["campo"] == "observacion"
    assert caso_2_rel[0]["valor_actual"] == "NULL"
    assert caso_2_rel[0]["valor_anterior"] == "texto original"
    assert caso_2_rel[0]["accion"] == reparacion.ACCION_RESTAURAR


@pytest.mark.django_db
def test_dry_run_no_escribe_nada(escenario, tmp_path):
    antes = _snapshot()
    with (tmp_path / "stdout.txt").open("w", encoding="utf-8") as stdout:
        with CaptureQueriesContext(connection) as consultas:
            call_command(COMANDO, "--log", escenario["log"], stdout=stdout)
    escrituras = [
        q["sql"]
        for q in consultas.captured_queries
        if q["sql"].lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))
    ]
    assert escrituras == []
    assert _snapshot() == antes


@pytest.mark.django_db
def test_aplicar_sin_confirmacion_o_con_token_ajeno_no_escribe(escenario, tmp_path):
    antes = _snapshot()
    with pytest.raises(CommandError, match="--confirmar"):
        call_command(COMANDO, "--log", escenario["log"], "--aplicar")
    with pytest.raises(CommandError, match="no coincide"):
        call_command(
            COMANDO, "--log", escenario["log"], "--aplicar", "--confirmar", "ffffff"
        )
    assert _snapshot() == antes


@pytest.mark.django_db
def test_aplicar_repara_solo_lo_listado_y_es_idempotente(escenario, tmp_path):
    token = _token(escenario)
    call_command(COMANDO, "--log", escenario["log"], "--aplicar", "--confirmar", token)

    def elementos(clave):
        escenario[clave].servicios_basicos.refresh_from_db()
        return escenario[clave].servicios_basicos.elementos_guardados

    assert elementos("dentro_1") is False
    assert elementos("fuera") is True  # fuera de la ventana: intacto
    assert elementos("sin_valor") is None
    assert elementos("reenviado") is True  # ambiguo: no se toca
    escenario["relevamiento"].refresh_from_db()
    assert escenario["relevamiento"].observacion == "texto original"
    # El caso 2 de seguimientos no se repara (sin historial).
    escenario["dentro_2"].servicios_basicos.refresh_from_db()
    assert escenario["dentro_2"].servicios_basicos.gas_red is None
    marcas = LogEntry.objects.filter(additional_data__reparacion=reparacion.MARCA)
    assert marcas.count() == 2

    # Segunda corrida con el mismo token: nada para aplicar, nada cambia.
    despues = _snapshot()
    call_command(COMANDO, "--log", escenario["log"], "--aplicar", "--confirmar", token)
    assert _snapshot() == despues
    assert elementos("dentro_1") is False

    filas = _correr(tmp_path, "--log", escenario["log"])
    acciones = {(f["caso"], f["modelo"], f["accion"]) for f in filas}
    assert ("1", "seguimiento", reparacion.ACCION_YA_REPARADO) in acciones
    assert ("2", "relevamiento", reparacion.ACCION_YA_REPARADO) in acciones
    assert not [f for f in filas if f["accion"] in reparacion.ACCIONES_APLICABLES]


@pytest.mark.django_db
def test_relevamiento_modificado_despues_es_conflicto_y_no_se_toca(escenario, tmp_path):
    Relevamiento.all_objects.filter(pk=escenario["relevamiento"].pk).update(
        observacion="corregido a mano"
    )
    filas = _correr(tmp_path, "--log", escenario["log"])
    fila = next(f for f in filas if f["modelo"] == "relevamiento")
    assert fila["accion"] == reparacion.ACCION_CONFLICTO

    call_command(
        COMANDO,
        "--log",
        escenario["log"],
        "--aplicar",
        "--confirmar",
        _token(escenario),
    )
    escenario["relevamiento"].refresh_from_db()
    assert escenario["relevamiento"].observacion == "corregido a mano"


@pytest.mark.django_db
def test_ids_manuales_y_caso_unico(escenario, tmp_path):
    filas = _correr(
        tmp_path, "--seguimientos", str(escenario["fuera"].pk), "--caso", "1"
    )
    assert [(f["caso"], int(f["registro_id"]), f["fuente"]) for f in filas] == [
        ("1", escenario["fuera"].pk, "manual")
    ]


@pytest.mark.django_db
def test_ventana_ampliada_incluye_envios_tardios(escenario, tmp_path):
    filas = _correr(
        tmp_path, "--log", escenario["log"], "--hasta", "2026-09-29T03:00:00Z"
    )
    ids = {int(f["registro_id"]) for f in filas if f["modelo"] == "seguimiento"}
    assert escenario["tarde"].pk in ids


@pytest.mark.django_db
def test_seguimiento_inexistente_en_log_es_advertencia(tmp_path):
    log = tmp_path / "info.log"
    log.write_text(_linea("18:20:00", "Primer seguimiento", 999999), encoding="utf-8")
    salida = tmp_path / "out.txt"
    with salida.open("w", encoding="utf-8") as stdout:
        call_command(COMANDO, "--log", str(log), stdout=stdout)
    assert "999999" in salida.read_text(encoding="utf-8")
    assert "no existe" in salida.read_text(encoding="utf-8")


def test_leer_logs_convierte_zona_y_acepta_gz(tmp_path):
    carpeta = tmp_path / "logs" / "2026-09-28"
    carpeta.mkdir(parents=True)
    with gzip.open(carpeta / "info.log.gz", "wt", encoding="utf-8") as archivo:
        archivo.write(_linea("18:20:01", "Relevamiento", 7))
        archivo.write(_linea("18:20:02", "Primer seguimiento", 8))
    evidencias = reparacion.leer_logs(
        [tmp_path / "logs"], "America/Argentina/Buenos_Aires"
    )
    assert [(e.modelo, e.pk, e.momento) for e in evidencias] == [
        (reparacion.RELEVAMIENTO, 7, datetime(2026, 9, 28, 21, 20, 1, tzinfo=UTC)),
        (reparacion.SEGUIMIENTO, 8, datetime(2026, 9, 28, 21, 20, 2, tzinfo=UTC)),
    ]


def test_log_inexistente_es_error(tmp_path):
    with pytest.raises(CommandError, match="No existe"):
        call_command(COMANDO, "--log", str(tmp_path / "nada.log"))
