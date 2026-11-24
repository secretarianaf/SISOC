"""Web API (G1 v1) del reporte de inscriptos y asistencias de VAT (V08.01).

``GET /api/web/vat/reportes/inscripciones-asistencias/`` corre
``ReporteInscriptosAsistenciasView`` (filtros, resumen, grupos y detalle nominal) y
proyecta su contexto. Solo lectura: las exportaciones (``?export=csv|xlsx|detalle_csv|
detalle_xlsx``) siguen siendo las descargas nativas, sin pasar por esta API. Acceso: el
decorador de la ruta nativa (``view_inscripcion``, ``view_comisioncurso`` o
``view_centro``); el alcance por usuario lo aplica el servicio del reporte.
"""

from django.urls import reverse
from rest_framework.response import Response

from VAT.services.reportes_inscripciones_asistencia import (
    build_reporte_inscripciones_asistencia,
)
from VAT.views.reporte import ReporteInscriptosAsistenciasView
from VAT.web_api_common import VatNativeReadView, mensajes_pendientes, texto

_VALOR = "{{ v }}"
_ENTERO = "{{ v|default:0 }}"

_COLUMNAS_RESUMEN = (
    "inscripciones_total",
    "preinscriptos",
    "en_espera",
    "inscriptos",
    "validados_presencial",
    "completados",
    "abandonados",
    "registros_asistencia",
    "presentes",
    "ausentes",
)


def _opciones(pares):
    return [
        {"value": texto(_VALOR, v=v), "label": texto(_VALOR, v=e)} for v, e in pares
    ]


def _opcion_vacia(etiqueta):
    return [{"value": "", "label": etiqueta}]


def _filtros(contexto):
    """Controles del formulario de filtros, en el orden y con las opciones del template."""
    f = contexto["filtros"]

    def campo(key, label, tipo, opciones=None, permanente=False):
        return {
            "key": key,
            "label": label,
            "type": tipo,
            "permanent": permanente,
            "value": getattr(f, key),
            "options": opciones or [],
        }

    return [
        campo(
            "nivel",
            "Nivel",
            "select",
            _opciones(contexto["nivel_choices"]),
            True,
        ),
        campo(
            "group_by",
            "Agrupar por",
            "select",
            _opciones(contexto["group_by_choices"]),
            True,
        ),
        campo("fecha_desde", "Fecha desde", "date"),
        campo("fecha_hasta", "Fecha hasta", "date"),
        campo(
            "provincia_id",
            "Provincia",
            "select",
            _opcion_vacia("Todas")
            + _opciones(
                (p["provincia_id"], p["provincia__nombre"])
                for p in contexto["provincias"]
            ),
        ),
        campo(
            "municipio_id",
            "Municipio",
            "select",
            _opcion_vacia("Todos")
            + _opciones(
                (m["municipio_id"], m["municipio__nombre"])
                for m in contexto["municipios"]
            ),
        ),
        campo(
            "centro_id",
            "Centro",
            "select",
            _opcion_vacia("Todos")
            + _opciones((c["id"], c["nombre"]) for c in contexto["centros"]),
        ),
        campo(
            "comision_id",
            "Comisión",
            "select",
            _opcion_vacia("Todas")
            + _opciones(
                (
                    c["comision_id_ref"],
                    f"{texto(_VALOR, v=c['comision_codigo_ref'])} - "
                    f"{texto(_VALOR, v=c['centro_nombre_ref'])}",
                )
                for c in contexto["comisiones"]
            ),
        ),
        campo(
            "curso_id",
            "Curso",
            "select",
            _opcion_vacia("Todos")
            + _opciones(
                (c["unidad_formativa_id"], c["unidad_formativa_nombre"])
                for c in contexto["cursos"]
            ),
        ),
        campo(
            "programa_id",
            "Programa",
            "select",
            _opcion_vacia("Todos")
            + _opciones(
                (p["programa_id_ref"], p["programa_nombre_ref"])
                for p in contexto["programas"]
            ),
        ),
        campo(
            "titulo_id",
            "Título",
            "select",
            _opcion_vacia("Todos")
            + _opciones(
                (t["titulo_id_ref"], t["titulo_nombre_ref"])
                for t in contexto["titulos"]
            ),
        ),
        campo(
            "estado",
            "Estado inscripción",
            "select",
            _opcion_vacia("Todos") + _opciones(contexto["estado_choices"]),
        ),
        campo(
            "usa_voucher",
            "Usa voucher",
            "select",
            _opciones(contexto["usa_voucher_choices"]),
        ),
        campo(
            "estado_curso",
            "Estado curso",
            "select",
            _opcion_vacia("Todos") + _opciones(contexto["curso_estado_choices"]),
        ),
        campo(
            "estado_comision",
            "Estado comisión",
            "select",
            _opcion_vacia("Todos") + _opciones(contexto["comision_estado_choices"]),
        ),
    ]


def _celda(fila, clave, filtro=""):
    """Valor de ``fila.clave`` tal como lo imprime el template (clave ausente: vacío)."""
    return texto("{{ fila." + clave + filtro + " }}", fila=fila)


def _fila_resumen(row):
    columnas = (
        "grupo",
        *_COLUMNAS_RESUMEN,
        "porcentaje_asistencia",
        "sesiones_programadas",
        "sesiones_realizadas",
    )
    return {clave: _celda(row, clave) for clave in columnas}


def _fila_detalle(item):
    return {
        "documento": _celda(item, "numero_documento", "|default:'—'"),
        "persona": texto(
            "{{ item.ciudadano__apellido|default:'' }}, "
            "{{ item.ciudadano__nombre|default:'' }}",
            item=item,
        ),
        "estado": _celda(item, "estado"),
        "con_voucher": bool(item.get("tiene_voucher_activo")),
        "centro": _celda(item, "centro_nombre_ref"),
        "comision": _celda(item, "comision_codigo_ref"),
        "curso": _celda(item, "unidad_formativa_nombre"),
        "fecha": _celda(item, "fecha_inscripcion", "|date:'d/m/Y H:i'"),
    }


def _paginas(page_obj):
    return {
        "is_paginated": page_obj.has_other_pages(),
        "number": page_obj.number,
        "num_pages": page_obj.paginator.num_pages,
        "count": page_obj.paginator.count,
        "previous": (
            page_obj.previous_page_number() if page_obj.has_previous() else None
        ),
        "next": page_obj.next_page_number() if page_obj.has_next() else None,
        # ``{% if page_obj %}``: una página sin filas es falsa y no imprime el resumen.
        "summary": bool(page_obj),
    }


def _info_detalle(info):
    return {
        "number": info["number"],
        "num_pages": info["num_pages"],
        "count": texto(_ENTERO, v=info["count"]),
        "start_index": texto(_VALOR, v=info["start_index"]),
        "end_index": texto(_VALOR, v=info["end_index"]),
        "previous": info["previous_page_number"] if info["has_previous"] else None,
        "next": info["next_page_number"] if info["has_next"] else None,
    }


class ReporteInscripcionesAsistenciasWebView(VatNativeReadView):
    """``GET .../reportes/inscripciones-asistencias/``: ``inscripciones_asistencia.html``."""

    native_class = ReporteInscriptosAsistenciasView
    codigos = ["VAT.view_inscripcion", "VAT.view_comisioncurso", "VAT.view_centro"]

    def get(self, request):
        vista = self.native()
        filtros = vista._build_filtros()  # pylint: disable=protected-access
        reporte = build_reporte_inscripciones_asistencia(vista.request.user, filtros)
        c = vista.get_context_data(reporte=reporte, filtros=filtros)
        etiqueta = next((e for v, e in c["group_by_choices"] if v == c["group_by"]), "")
        return Response(
            {
                "nivel_pill": texto("{{ v|default:'inet'|upper }}", v=filtros.nivel),
                "filters": _filtros(c),
                "resumen": {
                    "inscripciones_total": texto(
                        _ENTERO, v=c["resumen"].get("inscripciones_total")
                    ),
                    "presentes": texto(_ENTERO, v=c["resumen"].get("presentes")),
                    "ausentes": texto(_ENTERO, v=c["resumen"].get("ausentes")),
                    "porcentaje_asistencia": texto(
                        _ENTERO, v=c["resumen"].get("porcentaje_asistencia")
                    ),
                },
                "group_label": etiqueta,
                "group_label_lower": texto("{{ v|lower }}", v=etiqueta),
                "rows": [_fila_resumen(row) for row in c["rows"]],
                "page": _paginas(c["page_obj"]),
                "querystring": c["querystring"],
                "querystring_detalle": c["querystring_detalle"],
                "detalle": {
                    "rows": [_fila_detalle(item) for item in c["detalle_rows"]],
                    "info": _info_detalle(c["detalle_page_info"]),
                },
                "urls": {
                    "list": reverse("vat_reporte_inscripciones_asistencias"),
                    "vat": reverse("vat_centro_list"),
                },
                "messages": mensajes_pendientes(vista.request),
            }
        )
