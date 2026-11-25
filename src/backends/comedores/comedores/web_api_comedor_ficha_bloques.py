"""Lower blocks of the comedor ficha for the web API (CO07.01): top-level keys.

Projects, from the native ``ComedorDetailView`` context, the cards of
``comedor_detail.html`` under the central block. Every value is rendered with the
template's own expression (``date`` formats in local time, ``default``), so the
JSON shows what the page shows; React draws the markup. A block the template does
not draw (or a link the user cannot use) is ``None`` / absent.

- ``certificaciones``: «Certificaciones Mensuales de Prestaciones» (read only).
- ``colaboradores``: «Colaboradores del espacio». Each action carries the condition the
  template checks (add / change / delete permission, an inactive colaborador): a control
  the user cannot use is ``None``, not disabled.
- ``interacciones``: the data of the «Historial de interacciones» chart.
- ``capacitaciones``: the «Capacitaciones» table (``None`` when the page hides it).
"""

import json

from django.template import Context, Template
from django.urls import reverse

from comedores.web_api_comedor_ficha_relaciones import relaciones
from core.templatetags.custom_filters import has_perm_code

LOAD = "{% load custom_filters %}"


def _render(source, **context):
    return " ".join(Template(LOAD + source).render(Context(context)).split())


def _certificacion(certificacion, comedor):
    def valor(expresion):
        return _render(expresion, c=certificacion)

    return {
        "id": certificacion.pk,
        "periodo": valor('{{ c.periodo|date:"m/Y" }}'),
        "usuario": (
            valor("{{ c.usuario.get_full_name|default:c.usuario.username }}")
            if certificacion.usuario
            else "-"
        ),
        "conforme": bool(certificacion.conforme),
        "creado": valor('{{ c.creado|date:"d/m/Y H:i" }}'),
        "pdf": (
            reverse(
                "descargar_certificacion_prestaciones_web",
                args=[comedor.pk, certificacion.pk],
            )
            if certificacion.certificacion_pdf
            else None
        ),
    }


def certificaciones(context, comedor):
    """The certifications card: the six latest and the link to the whole history."""
    return {
        "historial": reverse(
            "certificaciones_prestaciones_historial", args=[comedor.pk]
        ),
        "items": [
            _certificacion(c, comedor)
            for c in context.get("certificaciones_prestaciones") or []
        ],
    }


def _colaborador(colaborador, comedor, user):
    def valor(expresion):
        return _render(expresion, c=colaborador)

    baja = bool(colaborador.fecha_baja)
    return {
        "id": colaborador.pk,
        "nombre": valor('{{ c.apellido|default:"-" }}, {{ c.nombre|default:"-" }}'),
        "dni": valor('{{ c.dni|default:"-" }}'),
        "cuil": valor('{{ c.cuil_cuit|default:"-" }}'),
        "sexo": valor('{{ c.sexo_display|default:"-" }}'),
        "genero": valor('{{ c.get_genero_display|default:"-" }}'),
        "telefono": valor(
            "{% if c.codigo_telefono or c.numero_telefono %}"
            '{{ c.codigo_telefono|default:"-" }} {{ c.numero_telefono|default:"" }}'
            "{% else %}-{% endif %}"
        ),
        "alta": valor('{{ c.fecha_alta|date:"d/m/Y"|default:"-" }}'),
        "baja": valor('{{ c.fecha_baja|date:"d/m/Y"|default:"-" }}'),
        "actividades": valor(
            "{% for a in c.actividades.all %}{{ a.nombre }} "
            "{% if not forloop.last %},{% endif %} {% empty %}-{% endfor %}"
        ),
        "editar": (
            reverse("colaborador_espacio_editar", args=[comedor.pk, colaborador.pk])
            if not baja and has_perm_code(user, "comedores.change_colaboradorespacio")
            else None
        ),
        "eliminar": (
            {
                # The colaboradores API (CO03.01) runs the native soft delete.
                "url": reverse(
                    "colaboradores_web_eliminar", args=[comedor.pk, colaborador.pk]
                ),
                "deshabilitado": baja,
            }
            if has_perm_code(user, "comedores.delete_colaboradorespacio")
            else None
        ),
    }


def colaboradores(context, comedor, user):
    """The colaboradores card: rows, the «Agregar» link and the result count."""
    items = list(context.get("colaboradores_espacio") or [])
    return {
        "agregar": (
            reverse("colaborador_espacio_crear", args=[comedor.pk])
            if context.get("permite_alta_colaboradores")
            and has_perm_code(user, "comedores.add_colaboradorespacio")
            else None
        ),
        "items": [_colaborador(c, comedor, user) for c in items],
        "resultados": _render(
            "Se encontraron {{ n }} resultado{{ n|pluralize }}.", n=len(items)
        ),
    }


def interacciones(context):
    """Labels and values of the chart (the context holds them as JSON text)."""
    return {
        "labels": json.loads(context.get("interacciones_labels") or "[]"),
        "values": json.loads(context.get("interacciones_values") or "[]"),
    }


def capacitaciones(context, comedor):
    """The capacitaciones table; ``None`` when the template does not draw it."""
    if not context.get("show_capacitaciones_certificados"):
        return None
    return {
        "items": [
            {
                "id": cert["id"],
                "capacitacion": cert["capacitacion_label"],
                "estado": cert["estado"],
                "archivo": cert["archivo_url"],
                "observacion": _render('{{ c.observacion|default:"-" }}', c=cert),
                "revisar": reverse(
                    "comedores_web_capacitacion_estado", args=[comedor.pk, cert["id"]]
                ),
            }
            for cert in context.get("capacitaciones_certificados") or []
        ]
    }


def bloques(context, comedor, user):
    """The lower blocks, merged into the ficha payload."""
    return {
        **relaciones(context, comedor),
        "certificaciones": certificaciones(context, comedor),
        "colaboradores": colaboradores(context, comedor, user),
        "interacciones": interacciones(context),
        "capacitaciones": capacitaciones(context, comedor),
    }
