"""Legajo sections delivered as React (O01-O04) instead of native HTML.

The native ``organizacion_detail.html`` renders each section through an
``{% include %}`` of a partial. The legajo API renders the template's own
``content`` block, but for every include that has a builder here the partial is
replaced by ``<div data-legajo-seccion="N"></div>`` and the builder's JSON
(computed from the same context the partial would have received, ``with``
arguments included) is appended to ``sections`` in DOM order. React mounts its
own component in each placeholder. Includes without a builder keep their native
HTML, and the native templates stay untouched.
"""

from django.template.loader_tags import IncludeNode
from django.utils.safestring import mark_safe

# Template name -> builder(context dict) -> JSON-safe dict with a ``kind``.
BUILDERS = {}
# Partials that only contain more includes: rendered natively, their includes are replaced.
CONTENEDORES = ("organizaciones/partials/legajo/sin_programa.html",)


def seccion(nombre):
    """Register the builder of the section rendered by the partial ``nombre``."""

    def registrar(funcion):
        BUILDERS[nombre] = funcion
        return funcion

    return registrar


class _Marcador:
    """Stands in for the include's template: records the section, emits its placeholder."""

    def __init__(self, builder, secciones):
        self.builder = builder
        self.secciones = secciones

    def render(self, context):
        self.secciones.append(self.builder(context.flatten()))
        return mark_safe(f'<div data-legajo-seccion="{len(self.secciones) - 1}"></div>')


def instrumentar(contexto, nodelist, secciones):
    """Prefill the include cache of ``contexto`` (a bound ``RequestContext``)."""
    for nodo in nodelist.get_nodes_by_type(IncludeNode):
        nombre = getattr(nodo.template, "var", None)
        if not isinstance(nombre, str):
            continue
        cache = contexto.render_context.dicts[0].setdefault(nodo, {})
        if nombre in BUILDERS:
            cache[(nombre,)] = _Marcador(BUILDERS[nombre], secciones)
        elif nombre in CONTENEDORES:
            plantilla = contexto.template.engine.get_template(nombre)
            cache[(nombre,)] = plantilla
            instrumentar(contexto, plantilla.nodelist, secciones)
