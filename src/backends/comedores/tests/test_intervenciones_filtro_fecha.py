"""Filtro por fecha del detalle de intervenciones sin ``__date`` (#2750)."""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from intervenciones.views import _filtrar_por_dia

ARGENTINA = ZoneInfo("America/Argentina/Buenos_Aires")


def test_filtra_por_el_dia_local_con_un_rango(mocker):
    intervenciones = mocker.Mock()

    resultado = _filtrar_por_dia(intervenciones, "2026-04-30")

    assert resultado is intervenciones.filter.return_value
    intervenciones.filter.assert_called_once_with(
        fecha__gte=datetime(2026, 4, 30, 0, 0, tzinfo=ARGENTINA),
        fecha__lt=datetime(2026, 5, 1, 0, 0, tzinfo=ARGENTINA),
    )


@pytest.mark.parametrize("fecha_texto", [None, "", "30/04/2026", "2026-02-30"])
def test_fecha_vacia_o_invalida_no_filtra(mocker, fecha_texto):
    intervenciones = mocker.Mock()

    assert _filtrar_por_dia(intervenciones, fecha_texto) is intervenciones
    intervenciones.filter.assert_not_called()
