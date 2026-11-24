"""JSON projections of the native PAS back-office contexts (``pas.web_api_views``).

Each function reads what the native view put in its template context and
returns the same values the template prints: dates with the template formats
(``d/m/Y``, ``d/m/Y H:i``) in local time, empty values as ``""`` so the screen
applies the same ``default`` texts, and URLs from ``reverse``. Nothing here
queries or recalculates domain data.
"""

from datetime import datetime
from html import unescape

from django.template import Context, Template
from django.urls import reverse
from django.utils import dateformat, timezone

AREA_FIELDS = ("key", "number", "title", "subtitle")
WORKFLOW_FIELDS = (*AREA_FIELDS, "url", "active", "source_status")

# ``components/pagination.html`` link prefix with ``query=query`` (persona_list.html).
_PAGINATION_PREFIX = Template(
    "{% if query %}busqueda={{ query|urlencode }}&{% endif %}"
    "{% for key, value in request.GET.items %}{% if key != 'page' and "
    "key != 'busqueda' %}{{ key }}={{ value|urlencode }}&{% endif %}{% endfor %}"
)


def _text(value):
    return "" if value is None else str(value)


def _local(value, fmt):
    if not value:
        return ""
    if isinstance(value, datetime) and timezone.is_aware(value):
        value = timezone.localtime(value)
    return dateformat.format(value, fmt)


def fecha_hora(value):
    """``value|date:"d/m/Y H:i"``."""
    return _local(value, "d/m/Y H:i")


def fecha(value):
    """``value|date:"d/m/Y"``."""
    return _local(value, "d/m/Y")


def fecha_iso(value):
    """``value|date:'c'`` (``<time datetime>`` of the history)."""
    return _local(value, "c")


def area(item):
    return {campo: item[campo] for campo in AREA_FIELDS}


def workflow(areas):
    """``pas/includes/workflow_nav.html`` cards, as ``_pas_areas`` built them."""
    return [{campo: item[campo] for campo in WORKFLOW_FIELDS} for item in areas]


def estado(item):
    return {"id": item.pk, "nombre": item.nombre, "css_class": item.css_class}


def aviso(item):
    return {"codigo": item.codigo, "descripcion": item.descripcion}


def persona_formacion(persona):
    return {
        "id": persona.pk,
        "apellidos": persona.apellidos,
        "nombres": persona.nombres,
        "puntos_formacion": persona.puntos_formacion,
        "estado_formacion": persona.estado_formacion,
    }


def resumen_formacion(resumen):
    if resumen is None:
        return None
    data = {
        campo: resumen[campo]
        for campo in (
            "puntos",
            "objetivo",
            "excedente",
            "cursos_completados",
            "total_cursos",
            "estado",
            "titulo",
            "detalle",
            "duracion_dias",
            "dia_actual",
        )
    }
    data.update(
        {
            "inicio_base": fecha(resumen["inicio_base"]),
            "inicio_actual": fecha(resumen["inicio_actual"]),
            "fin_actual": fecha(resumen["fin_actual"]),
        }
    )
    return data


def formacion(item):
    """One row of the courses table (the source has no rows yet)."""
    return {
        "curso": _text(item.get("curso")),
        "fuente": _text(item.get("fuente")),
        "inicio": fecha(item.get("inicio")),
        "fin": fecha(item.get("fin")),
        "progreso": _text(item.get("progreso")),
        "puntos": _text(item.get("puntos")),
        "estado": _text(item.get("estado")),
        "estado_codigo": _text(item.get("estado_codigo")),
        "certificado_url": _text(item.get("certificado_url")),
    }


def persona_listado(persona):
    return {
        "id": persona.pk,
        "apellidos": persona.apellidos,
        "nombres": persona.nombres,
        "dni": persona.dni,
        "id_persona": persona.id_persona,
        "cuit": persona.cuit,
        "provincia": _text(persona.provincia.nombre if persona.provincia else ""),
        "municipio": _text(persona.municipio.nombre if persona.municipio else ""),
        "estado": {
            "nombre": persona.estado.nombre,
            "css_class": persona.estado.css_class,
        },
        "avisos": [item.codigo for item in persona.avisos.all()],
    }


def pagina_listado(context, request):
    """Pager of ``components/pagination.html`` over ``NoCountPaginator``."""
    page = context["page_obj"]
    return {
        "page": page.number,
        "page_size": page.paginator.per_page,
        "has_previous": page.has_previous(),
        "has_next": page.has_next(),
        "previous": page.previous_page_number() if page.has_previous() else None,
        "next": page.next_page_number() if page.has_next() else None,
        "is_paginated": bool(context["is_paginated"]),
        "page_range": [
            "…" if numero in ("...", "…") else numero
            for numero in context.get("page_range") or []
        ],
        "count": page.paginator.count,
        "query_prefix": unescape(
            _PAGINATION_PREFIX.render(
                Context({"query": context["query"], "request": request})
            )
        ),
    }


def ddjj_url(declaracion):
    return reverse("pas_ddjj_descargar", kwargs={"pk": declaracion.pk})


def _respuestas(declaracion):
    filas = []
    respuestas = (
        declaracion.respuestas if isinstance(declaracion.respuestas, dict) else {}
    )
    for clave, respuesta in respuestas.items():
        if clave == "firma_nombre_completo":
            continue
        respuesta = respuesta if isinstance(respuesta, dict) else {}
        filas.append(
            {
                "clave": clave,
                "etiqueta": _text(respuesta.get("etiqueta", "")),
                "respuesta": _text(respuesta.get("respuesta", "")),
            }
        )
    return filas


def ddjj(declaraciones, seleccionada):
    """Tab «Declaración Jurada»: every version (model order) and the chosen one.

    Only id, version, date, answers and the native download route: never the
    legal text, the invitation, its token or the stored file path.
    """
    return {
        "declaraciones": [
            {
                "id": item.pk,
                "version": item.version,
                "presentada": fecha_hora(item.presentada),
                "es_ultima": index == 0,
            }
            for index, item in enumerate(declaraciones)
        ],
        "seleccionada": (
            {
                "id": seleccionada.pk,
                "version": seleccionada.version,
                "presentada": fecha_hora(seleccionada.presentada),
                "download_url": ddjj_url(seleccionada),
                "respuestas": _respuestas(seleccionada),
            }
            if seleccionada
            else None
        ),
        "vigente_download_url": ddjj_url(declaraciones[0]) if declaraciones else None,
    }


def persona_panel(persona):
    vigente = persona.declaracion_jurada_vigente
    return {
        "id": persona.pk,
        "apellidos": persona.apellidos,
        "nombres": persona.nombres,
        "dni": persona.dni,
        "id_persona": persona.id_persona,
        "cuit": persona.cuit,
        "genero": persona.genero,
        "provincia": _text(persona.provincia.nombre),
        "municipio": _text(persona.municipio.nombre),
        "domicilio": persona.domicilio,
        "correo_electronico": persona.correo_electronico,
        "telefono_celular": persona.telefono_celular,
        "estado": estado(persona.estado),
        "avisos": [aviso(item) for item in persona.avisos.all()],
        "fecha_creacion": fecha_hora(persona.fecha_creacion),
        "fecha_actualizacion": fecha_hora(persona.fecha_actualizacion),
        "ddjj_vigente": (
            {"id": vigente.pk, "download_url": ddjj_url(vigente)} if vigente else None
        ),
    }


def persona_mini(item):
    return {
        "id": item.pk,
        "apellidos": item.apellidos,
        "nombres": item.nombres,
        "cuit": item.cuit,
        "dni": item.dni,
        "provincia": _text(item.provincia.nombre if item.provincia else ""),
        "estado": {"nombre": item.estado.nombre, "css_class": item.estado.css_class},
        "mostrar_tag_ddjj": bool(item.mostrar_tag_ddjj),
        "mostrar_tag_fch": bool(item.mostrar_tag_fch),
    }


def _usuario(user):
    if user is None:
        return None
    return user.get_full_name() or user.username


def evento(item):
    base = {
        "tipo": item["tipo"],
        "fecha": fecha_hora(item["fecha"]),
        "fecha_iso": fecha_iso(item["fecha"]),
    }
    objeto = item["objeto"]
    if item["tipo"] == "ddjj":
        base.update({"id": objeto.pk, "version": objeto.version})
    else:
        base.update(
            {
                "estado": objeto.estado_nuevo.nombre,
                "avisos": [aviso(a) for a in objeto.avisos_nuevos.all()],
                "usuario": _usuario(objeto.usuario),
            }
        )
    return base
