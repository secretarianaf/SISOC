"""Nómina card, interventions and observations of the comedor ficha web API (CO07.01).

Top-level keys of ``GET /api/web/comedores/comedores/<pk>/``, projected from the native
``ComedorDetailView`` context:

- ``nomina``: the «Nómina» card (the metric boxes, «Ver nómina» and the native import form).
- ``intervenciones`` / ``observaciones``: the tabs card with the ``components/data_table.html``
  tables (rows, pager, convenio buttons) and the data of the two creation modals. The modals post
  to the existing web APIs of the native create views (``intervenciones_web_crear`` and
  ``observaciones_web_crear``), so validation and persistence are the native ones.
"""

import re
from html import unescape

from django.core.paginator import Paginator
from django.template import Context, Template
from django.urls import reverse
from django.utils.html import strip_tags

LOAD = "{% load custom_filters %}"
_LINK = re.compile(
    r"<a\s+href=\"([^\"]*)\"\s+class=\"([^\"]*)\"([^>]*)>(.*?)</a>", re.S
)
_BADGE = re.compile(r"<span class=\"badge ([^\"]*)\">(.*?)</span>", re.S)


def _render(source, **context):
    return " ".join(Template(LOAD + source).render(Context(context)).split())


def _celda(contenido):
    """A ``data_table`` cell: plain text, a badge or the action links of the native row."""
    html = str(contenido)
    enlaces = _LINK.findall(html)
    if enlaces:
        return {
            "acciones": [
                {
                    "url": url,
                    "clase": clase,
                    "nueva_ventana": "target=" in resto,
                    "label": unescape(strip_tags(label)).strip(),
                }
                for url, clase, resto, label in enlaces
            ]
        }
    insignia = _BADGE.search(html)
    if insignia:
        return {"insignia": insignia.group(1), "texto": unescape(insignia.group(2))}
    return {"texto": unescape(html)}


def _paginas(pagina, rango, param):
    """The pager links of ``components/pagination.html`` (a relative query, as the page builds it)."""
    if not pagina.has_other_pages():
        return None
    paginas = []
    for i in rango:
        if i in (Paginator.ELLIPSIS, "...", "…"):
            paginas.append({"ellipsis": True})
        else:
            paginas.append({"numero": i, "activa": i == pagina.number})
    return {
        "param": param,
        "anterior": pagina.previous_page_number() if pagina.has_previous() else None,
        "siguiente": pagina.next_page_number() if pagina.has_next() else None,
        "paginas": paginas,
    }


def _tabla(context, prefijo, param):
    pagina = context[f"{prefijo}_page_obj"]
    return {
        "encabezados": [h["title"] for h in context[f"{prefijo}_headers"]],
        "filas": [
            [_celda(c["content"]) for c in item["cells"]]
            for item in context[f"{prefijo}_items"]
        ],
        "paginacion": _paginas(pagina, context[f"{prefijo}_page_range"], param),
        "resultados": pagina.paginator.count,
    }


def _opciones(campo):
    return [{"value": str(v), "label": str(label)} for v, label in campo.field.choices]


def _select(form, nombre):
    campo = form[nombre]
    return {
        "id": campo.id_for_label,
        "label": str(campo.label),
        "required": campo.field.required,
        "options": _opciones(campo),
    }


def _intervenciones(context, comedor):
    form = context["intervencion_form"]
    admision_id = context.get("intervenciones_admision_id")
    ficha = reverse("comedor_detalle", kwargs={"pk": comedor.pk})
    tabla = _tabla(context, "intervenciones", "intervenciones_page")
    return {
        **tabla,
        "convenios": [
            {
                "id": a.pk,
                "texto": _render(
                    "{% if a.acompanamiento.nro_convenio %}{{ a.acompanamiento.nro_convenio }}"
                    "{% else %}Admisión #{{ a.id }}{% endif %}",
                    a=a,
                ),
                "cerrada": not a.activa,
                "seleccionada": a.pk == admision_id,
            }
            for a in context.get("intervenciones_admisiones_disponibles") or []
        ],
        "modal": {
            "crear": reverse("intervenciones_web_crear", args=[comedor.pk]),
            # The native create page: where a rejected post re-renders the form with its errors.
            "formulario": reverse("comedor_intervencion_crear", args=[comedor.pk]),
            "subestados": reverse("intervenciones_web_subestados"),
            "next": f"{ficha}?admision_id={admision_id}" if admision_id else ficha,
            "admision_id": admision_id,
            "fecha": {
                "id": form["fecha"].id_for_label,
                "label": str(form["fecha"].label),
                "required": form["fecha"].field.required,
            },
            "tipo_intervencion": _select(form, "tipo_intervencion"),
            "subintervencion": _select(form, "subintervencion"),
            "destinatario": _select(form, "destinatario"),
            "forma_contacto": _select(form, "forma_contacto"),
            "observaciones": {
                "id": form["observaciones"].id_for_label,
                "label": str(form["observaciones"].label),
                "required": form["observaciones"].field.required,
            },
            "tiene_documentacion": {
                "id": form["tiene_documentacion"].id_for_label,
                "label": str(form["tiene_documentacion"].label),
            },
            "documentacion": {
                "id": form["documentacion"].id_for_label,
                "label": str(form["documentacion"].label),
            },
        },
    }


def _observaciones(context, comedor):
    form = context["observacion_form"]
    campo = form["observacion"]
    attrs = campo.field.widget.attrs
    return {
        **_tabla(context, "observaciones", "observaciones_page"),
        "modal": {
            "crear": reverse("observaciones_web_crear", args=[comedor.pk]),
            "formulario": reverse("observacion_crear", args=[comedor.pk]),
            "next": reverse("comedor_detalle", kwargs={"pk": comedor.pk}),
            "campo": {
                "id": campo.id_for_label,
                "label": str(campo.label),
                "required": campo.field.required,
                "rows": int(attrs.get("rows", 4)),
                "placeholder": str(attrs.get("placeholder", "")),
            },
        },
    }


def _nomina(context, comedor):
    admision_id = context.get("selected_admision_id")
    programa = comedor.programa
    directa = bool(programa and not programa.usa_admision_para_nomina)
    ver = None
    if admision_id:
        ver = reverse(
            "nomina_ver", kwargs={"pk": comedor.pk, "admision_pk": admision_id}
        )
    elif directa:
        ver = reverse("nomina_directa_ver", args=[comedor.pk])

    def n(clave):
        return _render("{{ v|default:0 }}", v=context.get(clave))

    return {
        "ver": ver,
        "pendiente": bool(admision_id and context.get("nomina_total") == 0),
        "importar": (
            reverse(
                "nomina_importar", kwargs={"pk": comedor.pk, "admision_pk": admision_id}
            )
            if admision_id
            else None
        ),
        "directa": bool(not admision_id and directa),
        "cifras": {
            "asistentes": n("nomina_asistentes"),
            "hombres": n("nomina_hombres"),
            "mujeres": n("nomina_mujeres"),
            "menores": n("nomina_menores"),
            "espera": n("nomina_espera"),
            "bajas": n("nomina_bajas"),
        },
    }


def relaciones(context, comedor):
    """The ``nomina``, ``intervenciones`` and ``observaciones`` keys."""
    return {
        "nomina": _nomina(context, comedor),
        "intervenciones": _intervenciones(context, comedor),
        "observaciones": _observaciones(context, comedor),
    }
