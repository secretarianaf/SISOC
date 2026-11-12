"""JSON projection of the native relevamiento pages for the React web API (G1 v1).

The projections print values exactly as the native templates do: dates and
numbers go through ``render_value_in_context`` (the template engine's own
rendering) and the data sections of the detail are parsed from the rendered
``relevamiento_detail_secciones.html``, the very template that still feeds the
PDF, so React never formats values nor drifts from the native labels.
"""

from html.parser import HTMLParser

from django.contrib import messages
from django.template import Context
from django.template.base import render_value_in_context
from django.template.defaultfilters import date as date_filter
from django.template.loader import render_to_string
from django.urls import reverse

from relevamientos.service import RelevamientoService

MESSAGE_LEVELS = {
    messages.DEBUG: "info",
    messages.INFO: "info",
    messages.SUCCESS: "success",
    messages.WARNING: "warning",
    messages.ERROR: "error",
}
FINALIZADOS = ("Finalizado", "Finalizado/Excepciones")
SECCIONES_TEMPLATE = "relevamiento_detail_secciones.html"


def pending_messages(request):
    """Consume queued Django messages exactly as the native page would."""
    return [
        {"message": str(m), "level": MESSAGE_LEVELS.get(m.level, "info")}
        for m in messages.get_messages(request)
    ]


def mostrar(valor, por_defecto=None):
    """``{{ valor|default_if_none:por_defecto }}``; ``None`` without default stays ``None``."""
    if valor is None:
        return por_defecto
    return render_value_in_context(valor, Context(autoescape=False))


def _forma(valor, formato, por_defecto="-"):
    """``{{ valor|date:formato|default:por_defecto }}``."""
    return date_filter(valor, formato) or por_defecto


# --- Listing -------------------------------------------------------------------


def comedor_encabezado(comedor):
    """The native heading prints ``None`` for a missing province, municipality or locality."""
    return (
        f"{mostrar(comedor['nombre'])} | {mostrar(comedor['provincia__nombre'])}, "
        f"{mostrar(comedor['municipio__nombre'])}, {mostrar(comedor['localidad__nombre'])}"
    )


def _seguimiento_item(item, comedor_id):
    return {
        "id": item["id"],
        "fecha": mostrar(item["fecha"], "Sin fecha"),
        "estado": item["estado"],
        "estado_badge": item["estado_badge"],
        "tipo": item["tipo"],
        "numero_orden": item["numero_orden"],
        "origen": item["origen"],
        "sincronizado_gestionar": bool(item["sincronizado_gestionar"]),
        "detalle_url": reverse(
            "seguimiento_detalle", args=[comedor_id, item["parent_id"], item["id"]]
        ),
    }


def relevamientos_listado(items, comedor_id):
    """Group the native flat ``relevamientos_items`` into parents with their children."""
    padres = []
    for item in items:
        if not item["is_child"]:
            padres.append(
                {
                    "id": item["id"],
                    "fecha": mostrar(item["fecha"], "Sin fecha"),
                    "estado": item["estado"],
                    "estado_badge": item["estado_badge"],
                    "numero_if": item["numero_if"],
                    "origen": item["origen"],
                    "sincronizado_gestionar": bool(item["sincronizado_gestionar"]),
                    "has_seguimiento": item["has_seguimiento"],
                    "detalle_url": reverse(
                        "relevamiento_detalle", args=[comedor_id, item["id"]]
                    ),
                    "seguimientos": [],
                }
            )
        else:
            padres[-1]["seguimientos"].append(_seguimiento_item(item, comedor_id))
    return padres


def actas_listado(actas, comedor_id):
    resultado = []
    for acta in actas:
        estado = RelevamientoService.estado_unificado(acta)
        resultado.append(
            {
                "id": acta.id,
                "fecha_hora": mostrar(acta.fecha_hora, "Sin fecha"),
                "tecnico": mostrar(acta.tecnico) or "Sin técnico",
                "origen": acta.origen,
                "prestaciones_count": len(acta.prestaciones.all()),
                "estado": estado,
                "estado_badge": RelevamientoService.badge_estado_unificado(estado),
                "a_subsanar": acta.estado_validacion == "A subsanar",
                "detalle_url": reverse(
                    "acta_complementaria_detalle", args=[comedor_id, acta.id]
                ),
                "editar_url": reverse(
                    "acta_complementaria_editar", args=[comedor_id, acta.id]
                ),
            }
        )
    return resultado


def seguimientos_pnud_listado(seguimientos, comedor_id):
    resultado = []
    for seguimiento in seguimientos:
        estado = RelevamientoService.estado_unificado(seguimiento)
        resultado.append(
            {
                "id": seguimiento.id,
                "formulario_display": seguimiento.get_formulario_display(),
                "fecha_hora": mostrar(seguimiento.fecha_hora, "Sin fecha"),
                "tecnico": mostrar(seguimiento.tecnico) or "Sin técnico",
                "origen": seguimiento.origen,
                "estado": estado,
                "estado_badge": RelevamientoService.badge_estado_unificado(estado),
                "a_subsanar": seguimiento.estado_validacion == "A subsanar",
                "detalle_url": reverse(
                    "seguimiento_pnud_detalle", args=[comedor_id, seguimiento.id]
                ),
            }
        )
    return resultado


# --- Detail --------------------------------------------------------------------


def timeline(items):
    return [
        {
            "id": item["id"],
            "step": item["step"],
            "fecha": _forma(item["fecha"], "d/m/y"),
            "estado": item["estado"] or "-",
            "card_class": item["card_class"],
            "status_class": item["status_class"],
        }
        for item in items
    ]


def seguimientos_detalle(seguimientos, comedor_id, relevamiento_id):
    resultado = []
    for seguimiento in seguimientos:
        estado = RelevamientoService.estado_unificado(seguimiento)
        args = [comedor_id, relevamiento_id, seguimiento.id]
        resultado.append(
            {
                "id": seguimiento.id,
                "numero_orden": seguimiento.numero_orden,
                "tipo": seguimiento.get_tipo_display(),
                "fecha": mostrar(seguimiento.fecha_hora, "Sin fecha"),
                "estado": estado,
                "estado_badge": RelevamientoService.badge_estado_unificado(estado),
                "estado_validacion": seguimiento.estado_validacion or "",
                "a_subsanar": seguimiento.estado_validacion == "A subsanar",
                "origen": seguimiento.origen,
                "sincronizado_gestionar": bool(seguimiento.sincronizado_gestionar),
                "detalle_url": reverse("seguimiento_detalle", args=args),
                "editar_url": reverse("seguimiento_editar", args=args),
                "eliminar_url": reverse("seguimiento_eliminar", args=args),
            }
        )
    return resultado


def adjuntos_detalle(adjuntos):
    from django.template.defaultfilters import filesizeformat  # pylint: disable=C0415

    return [
        {
            "id": adjunto.pk,
            "nombre_original": adjunto.nombre_original,
            "es_pdf": adjunto.tipo_mime == "application/pdf",
            "tamano": filesizeformat(adjunto.tamano),
            "fecha_subida": _forma(adjunto.fecha_subida, "d/m/Y H:i", ""),
            "descargar_url": reverse(
                "adjunto_descargar",
                kwargs={"comedor_pk": adjunto.comedor_id, "pk": adjunto.pk},
            ),
        }
        for adjunto in adjuntos
    ]


def pdf_detalle(relevamiento, pdf_oficial):
    return {
        "disponible": relevamiento.estado in FINALIZADOS,
        "url": reverse(
            "relevamiento_pdf", args=[relevamiento.comedor.id, relevamiento.id]
        ),
        "oficial": pdf_oficial is not None,
        "fecha_oficial": (
            _forma(pdf_oficial.fecha_actualizacion, "d/m/Y H:i", "")
            if pdf_oficial
            else None
        ),
    }


def cabecera(relevamiento, estado_visible):
    coordinador = relevamiento.coordinador
    return {
        "id": relevamiento.id,
        "comedor": {
            "id": relevamiento.comedor.id,
            "nombre": relevamiento.comedor.nombre,
        },
        "nombre_comedor": mostrar(relevamiento.datos_comedor.get("nombre")),
        "fecha_visita": mostrar(relevamiento.fecha_visita, "Sin información"),
        "estado": relevamiento.estado,
        "estado_visible": estado_visible,
        "estado_badge": RelevamientoService.badge_estado_unificado(estado_visible),
        "estado_validacion": relevamiento.estado_validacion or "",
        "a_subsanar": relevamiento.estado_validacion == "A subsanar",
        "esta_validado": relevamiento.esta_validado,
        "sin_cargar": bool(relevamiento.sin_cargar),
        "origen": relevamiento.origen,
        "sincronizado_gestionar": bool(relevamiento.sincronizado_gestionar),
        "observaciones_coordinador": relevamiento.observaciones_coordinador or "",
        "coordinador": coordinador.username if coordinador else None,
        "fecha_revision_coordinador": mostrar(relevamiento.fecha_revision_coordinador),
    }


# --- Data sections: the native partial as a whitelisted element tree -----------

TAGS = {
    "div",
    "span",
    "h3",
    "a",
    "img",
    "picture",
    "source",
    "table",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
    "button",
    "i",
    "p",
    "iframe",
}
VOID = {"img", "source"}
ATTRS = {
    "class",
    "id",
    "colspan",
    "href",
    "src",
    "srcset",
    "type",
    "alt",
    "width",
    "height",
    "border",
    "loading",
    "title",
    "aria-label",
    "aria-current",
    "aria-hidden",
    "aria-labelledby",
    "target",
    "rel",
    "style",
    "data-card-widget",
    "data-bs-target",
    "data-bs-slide",
    "data-bs-slide-to",
    "data-bs-ride",
    "role",
}


def _colapsar(partes):
    return " ".join("".join(partes).split())


class _Arbol(HTMLParser):
    """``relevamiento_detail_secciones.html`` as ``{"t", "a", "c"}`` nodes (text as strings).

    Only the tags and attributes of ``TAGS`` and ``ATTRS`` are kept; comments,
    scripts and whitespace-only text between elements are dropped, so React
    prints the same markup and classes as the native partial.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.raiz = []
        self._pila = []

    def _hijos(self):
        return self._pila[-1]["c"] if self._pila else self.raiz

    def handle_starttag(self, tag, attrs):
        if tag not in TAGS:
            return
        nodo = {
            "t": tag,
            "a": {k: v for k, v in attrs if k in ATTRS and v is not None},
            "c": [],
        }
        self._hijos().append(nodo)
        if tag not in VOID:
            self._pila.append(nodo)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag in TAGS and tag not in VOID and self._pila:
            for indice in range(len(self._pila) - 1, -1, -1):
                if self._pila[indice]["t"] == tag:
                    del self._pila[indice:]
                    break

    def handle_data(self, data):
        if not data.strip():
            return
        texto = (" " if data[:1].isspace() else "") + " ".join(data.split())
        if data[-1:].isspace():
            texto += " "
        self._hijos().append(texto)


def _titulos(nodos):
    for nodo in nodos:
        if isinstance(nodo, str):
            continue
        if nodo["t"] == "h3" and "card-title" in nodo["a"].get("class", "").split():
            yield _colapsar([_texto(nodo)])
        yield from _titulos(nodo["c"])


def _texto(nodo):
    return "".join(
        hijo if isinstance(hijo, str) else _texto(hijo) for hijo in nodo["c"]
    )


def secciones(context):
    """The native partial rendered with the detail's own context, as nodes and titles."""
    parser = _Arbol()
    parser.feed(render_to_string(SECCIONES_TEMPLATE, context))
    parser.close()
    return parser.raiz, list(_titulos(parser.raiz))


# --- Seguimientos, seguimientos PNUD and actas ---------------------------------


def defecto(valor, texto):
    """``{{ valor|default:texto }}``: the default applies to every falsy value."""
    return mostrar(valor) if valor else texto


def revision(registro):
    """The coordinator review block shared by the detail pages (N16)."""
    coordinador = registro.coordinador
    return {
        "estado_validacion": registro.estado_validacion or "",
        "a_subsanar": registro.estado_validacion == "A subsanar",
        "esta_validado": registro.esta_validado,
        "sin_cargar": bool(registro.sin_cargar),
        "observaciones_coordinador": registro.observaciones_coordinador or "",
        "coordinador": coordinador.username if coordinador else None,
        "fecha_revision_coordinador": mostrar(registro.fecha_revision_coordinador),
    }


def estado_de(registro):
    estado = RelevamientoService.estado_unificado(registro)
    return {
        "estado": estado,
        "estado_badge": RelevamientoService.badge_estado_unificado(estado),
    }


def seguimiento_resumen(seguimiento):
    return {
        "id": seguimiento.id,
        "tipo_display": seguimiento.get_tipo_display(),
        "numero_orden": seguimiento.numero_orden,
        "fecha_hora": mostrar(seguimiento.fecha_hora, "Sin información"),
        **estado_de(seguimiento),
        **revision(seguimiento),
        "origen": seguimiento.origen,
        "sincronizado_gestionar": bool(seguimiento.sincronizado_gestionar),
        "gestionar_id": defecto(seguimiento.gestionar_id, "Sin asignar"),
        "tecnico": defecto(seguimiento.tecnico, "Sin asignar"),
        "referente": defecto(seguimiento.referente, "Sin asignar"),
        "motivo_diferencia_aprobado_declarado": (
            seguimiento.motivo_diferencia_aprobado_declarado or ""
        ),
    }


def instancias_ciclo(instancias, comedor_id, relevamiento_id):
    return [
        {
            "id": instancia.id,
            "numero_orden": instancia.numero_orden,
            "tipo_display": instancia.get_tipo_display(),
            "detalle_url": reverse(
                "seguimiento_detalle", args=[comedor_id, relevamiento_id, instancia.id]
            ),
        }
        for instancia in instancias
    ]


def _imagen(valor, etiqueta):
    from core.templatetags.image_tags import (  # pylint: disable=import-outside-toplevel
        optimized_image,
    )

    parser = _Arbol()
    parser.feed(
        optimized_image(
            valor, etiqueta, css_class="img-fluid my-1 rounded object-fit-contain"
        )
    )
    parser.close()
    return parser.raiz


def bloques_seguimiento(bloques):
    """The native ``bloques``; values printed by the template engine, signatures as image nodes."""
    return [
        {
            "key": bloque["key"],
            "label": bloque["label"],
            "campos": [
                {
                    "label": campo["label"],
                    "es_imagen": campo["es_imagen"],
                    "value": (
                        _imagen(campo["value"], campo["label"])
                        if campo["es_imagen"]
                        else mostrar(campo["value"])
                    ),
                }
                for campo in bloque["campos"]
            ],
        }
        for bloque in bloques
    ]


def prestaciones_seguimiento(prestaciones, es_primer):
    filas = []
    for p in prestaciones:
        ap = (
            [mostrar(p.ap_total_efectivo, "-")]
            if es_primer
            else [mostrar(p.ap_presencial, "-"), mostrar(p.ap_vianda, "-")]
        )
        filas.append(
            [
                mostrar(p.dias_prestacion, "-"),
                mostrar(p.tipo_prestacion, "-"),
                *ap,
                mostrar(p.de_presencial, "-"),
                mostrar(p.de_vianda, "-"),
            ]
        )
    return filas


def receta_items(items):
    return [
        [
            mostrar(i.ingrediente, "-"),
            mostrar(i.unidad_medida, "-"),
            mostrar(i.cantidad_medida, "-"),
        ]
        for i in items
    ]


def pdf_seguimiento(seguimiento, pdf_oficial, comedor_id, relevamiento_id):
    return {
        "url": (
            reverse(
                "seguimiento_pdf", args=[comedor_id, relevamiento_id, seguimiento.id]
            )
            if pdf_oficial
            else None
        ),
        "fecha_oficial": (
            _forma(pdf_oficial.fecha_actualizacion, "d/m/Y H:i", "")
            if pdf_oficial
            else None
        ),
    }


def pnud_resumen(seguimiento):
    return {
        "id": seguimiento.id,
        "formulario": seguimiento.formulario,
        "formulario_display": seguimiento.get_formulario_display(),
        "fecha_hora": mostrar(seguimiento.fecha_hora, "Sin fecha"),
        "tecnico": defecto(seguimiento.tecnico, "Sin técnico"),
        "fecha_creacion": mostrar(seguimiento.fecha_creacion) or "",
        **estado_de(seguimiento),
        **revision(seguimiento),
        "origen": seguimiento.origen,
    }


def secciones_pnud(secciones_nativas):
    """``respuestas_por_seccion``: text values stay raw (the page applies ``linebreaksbr``)."""
    resultado = []
    for seccion in secciones_nativas:
        filas = []
        for fila in seccion["filas"]:
            if fila["tipo"] == "tabla":
                filas.append(
                    {
                        **fila,
                        "columnas": [str(c) for c in fila["columnas"]],
                        "filas": [[mostrar(c) or "" for c in f] for f in fila["filas"]],
                    }
                )
            else:
                filas.append({**fila, "valor": mostrar(fila["valor"]) or ""})
        resultado.append({"titulo": seccion["titulo"], "filas": filas})
    return resultado


def acta_resumen(acta):
    return {
        "id": acta.id,
        "comedor": {"id": acta.comedor.id, "nombre": acta.comedor.nombre},
        "fecha_hora": mostrar(acta.fecha_hora, "Sin fecha"),
        "tecnico": defecto(acta.tecnico, "Sin asignar"),
        "fecha_creacion": mostrar(acta.fecha_creacion) or "",
        "observaciones": acta.observaciones or "",
        "origen": acta.origen,
        **estado_de(acta),
        **revision(acta),
    }


def prestaciones_acta(prestaciones):
    return [
        [
            mostrar(p.dias_prestacion, "-"),
            mostrar(p.tipo_prestacion, "-"),
            mostrar(p.cantidad_actual, "-"),
            mostrar(p.cantidad_espera, "-"),
        ]
        for p in prestaciones
    ]
