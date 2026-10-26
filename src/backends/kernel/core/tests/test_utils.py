import logging
import os
import stat
from datetime import datetime
from unittest.mock import patch

from django.utils import timezone

from core.utils import DailyFileHandler


def _ts(*args):
    """Timestamp del mediodía local de la fecha dada."""
    return datetime(*args, 12, tzinfo=timezone.get_current_timezone()).timestamp()


def test_daily_file_handler_creates_group_writable_log_path(tmp_path):
    previous_umask = os.umask(0o022)
    try:
        with patch("core.utils.time_module.time", return_value=_ts(2026, 7, 14)):
            handler = DailyFileHandler(tmp_path / "critical.log")
    finally:
        os.umask(previous_umask)

    handler.close()
    daily_folder = tmp_path / "2026-07-14"
    log_file = daily_folder / "critical.log"

    assert stat.S_IMODE(daily_folder.stat().st_mode) & stat.S_IWGRP
    assert stat.S_IMODE(log_file.stat().st_mode) & stat.S_IWGRP


def test_daily_file_handler_cambia_de_carpeta_cuando_cambia_el_dia(tmp_path):
    # Issue #2750: la fecha se fijaba al arrancar el proceso y los errores de
    # hoy terminaban en la carpeta del día de arranque.
    with patch("core.utils.time_module.time", return_value=_ts(2026, 10, 15)):
        handler = DailyFileHandler(tmp_path / "error.log")
    for msg, dia in (("del 15", 15), ("del 21", 21)):
        handler.handle(
            logging.makeLogRecord(
                {"msg": msg, "levelno": 40, "created": _ts(2026, 10, dia)}
            )
        )
    handler.close()

    assert (tmp_path / "2026-10-15" / "error.log").read_text().strip() == "del 15"
    assert (tmp_path / "2026-10-21" / "error.log").read_text().strip() == "del 21"
    for ruta in (tmp_path / "2026-10-21", tmp_path / "2026-10-21" / "error.log"):
        assert stat.S_IMODE(ruta.stat().st_mode) & stat.S_IWGRP


def test_daily_file_handler_no_depende_de_timezone_now(tmp_path):
    # Tests de otros módulos parchean ``timezone.now`` con valores naive o
    # strings; loguear en ese contexto no debe lanzar excepciones.
    handler = DailyFileHandler(tmp_path / "error.log")
    record = logging.makeLogRecord({"msg": "ok", "levelno": 40})
    with patch("django.utils.timezone.now", return_value="now"):
        handler.handle(record)
    handler.close()

    tz = timezone.get_current_timezone()
    hoy = datetime.fromtimestamp(record.created, tz=tz).strftime("%Y-%m-%d")
    assert (tmp_path / hoy / "error.log").read_text().strip() == "ok"
