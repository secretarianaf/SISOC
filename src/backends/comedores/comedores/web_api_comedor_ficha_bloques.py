"""Lower blocks of the comedor ficha for the web API (CO07.01): top-level keys.

Projects, from the native ``ComedorDetailView`` context, the cards of
``comedor_detail.html`` under the central block. Every value is rendered with the
template's own expression (``date`` formats in local time, ``default``), so the
JSON shows what the page shows; React draws the markup. A block the template does
not draw (or a link the user cannot use) is ``None`` / absent.

- ``certificaciones``: «Certificaciones Mensuales de Prestaciones» (read only).
"""

from django.template import Context, Template
from django.urls import reverse

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


def bloques(context, comedor):
    """The lower blocks, merged into the ficha payload."""
    return {"certificaciones": certificaciones(context, comedor)}
