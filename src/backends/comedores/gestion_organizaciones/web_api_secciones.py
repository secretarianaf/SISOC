"""Legajo sections delivered as React (O01-O04) instead of native HTML.

The native ``organizacion_detail.html`` renders each section through an
``{% include %}`` of a partial. The legajo API renders the template's own
``content`` block, but for every include that has a builder here the partial is
replaced by ``<div data-legajo-seccion="N"></div>`` and the builder's JSON
(computed from the same context the partial would have received, ``with``
arguments included) is appended to ``sections`` in DOM order. React mounts its
own component in each placeholder. Includes without a builder keep their native
HTML, and the native templates stay untouched.

Some blocks of the legajo are inline markup, not an include (the "Avales"
table is an ``{% if avales %}`` block). ``seccion_en_linea`` registers a
builder for such an ``{% if %}`` block, recognised by the variable it tests:
the node is wrapped once, in memory, by a node that renders exactly as before
unless a legajo API request is collecting sections, in which case a non-empty
block becomes a placeholder plus the builder's JSON. The template file and the
native pages are unchanged.
"""

from django.template.base import Node, NodeList
from django.template.defaulttags import IfNode
from django.template.loader_tags import IncludeNode
from django.utils.safestring import mark_safe

# Template name -> builder(context dict) -> JSON-safe dict with a ``kind``.
BUILDERS = {}
# Partials that only contain more includes: rendered natively, their includes are replaced.
CONTENEDORES = ("organizaciones/partials/legajo/sin_programa.html",)
# Variable tested by an inline ``{% if %}`` block -> builder(context dict).
EN_LINEA = {}
# Key of the sections list inside ``render_context.dicts[0]`` while the API collects.
_RECOLECTOR = "legajo_secciones_recolector"


def seccion(nombre):
    """Register the builder of the section rendered by the partial ``nombre``."""

    def registrar(funcion):
        BUILDERS[nombre] = funcion
        return funcion

    return registrar


def seccion_en_linea(variable):
    """Register the builder of the inline ``{% if <variable> %}`` block of the legajo."""

    def registrar(funcion):
        EN_LINEA[variable] = funcion
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


class _BloqueEnLinea(Node):
    """Wraps an inline ``{% if %}`` block; native rendering is delegated untouched."""

    def __init__(self, original, builder):
        super().__init__()
        self.original = original
        self.builder = builder

    def render(self, context):
        html = self.original.render(context)
        secciones = context.render_context.dicts[0].get(_RECOLECTOR)
        if secciones is None or not html.strip():
            return html
        secciones.append(self.builder(context.flatten()))
        return mark_safe(f'<div data-legajo-seccion="{len(secciones) - 1}"></div>')


def _variable(nodo):
    condicion = nodo.conditions_nodelists[0][0]
    valor = getattr(getattr(condicion, "value", None), "var", None)
    return getattr(valor, "var", None)


def _listas(nodo):
    if isinstance(nodo, IfNode):
        yield from (lista for _, lista in nodo.conditions_nodelists)
    for valor in vars(nodo).values():
        if isinstance(valor, NodeList):
            yield valor


def _envolver_en_linea(nodelist):
    for indice, nodo in enumerate(nodelist):
        if isinstance(nodo, _BloqueEnLinea):
            continue
        if isinstance(nodo, IfNode) and _variable(nodo) in EN_LINEA:
            nodelist[indice] = _BloqueEnLinea(nodo, EN_LINEA[_variable(nodo)])
            continue
        for lista in _listas(nodo):
            _envolver_en_linea(lista)


def instrumentar_en_linea(contexto, nodelist, secciones):
    """Wrap the inline blocks of ``nodelist`` and start collecting into ``secciones``."""
    _envolver_en_linea(nodelist)
    contexto.render_context.dicts[0][_RECOLECTOR] = secciones
