"""Legajo sections of the organization data blocks (O05.01): región, proyectos, comedores.

Each builder receives the context the native partial would have received
(``with`` arguments included) and returns the JSON React draws in the
partial's placeholder (see ``web_api_secciones``). Texts, defaults and
permissions are the partial's own; nothing is recomputed.
"""

from django.urls import reverse

from gestion_organizaciones.templatetags.organizaciones_tags import (
    etiqueta_territorial,
)
from gestion_organizaciones.web_api_secciones import seccion

EDITAR_ABORDAJE = "#abordaje-card"


def _editar(organizacion):
    return reverse("organizacion_editar", args=[organizacion.pk]) + EDITAR_ABORDAJE


@seccion("organizaciones/partials/legajo/region.html")
def seccion_region(contexto):
    """``legajo/region.html``: región and subzona, plus the old territoriales."""
    organizacion = contexto["organizacion"]
    gestionar = bool(contexto.get("puede_gestionar_organizaciones"))
    con_datos = bool(
        organizacion.region_abordaje_id or organizacion.subzona_abordaje_id
    )
    return {
        "kind": "region",
        "can_manage": gestionar,
        "edit_url": _editar(organizacion) if gestionar else None,
        "has_data": con_datos,
        "region": str(organizacion.region_abordaje or "-"),
        "subzona": str(organizacion.subzona_abordaje or "-"),
        "territorials": [
            etiqueta_territorial(t)
            for t in contexto.get("territoriales_sin_proyecto") or []
        ],
    }


@seccion("organizaciones/partials/legajo/proyectos.html")
def seccion_proyectos(contexto):
    """``legajo/proyectos.html``: the active projects and their territoriales."""
    organizacion = contexto["organizacion"]
    gestionar = bool(contexto.get("puede_gestionar_organizaciones"))
    proyectos = list(contexto.get("proyectos") or [])
    return {
        "kind": "proyectos",
        "title": contexto.get("titulo") or "",
        "color": contexto.get("color") or "otro",
        "can_manage": gestionar,
        "edit_url": _editar(organizacion) if gestionar else None,
        "total": len(proyectos),
        "rows": [
            {
                "id": proyecto.pk,
                "code": proyecto.codigo,
                "territorials": [
                    etiqueta_territorial(t) for t in proyecto.territoriales.all()
                ],
            }
            for proyecto in proyectos
        ],
    }


def _nombre(objeto):
    return objeto.nombre if objeto else None


def _validacion(comedor):
    if comedor.estado_validacion == "Validado":
        return "ok"
    if comedor.estado_validacion == "No Validado":
        return "no"
    return "pending"


@seccion("organizaciones/partials/legajo/comedores.html")
def seccion_comedores(contexto):
    """``legajo/comedores.html``: the spaces (comedores) of the program or of "sin programa"."""
    comedores = list(contexto.get("comedores") or [])
    return {
        "kind": "comedores",
        "title": contexto.get("titulo") or "",
        "color": contexto.get("color") or "otro",
        "show_code": bool(contexto.get("mostrar_codigo")),
        "show_program": bool(contexto.get("mostrar_programa")),
        "total": len(comedores),
        "rows": [
            {
                "id": comedor.pk,
                "name": comedor.nombre,
                "url": reverse("comedor_detalle", args=[comedor.pk]),
                "caritas": bool(comedor.es_caritas),
                "type": _nombre(comedor.tipocomedor) or "-",
                "code": (
                    comedor.proyecto.codigo
                    if comedor.proyecto
                    else comedor.codigo_de_proyecto or None
                ),
                "program": _nombre(comedor.programa) or "-",
                "province": _nombre(comedor.provincia) or "-",
                "municipality": _nombre(comedor.municipio) or "-",
                "locality": _nombre(comedor.localidad) or "-",
                "address": f"{comedor.calle or '-'} {comedor.numero or 'S/N'}",
                "referent": (
                    f"{comedor.referente.nombre} {comedor.referente.apellido}"
                    if comedor.referente
                    else None
                ),
                "validation": _validacion(comedor),
            }
            for comedor in comedores
        ],
    }
