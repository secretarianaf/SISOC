import logging
import os
import stat
from datetime import datetime
from unittest.mock import patch

from core.utils import DailyFileHandler


def test_daily_file_handler_creates_group_writable_log_path(tmp_path):
    previous_umask = os.umask(0o022)
    try:
        with patch("core.utils.timezone.localtime", return_value=datetime(2026, 7, 14)):
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
    with patch("core.utils.timezone.localtime", return_value=datetime(2026, 10, 15)):
        handler = DailyFileHandler(tmp_path / "error.log")
        handler.handle(logging.makeLogRecord({"msg": "del 15", "levelno": 40}))
    with patch("core.utils.timezone.localtime", return_value=datetime(2026, 10, 21)):
        handler.handle(logging.makeLogRecord({"msg": "del 21", "levelno": 40}))
    handler.close()

    assert (tmp_path / "2026-10-15" / "error.log").read_text().strip() == "del 15"
    assert (tmp_path / "2026-10-21" / "error.log").read_text().strip() == "del 21"
    for ruta in (tmp_path / "2026-10-21", tmp_path / "2026-10-21" / "error.log"):
        assert stat.S_IMODE(ruta.stat().st_mode) & stat.S_IWGRP
