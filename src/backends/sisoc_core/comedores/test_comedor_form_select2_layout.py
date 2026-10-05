"""Regresiones visuales del Select2 del formulario de comedores."""

from pathlib import Path


# El JS es de comedores; el CSS lo comparten varios verticales (kernel).
STATIC_DIR = Path(__file__).resolve().parent / "static" / "custom"
KERNEL_STATIC_DIR = Path(__file__).resolve().parents[2] / "kernel" / "static" / "custom"


def test_select2_no_modifica_overflow_del_layout_principal():
    javascript = (STATIC_DIR / "js" / "comedorFormModerno.js").read_text(
        encoding="utf-8"
    )
    stylesheet = (KERNEL_STATIC_DIR / "css" / "comedorFormModerno.css").read_text(
        encoding="utf-8"
    )

    assert "appContent.style.overflow" not in javascript
    assert "document.body.style.overflow" not in javascript
    assert "document.documentElement.style.overflow" not in javascript
    assert "classList.add('select2-container--open')" not in javascript
    assert "body.select2-container--open" not in stylesheet


def test_select2_enfoca_buscador_sin_desplazar_la_pagina():
    javascript = (STATIC_DIR / "js" / "comedorFormModerno.js").read_text(
        encoding="utf-8"
    )

    assert "field.focus({ preventScroll: true });" in javascript
