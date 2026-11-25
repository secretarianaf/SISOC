"""Registry of the legajo sections delivered as React (O01-O05).

Each section of the legajo (convenio, documentación, firmantes, avales,
rendiciones, región, proyectos, comedores) has a builder that receives the
context its native partial would receive (``with`` arguments included) and
returns the JSON React draws. ``web_api_legajo_pagina`` calls them while it
composes the page; the native templates stay untouched.
"""

# Partial name (or ``inline/<name>`` for blocks that are not a partial) -> builder(context dict).
BUILDERS = {}
AVALES = "inline/avales"


def seccion(nombre):
    """Register the builder of the section rendered by the partial ``nombre``."""

    def registrar(funcion):
        BUILDERS[nombre] = funcion
        return funcion

    return registrar


def construir(nombre, contexto, **extra):
    """Run the builder of ``nombre`` with ``contexto`` plus the ``with`` arguments ``extra``."""
    return BUILDERS[nombre]({**contexto, **extra})
