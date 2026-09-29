"""Tests del comando ``diagnosticar_datos_app_2809`` (datos del 28/9/2026).

Caso 1: la 1.1.44 guardó 2.1.6 invertida en ``elementos_guardados``.
Caso 2: la 1.1.45 vació campos con ``''`` en correcciones derivadas.
"""

import csv
import gzip
import itertools
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
TZ_LOG = "America/Argentina/Buenos_Aires"
_NUMERO_SALIDA = itertools.count()


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


def _vaciar_observacion(relevamiento, momento, actor=None):
    """Vacía ``observacion`` con save() (auditlog) y fecha la LogEntry."""
    relevamiento.observacion = None
    relevamiento.save()
    entrada = LogEntry.objects.get_for_object(relevamiento).latest("pk")
    LogEntry.objects.filter(pk=entrada.pk).update(timestamp=momento, actor=actor)
    return entrada


@pytest.fixture
def escenario(tmp_path):
    user = get_user_model().objects.create_user(username="tec_2809", password="x")
    coordinador = get_user_model().objects.create_user(
        username="coord_2809", password="x"
    )
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

    # Relevamientos del caso 2 con historial de auditlog:
    # - app: sin actor (token DRF) y con la línea del log de la API al lado;
    # - coordinador: vaciado por web (actor no territorial, sin línea de la API);
    # - retocado: vaciado por la app y cambiado después por otra LogEntry;
    # - borrado: vaciado por la app pero borrado lógicamente.
    _vaciar_observacion(relevamiento, datetime(2026, 9, 28, 21, 45, tzinfo=UTC))
    rel_coordinador = Relevamiento.objects.create(
        comedor=Comedor.objects.create(nombre="Comedor coord"),
        observacion="dato del coordinador",
    )
    _vaciar_observacion(
        rel_coordinador, datetime(2026, 9, 28, 21, 46, tzinfo=UTC), coordinador
    )
    rel_retocado = Relevamiento.objects.create(
        comedor=Comedor.objects.create(nombre="Comedor retocado"),
        observacion="primero",
    )
    _vaciar_observacion(rel_retocado, datetime(2026, 9, 28, 21, 47, tzinfo=UTC))
    rel_retocado.observacion = "segundo"
    rel_retocado.save()
    rel_retocado.observacion = None
    rel_retocado.save()
    for entrada in LogEntry.objects.get_for_object(rel_retocado).order_by("pk")[2:]:
        LogEntry.objects.filter(pk=entrada.pk).update(
            timestamp=datetime(2026, 9, 29, 10, 0, tzinfo=UTC)
        )
    rel_borrado = Relevamiento.objects.create(
        comedor=Comedor.objects.create(nombre="Comedor borrado"),
        observacion="del borrado",
    )
    _vaciar_observacion(rel_borrado, datetime(2026, 9, 28, 21, 48, tzinfo=UTC))
    Relevamiento.all_objects.filter(pk=rel_borrado.pk).update(
        deleted_at=datetime(2026, 9, 29, 9, 0, tzinfo=UTC)
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
        + _linea("18:45:03", "Relevamiento", relevamiento.pk)
        + _linea("18:47:02", "Relevamiento", rel_retocado.pk)
        + _linea("18:48:01", "Relevamiento", rel_borrado.pk)
        + "[2026-09-28 18:22:00,000] otra cosa INFO django: sin relación\n",
        encoding="utf-8",
    )
    return {
        "log": str(log),
        "relevamiento": relevamiento,
        "rel_coordinador": rel_coordinador,
        "rel_retocado": rel_retocado,
        "rel_borrado": rel_borrado,
        "dentro_1": dentro_1,
        "fuera": fuera,
        "sin_valor": sin_valor,
        "dentro_2": dentro_2,
        "tarde": tarde,
        "reenviado": reenviado,
    }


def _correr(tmp_path, *args):
    salida = tmp_path / f"salida_{next(_NUMERO_SALIDA)}.csv"
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


def _token(escenario_datos, invertir_ids=()):
    parametros = reparacion.Parametros(
        evidencias=reparacion.leer_logs([escenario_datos["log"]], TZ_LOG),
        invertir_ids=frozenset(invertir_ids),
    )
    return reparacion.diagnosticar(parametros).token()


def _fila_relevamiento(filas, relevamiento):
    return next(
        f
        for f in filas
        if f["modelo"] == "relevamiento" and int(f["registro_id"]) == relevamiento.pk
    )


def _elementos(seguimiento):
    seguimiento.servicios_basicos.refresh_from_db()
    return seguimiento.servicios_basicos.elementos_guardados


@pytest.mark.django_db
def test_dry_run_caso_1_queda_a_revisar_sin_invertir_ids(escenario, tmp_path):
    filas = _correr(tmp_path, "--log", escenario["log"])

    caso_1 = [f for f in filas if f["caso"] == "1"]
    assert [int(f["registro_id"]) for f in caso_1] == [
        escenario["dentro_1"].pk,
        escenario["reenviado"].pk,
    ]
    assert caso_1[0]["accion"] == reparacion.ACCION_A_REVISAR
    assert caso_1[0]["valor_actual"] == "True"
    assert caso_1[0]["valor_propuesto"] == "False"
    assert reparacion.AVISO_CASO1 in caso_1[0]["detalle"]
    assert caso_1[0]["comedor"] == "Comedor 2809"
    assert caso_1[0]["fecha_evidencia_utc"] == "2026-09-28T21:20:01+00:00"
    assert "uid-tec" in caso_1[0]["tecnico"] and "tec_2809" in caso_1[0]["tecnico"]
    # Reenviado después: el valor pudo corregirse, queda para revisión manual.
    assert caso_1[1]["accion"] == reparacion.ACCION_CONFLICTO
    assert "2026-09-28T23:10:00+00:00" in caso_1[1]["detalle"]
    assert not [f for f in caso_1 if f["accion"] in reparacion.ACCIONES_APLICABLES]


@pytest.mark.django_db
def test_invertir_ids_confirma_uno_por_uno(escenario, tmp_path):
    filas = _correr(
        tmp_path,
        "--log",
        escenario["log"],
        "--invertir-ids",
        f"{escenario['dentro_1'].pk},{escenario['reenviado'].pk},999999",
    )
    caso_1 = {int(f["registro_id"]): f for f in filas if f["caso"] == "1"}
    assert caso_1[escenario["dentro_1"].pk]["accion"] == reparacion.ACCION_INVERTIR
    assert reparacion.AVISO_CASO1 in caso_1[escenario["dentro_1"].pk]["detalle"]
    # El conflicto no se pisa aunque venga en la lista.
    assert caso_1[escenario["reenviado"].pk]["accion"] == reparacion.ACCION_CONFLICTO


@pytest.mark.django_db
def test_dry_run_caso_2(escenario, tmp_path):
    filas = _correr(tmp_path, "--log", escenario["log"])

    caso_2_seg = [f for f in filas if f["caso"] == "2" and f["modelo"] == "seguimiento"]
    assert {int(f["registro_id"]) for f in caso_2_seg} == {escenario["dentro_2"].pk}
    # Solo el bloque con datos; el de higiene está entero vacío (no lo tocó la app).
    assert len(caso_2_seg) == 1
    assert caso_2_seg[0]["campo"].startswith("servicios_basicos: ")
    assert "gas_red" in caso_2_seg[0]["campo"]
    assert caso_2_seg[0]["accion"] == reparacion.ACCION_SOLO_REPORTE
    assert caso_2_seg[0]["valor_anterior"] == "(sin historial)"

    app = _fila_relevamiento(filas, escenario["relevamiento"])
    assert app["campo"] == "observacion"
    assert app["valor_actual"] == "NULL"
    assert app["valor_anterior"] == "texto original"
    assert app["accion"] == reparacion.ACCION_RESTAURAR
    assert app["actor"] == "(sin actor)"
    assert app["entrada_auditlog"].isdigit()
    assert "log:info.log" in app["detalle"]

    coordinador = _fila_relevamiento(filas, escenario["rel_coordinador"])
    assert coordinador["accion"] == reparacion.ACCION_A_REVISAR
    assert coordinador["actor"] == "coord_2809"

    retocado = _fila_relevamiento(filas, escenario["rel_retocado"])
    assert retocado["accion"] == reparacion.ACCION_CONFLICTO
    assert "después del vaciado" in retocado["detalle"]

    borrado = _fila_relevamiento(filas, escenario["rel_borrado"])
    assert borrado["accion"] == reparacion.ACCION_SOLO_REPORTE
    assert "borrado" in borrado["detalle"]


@pytest.mark.django_db
def test_actor_territorial_alcanza_sin_linea_de_log(escenario, tmp_path):
    territorial = escenario["relevamiento"].territorial_user
    territorial.profile.es_territorial_comedor = True
    territorial.profile.save(update_fields=["es_territorial_comedor"])
    LogEntry.objects.get_for_object(escenario["rel_coordinador"]).update(
        actor=territorial
    )
    filas = _correr(tmp_path, "--log", escenario["log"])
    fila = _fila_relevamiento(filas, escenario["rel_coordinador"])
    assert fila["accion"] == reparacion.ACCION_RESTAURAR
    assert "actor territorial" in fila["detalle"]


@pytest.mark.django_db
def test_dry_run_no_escribe_nada(escenario, tmp_path):
    antes = _snapshot()
    with (tmp_path / "stdout.txt").open("w", encoding="utf-8") as stdout:
        with CaptureQueriesContext(connection) as consultas:
            call_command(
                COMANDO,
                "--log",
                escenario["log"],
                "--invertir-ids",
                str(escenario["dentro_1"].pk),
                stdout=stdout,
            )
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
    # El token sin --invertir-ids no sirve para aplicar con --invertir-ids.
    with pytest.raises(CommandError, match="no coincide"):
        call_command(
            COMANDO,
            "--log",
            escenario["log"],
            "--invertir-ids",
            str(escenario["dentro_1"].pk),
            "--aplicar",
            "--confirmar",
            _token(escenario),
        )
    assert _snapshot() == antes


@pytest.mark.django_db
def test_aplicar_sin_invertir_ids_no_toca_el_caso_1(escenario):
    call_command(
        COMANDO,
        "--log",
        escenario["log"],
        "--aplicar",
        "--confirmar",
        _token(escenario),
    )
    assert _elementos(escenario["dentro_1"]) is True
    escenario["relevamiento"].refresh_from_db()
    assert escenario["relevamiento"].observacion == "texto original"


@pytest.mark.django_db
def test_aplicar_repara_solo_lo_listado_y_es_idempotente(escenario, tmp_path):
    ids = [escenario["dentro_1"].pk]
    token = _token(escenario, ids)
    args = ("--log", escenario["log"], "--invertir-ids", str(ids[0]))
    call_command(COMANDO, *args, "--aplicar", "--confirmar", token)

    assert _elementos(escenario["dentro_1"]) is False
    assert _elementos(escenario["fuera"]) is True  # fuera de la ventana: intacto
    assert _elementos(escenario["sin_valor"]) is None
    assert _elementos(escenario["reenviado"]) is True  # ambiguo: no se toca
    escenario["relevamiento"].refresh_from_db()
    assert escenario["relevamiento"].observacion == "texto original"
    for clave in ("rel_coordinador", "rel_borrado"):
        assert Relevamiento.all_objects.get(pk=escenario[clave].pk).observacion is None
    # El caso 2 de seguimientos no se repara (sin historial).
    escenario["dentro_2"].servicios_basicos.refresh_from_db()
    assert escenario["dentro_2"].servicios_basicos.gas_red is None
    marcas = LogEntry.objects.filter(additional_data__reparacion=reparacion.MARCA)
    assert marcas.count() == 2

    # Segunda corrida con el mismo token: nada para aplicar, nada cambia.
    despues = _snapshot()
    call_command(COMANDO, *args, "--aplicar", "--confirmar", token)
    assert _snapshot() == despues
    assert _elementos(escenario["dentro_1"]) is False

    filas = _correr(tmp_path, *args)
    acciones = {(f["caso"], f["modelo"], f["accion"]) for f in filas}
    assert ("1", "seguimiento", reparacion.ACCION_YA_REPARADO) in acciones
    assert ("2", "relevamiento", reparacion.ACCION_YA_REPARADO) in acciones
    assert not [f for f in filas if f["accion"] in reparacion.ACCIONES_APLICABLES]


@pytest.mark.django_db
def test_carrera_entre_lectura_y_update_revierte_todo(escenario, monkeypatch):
    """Si un registro cambia entre el diagnóstico y el UPDATE, no queda nada."""
    ids = [escenario["dentro_1"].pk]
    token = _token(escenario, ids)
    original = reparacion.diagnosticar

    def diagnosticar_y_pisar(parametros):
        diagnostico = original(parametros)
        # Otro proceso escribe el relevamiento después de la lectura.
        Relevamiento.all_objects.filter(pk=escenario["relevamiento"].pk).update(
            observacion="escrito en paralelo"
        )
        return diagnostico

    monkeypatch.setattr(reparacion, "diagnosticar", diagnosticar_y_pisar)
    antes = LogEntry.objects.count()
    with pytest.raises(CommandError, match="cambió durante la reparación"):
        call_command(
            COMANDO,
            "--log",
            escenario["log"],
            "--invertir-ids",
            str(ids[0]),
            "--aplicar",
            "--confirmar",
            token,
        )
    # La inversión del caso 1 (primera fila) también se revirtió.
    assert _elementos(escenario["dentro_1"]) is True
    assert LogEntry.objects.count() == antes
    escenario["relevamiento"].refresh_from_db()
    assert escenario["relevamiento"].observacion is None


@pytest.mark.django_db
def test_log_del_cambio_se_escribe_despues_del_commit(
    escenario, monkeypatch, django_capture_on_commit_callbacks
):
    mensajes = []
    monkeypatch.setattr(reparacion.logger, "info", mensajes.append)
    ids = [escenario["dentro_1"].pk]
    with django_capture_on_commit_callbacks(execute=False) as callbacks:
        call_command(
            COMANDO,
            "--log",
            escenario["log"],
            "--invertir-ids",
            str(ids[0]),
            "--aplicar",
            "--confirmar",
            _token(escenario, ids),
        )
        assert mensajes == []
    for callback in callbacks:
        callback()
    assert len(mensajes) == 2
    assert all(m.startswith(f"[{reparacion.MARCA}]") for m in mensajes)


@pytest.mark.django_db
def test_ids_manuales_sin_hora_quedan_a_revisar(escenario, tmp_path):
    pk = escenario["fuera"].pk
    filas = _correr(tmp_path, "--seguimientos", str(pk), "--caso", "1")
    assert [(f["caso"], int(f["registro_id"]), f["fuente"]) for f in filas] == [
        ("1", pk, "manual")
    ]
    assert filas[0]["accion"] == reparacion.ACCION_A_REVISAR
    assert "manual" in filas[0]["detalle"]

    filas = _correr(
        tmp_path, "--seguimientos", str(pk), "--caso", "1", "--invertir-ids", str(pk)
    )
    assert filas[0]["accion"] == reparacion.ACCION_INVERTIR


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


@pytest.mark.django_db
def test_salida_existente_no_se_pisa_sin_forzar(tmp_path):
    salida = tmp_path / "ya.csv"
    salida.write_text("previo", encoding="utf-8")
    with pytest.raises(CommandError, match="ya existe"):
        call_command(COMANDO, "--salida", str(salida))
    assert salida.read_text(encoding="utf-8") == "previo"
    call_command(COMANDO, "--salida", str(salida), "--forzar", "--formato", "csv")
    assert salida.read_text(encoding="utf-8").startswith("caso,modelo")


def test_leer_logs_convierte_zona_y_acepta_gz(tmp_path):
    carpeta = tmp_path / "logs" / "2026-09-28"
    carpeta.mkdir(parents=True)
    with gzip.open(carpeta / "info.log.gz", "wt", encoding="utf-8") as archivo:
        archivo.write(_linea("18:20:01", "Relevamiento", 7))
        archivo.write(_linea("18:20:02", "Primer seguimiento", 8))
    evidencias = reparacion.leer_logs([tmp_path / "logs"], TZ_LOG)
    assert [(e.modelo, e.pk, e.momento) for e in evidencias] == [
        (reparacion.RELEVAMIENTO, 7, datetime(2026, 9, 28, 21, 20, 1, tzinfo=UTC)),
        (reparacion.SEGUIMIENTO, 8, datetime(2026, 9, 28, 21, 20, 2, tzinfo=UTC)),
    ]


def test_linea_con_fecha_invalida_se_ignora_con_aviso(tmp_path):
    log = tmp_path / "info.log"
    log.write_text(
        "[2026-13-45 18:20:01,123] api_views INFO django: "
        "Primer seguimiento 5 actualizado correctamente\n"
        + _linea("18:20:02", "Primer seguimiento", 6),
        encoding="utf-8",
    )
    avisos = []
    evidencias = reparacion.leer_logs([log], TZ_LOG, advertencias=avisos)
    assert [e.pk for e in evidencias] == [6]
    assert len(avisos) == 1 and "fecha inválida" in avisos[0]


def test_log_inexistente_es_error(tmp_path):
    with pytest.raises(CommandError, match="No existe"):
        call_command(COMANDO, "--log", str(tmp_path / "nada.log"))
