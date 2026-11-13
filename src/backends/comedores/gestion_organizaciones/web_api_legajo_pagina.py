"""The organization legajo page as data (O05.01).

``OrganizacionDetailView`` computes the context (dupla scope, program and
section parameters, ``datos_legajo``). This module follows the control flow of
``organizacion_detail.html`` over that context and returns the page React
draws: the header, the program selector, "Datos de la Organización", the
notices, the program strip and tabs, and the ordered blocks. Each block that
is a legajo section carries the JSON of its builder (``web_api_secciones``),
called with the context and the ``with`` arguments the template passes.
Texts, defaults, localization and permissions are the template's; the
template's ``<style>`` is read from its source, so the CSS has a single owner.
"""

import re

from django.template.defaultfilters import date as formato, default, pluralize
from django.template.loader import get_template
from django.urls import reverse
from django.utils import timezone

from gestion_organizaciones.web_api_secciones import AVALES, construir

PLANTILLA = "organizacion_detail.html"
PARCIALES = "organizaciones/partials/legajo/"
REGION = PARCIALES + "region.html"
PROYECTOS = PARCIALES + "proyectos.html"
CONVENIOS = PARCIALES + "convenios.html"
FIRMANTES = PARCIALES + "firmantes.html"
COMEDORES = PARCIALES + "comedores.html"
DOCUMENTACION = PARCIALES + "documentacion.html"
RENDICIONES = PARCIALES + "rendiciones_tabla.html"
FILTRO = PARCIALES + "filtro_proyecto.html"
ESTILO = re.compile(r"<style>(.*?)</style>", re.DOTALL)


def estilos():
    """The ``<style>`` of the native legajo template (it has no template tags)."""
    encontrado = ESTILO.search(get_template(PLANTILLA).template.source)
    return encontrado.group(1) if encontrado else ""


def _texto(valor, por_defecto="-"):
    """``{{ valor|default:por_defecto }}`` for a value rendered as text."""
    return str(default(valor, por_defecto))


def _fecha(valor, formato_fecha):
    """``{{ valor|date:formato }}`` ('' when empty); aware datetimes in local time."""
    if valor and hasattr(valor, "tzinfo") and timezone.is_aware(valor):
        valor = timezone.localtime(valor)
    return formato(valor, formato_fecha)


def _editar(organizacion, ancla=""):
    return reverse("organizacion_editar", args=[organizacion.pk]) + ancla


def _encabezado(contexto):
    organizacion = contexto["organizacion"]
    gestionar = bool(contexto.get("puede_gestionar_organizaciones"))
    return {
        "name": organizacion.nombre,
        "cuit": _texto(organizacion.cuit, "Sin información"),
        "tipo": _texto(organizacion.tipo_entidad, "Sin tipo de entidad"),
        "subtipo": (
            str(organizacion.subtipo_entidad) if organizacion.subtipo_entidad else None
        ),
        "history_url": (
            reverse(
                "audittrail:log_instance",
                args=["organizaciones", "organizacion", organizacion.pk],
            )
            if contexto["ver_historial"]
            else None
        ),
        "edit_url": _editar(organizacion) if gestionar else None,
        "delete_url": (
            reverse("organizacion_eliminar", args=[organizacion.pk])
            if gestionar
            else None
        ),
    }


def _selector(contexto):
    programas, programa = contexto["programas"], contexto["programa"]
    if len(programas) > 1:
        return {
            "kind": "switch",
            "items": [
                {
                    "id": item["programa"].pk,
                    "name": item["programa"].nombre,
                    "color": item["color"],
                    "active": item["programa"] == programa,
                    "url": f"?programa={item['programa'].pk}",
                }
                for item in programas
            ],
        }
    if programa:
        return {"kind": "chip", "name": programa.nombre, "color": contexto["color"]}
    return {"kind": "none"}


def _vencimiento(organizacion):
    if organizacion.sin_vencimiento:
        texto = "Sin Vencimiento"
    else:
        texto = _texto(_fecha(organizacion.fecha_vencimiento, "d/m/Y"))
    estado = None
    if organizacion.fecha_vencimiento:
        hoy = formato(timezone.localtime(), "Y-m-d")
        vigente = _fecha(organizacion.fecha_vencimiento, "Y-m-d") >= hoy
        estado = "vigente" if vigente else "vencido"
    return {"text": texto, "state": estado}


def _datos(contexto):
    organizacion = contexto["organizacion"]
    gestionar = bool(contexto.get("puede_gestionar_organizaciones"))
    return {
        "edit_url": _editar(organizacion) if gestionar else None,
        "name": organizacion.nombre,
        "cuit": _texto(organizacion.cuit),
        "tipo": _texto(organizacion.tipo_entidad),
        "subtipo": _texto(organizacion.subtipo_entidad),
        "phone": _texto(organizacion.telefono),
        "email": _texto(organizacion.email),
        "programs": [item["programa"].nombre for item in contexto["programas"]],
        "comedores_count": contexto["comedores_count"],
        "provincia": _texto(organizacion.provincia),
        "municipio": _texto(organizacion.municipio),
        "localidad": _texto(organizacion.localidad),
        "partido": _texto(organizacion.partido),
        "domicilio": _texto(organizacion.domicilio),
        "expiry": _vencimiento(organizacion),
        "created": _texto(_fecha(organizacion.fecha_creacion, "d/m/Y H:i")),
    }


def _tabla_rendiciones(contexto, rendiciones, **extra):
    """The rendiciones table, or None for the empty text."""
    if not rendiciones:
        return None
    return construir(RENDICIONES, contexto, rendiciones=rendiciones, **extra)


def _rendiciones_generales(contexto):
    rendiciones = contexto["rendiciones_generales"]
    return {
        "kind": "rendiciones_generales",
        "total": len(rendiciones),
        "filter": construir(FILTRO, contexto),
        "table": _tabla_rendiciones(contexto, rendiciones, mostrar_linea=True),
    }


def _franja(contexto):
    programa, abordaje = contexto["programa"], contexto["es_abordaje"]
    comedores = contexto["comedores"]
    if abordaje:
        proyectos = contexto.get("proyectos") or []
        resumen = (
            f"{len(comedores)} espacio{pluralize(len(comedores))} · "
            f"{len(proyectos)} proyecto{pluralize(len(proyectos))}"
        )
    else:
        firmantes = contexto["firmantes"]
        resumen = (
            f"{len(comedores)} comedor{pluralize(len(comedores), 'es')} · "
            f"{len(firmantes)} firmante{pluralize(len(firmantes))}"
        )
    return {
        "kind": "franja",
        "color": contexto["color"],
        "label": "Abordaje Comunitario" if abordaje else "Programa",
        "name": programa.nombre,
        "summary": resumen,
    }


def _pestanas(contexto):
    programa, seccion = contexto["programa"], contexto["seccion"]
    base = f"?programa={programa.pk}&seccion="
    return {
        "kind": "tabs",
        "color": contexto["color"],
        "items": [
            {
                "label": "Información del programa",
                "url": base + "info",
                "active": seccion == "info",
            },
            {
                "label": f"Rendiciones Presentadas ({contexto['rendiciones_total']})",
                "url": base + "rendiciones",
                "active": seccion == "rendiciones",
            },
        ],
    }


def _rendiciones_del_programa(contexto):
    programa, rendiciones = contexto["programa"], contexto["rendiciones"]
    bloques = [
        {
            "kind": "rendiciones_programa",
            "color": contexto["color"],
            "title": f"Rendiciones Presentadas · {programa.nombre}",
            "total": len(rendiciones),
            "filter": construir(FILTRO, contexto),
            "table": _tabla_rendiciones(contexto, rendiciones),
        }
    ]
    otras = contexto.get("rendiciones_otras_lineas")
    if otras:
        bloques.append(
            {
                "kind": "rendiciones_otras",
                "total": len(otras),
                "table": construir(
                    RENDICIONES, contexto, rendiciones=otras, mostrar_linea=True
                ),
            }
        )
    return bloques


def _aviso_sin_linea(contexto):
    sin_linea = contexto.get("proyectos_sin_linea")
    if not sin_linea:
        return []
    cantidad = len(sin_linea)
    return [
        {
            "kind": "aviso_sin_linea",
            "count": cantidad,
            "plural": pluralize(cantidad),
            "plural_n": pluralize(cantidad, "n"),
            "plural_s": pluralize(cantidad, "s"),
            "codes": [proyecto.codigo for proyecto in sin_linea],
            "edit_url": (
                _editar(contexto["organizacion"], "#abordaje-card")
                if contexto.get("puede_gestionar_organizaciones")
                else None
            ),
        }
    ]


def _info_del_programa(contexto):
    nombre, abordaje = contexto["programa"].nombre, contexto["es_abordaje"]
    bloques = []
    if abordaje:
        bloques += _aviso_sin_linea(contexto)
        bloques.append(construir(REGION, contexto))
        bloques.append(construir(PROYECTOS, contexto, titulo="Proyectos · " + nombre))
        bloques.append(construir(CONVENIOS, contexto))
    bloques.append(construir(FIRMANTES, contexto, titulo="Firmantes · " + nombre))
    if abordaje:
        bloques.append(
            construir(
                COMEDORES,
                contexto,
                titulo="Espacios Asociados · " + nombre,
                mostrar_codigo=True,
            )
        )
    else:
        bloques.append(
            construir(COMEDORES, contexto, titulo="Comedores Asociados · " + nombre)
        )
    return bloques


def _programa(contexto):
    bloques = [_franja(contexto)]
    if contexto["es_abordaje"]:
        bloques.append(_pestanas(contexto))
    if contexto["es_abordaje"] and contexto["seccion"] == "rendiciones":
        return bloques + _rendiciones_del_programa(contexto)
    return bloques + _info_del_programa(contexto)


def _sin_programa(contexto):
    """``legajo/sin_programa.html``: signers and spaces without a (loaded) program."""
    datos, programa = contexto["sin_programa"], contexto["programa"]
    if not (datos["firmantes"] or datos["comedores"] or not programa):
        return []
    secciones = []
    if not programa or datos["firmantes"]:
        extra = {"sin_alta": True} if programa else {}
        secciones.append(
            construir(
                FIRMANTES,
                contexto,
                firmantes=datos["firmantes"],
                titulo="Firmantes",
                color="sin",
                mostrar_programa=True,
                **extra,
            )
        )
    if not programa or datos["comedores"]:
        secciones.append(
            construir(
                COMEDORES,
                contexto,
                comedores=datos["comedores"],
                titulo="Comedores",
                color="sin",
                mostrar_programa=True,
                mostrar_codigo=True,
            )
        )
    return [{"kind": "sin_programa", "sections": secciones}]


def _bloques(contexto):
    organizacion, bloques = contexto["organizacion"], []
    if contexto.get("avales"):
        bloques.append(construir(AVALES, contexto))
    if not contexto["programa"]:
        gestionar = bool(contexto.get("puede_gestionar_organizaciones"))
        bloques.append(
            {
                "kind": "sin_programas",
                "edit_url": (
                    _editar(organizacion, "#section-programas") if gestionar else None
                ),
            }
        )
    sin_abordaje = contexto.get("abordaje_sin_programa")
    if sin_abordaje:
        bloques.append({"kind": "aviso_abordaje"})
        bloques.append(
            construir(
                REGION,
                contexto,
                territoriales_sin_proyecto=sin_abordaje["territoriales_sin_proyecto"],
            )
        )
        bloques.append(
            construir(
                PROYECTOS,
                contexto,
                proyectos=sin_abordaje["proyectos"],
                titulo="Proyectos",
                color="otro",
            )
        )
    if not contexto["tiene_abordaje"]:
        bloques.append(_rendiciones_generales(contexto))
    if contexto["programa"]:
        bloques += _programa(contexto)
    if contexto.get("muestra_documentacion"):
        bloques.append(construir(DOCUMENTACION, contexto))
    return bloques + _sin_programa(contexto)


def pagina(contexto):
    """The legajo page for the ``OrganizacionDetailView`` context plus ``ver_historial``."""
    return {
        "title": f"Organización: {contexto['organizacion'].nombre}",
        "css": estilos(),
        "header": _encabezado(contexto),
        "selector": _selector(contexto),
        "datos": _datos(contexto),
        "blocks": _bloques(contexto),
    }
