"""Web API (G1 v1) del detalle de comisión de VAT (V04.01, U4).

``/api/web/vat/comisiones-detalle/<pk>/`` (oferta) y ``/api/web/vat/comisiones-detalle/cursos/<pk>/``
(curso) corren ``ComisionDetailView`` y ``ComisionCursoDetailView`` (las dos usan
``comision_detail.html``) y proyectan su contexto: el alcance por usuario, los permisos de la
pantalla, las tablas y los mensajes son los nativos. Fechas, horas y números salen del motor de
plantillas de Django, y lo que el template nativo imprime vacío (por ejemplo las métricas de la
variante de oferta) queda vacío. Acceso: ``VAT.view_comision`` / ``VAT.view_comisioncurso``.

Las acciones de la pestaña «Resultados» (solo curso) corren las vistas nativas con el permiso de su ruta
(``VAT.change_inscripcion``): ``POST .../cursos/<pk>/resultados/`` guarda el acta y las calificaciones y responde
``{"ok": true, "redirect": <detalle>#resultados}``; ``GET .../cursos/<pk>/profesores/buscar/`` y
``POST .../cursos/<pk>/profesores/nuevo/`` conservan el JSON y el estado de la vista nativa. Una comisión fuera de
alcance da 404 y no escribe. El cambio de estado, el lote y la alta rápida son las rutas de
``web_api_inscripcion_acciones``.
"""

import json

from django.http import Http404
from django.urls import reverse
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from VAT.views.curso import (
    ComisionCursoDetailView,
    ComisionCursoResultadosView,
    ProfesorCentroBuscarView,
    ProfesorCentroCrearView,
)
from VAT.views.oferta_institucional import ComisionDetailView
from VAT.web_api_common import (
    VatNativeReadView,
    campo_formulario,
    mensajes_pendientes,
    texto,
)

_DEFECTO = "{{ v|default:'—' }}"
_FECHA = "{{ v|date:'d/m/Y' }}"
_HORA = "{{ v|time:'H:i' }}"
_DIA_FECHA = '{{ v|date:"d \\d\\e F" }}'

_PERMISOS = (
    "puede_gestionar_comision",
    "puede_editar_comision",
    "puede_eliminar_comision",
    "puede_agregar_inscripcion",
    "puede_cambiar_inscripcion",
    "puede_eliminar_inscripcion",
    "puede_gestionar_asistencia",
    "puede_agregar_comision_horario",
    "puede_editar_comision_horario",
    "puede_eliminar_comision_horario",
    "puede_gestionar_lote_inscriptos",
    "puede_gestionar_resultados",
)


def _inscripcion(insc, *, espera):
    ciudadano = insc.ciudadano
    fila = {
        "id": insc.pk,
        "apellido": texto(_DEFECTO, v=ciudadano.apellido),
        "nombre": texto(_DEFECTO, v=ciudadano.nombre),
        "documento": texto(
            "{{ c.get_tipo_documento_display }} {{ c.numero_documento|default:'—' }}",
            c=ciudadano,
        ),
        "estado": insc.estado,
        "estado_label": texto("{{ i.get_estado_display }}", i=insc),
        "detail_url": reverse("vat_inscripcion_detail", kwargs={"pk": insc.pk}),
    }
    if espera:
        fila["fecha"] = texto(_FECHA, v=insc.fecha_inscripcion)
        return fila
    porcentaje = getattr(insc, "porcentaje_asistencia", None)
    fila.update(
        {
            "busqueda": texto(
                "{{ c.apellido|lower }} {{ c.nombre|lower }}", c=ciudadano
            ),
            "tipo_alumno": texto("{{ i.tipo_alumno }}", i=insc),
            "es_alumno_vat": bool(insc.es_alumno_vat),
            "email": texto(_DEFECTO, v=ciudadano.email),
            "telefono": texto(_DEFECTO, v=ciudadano.telefono),
            "asistencia": None if porcentaje is None else str(porcentaje),
            "delete_url": reverse("vat_inscripcion_delete", kwargs={"pk": insc.pk}),
        }
    )
    return fila


def _sesion(sesion, asistencia_url_name):
    realizada = sesion.estado == "realizada"

    def conteo(nombre):
        if not realizada:
            return ""
        return texto("{{ v }}", v=getattr(sesion, nombre, ""))

    return {
        "id": sesion.pk,
        "numero": sesion.numero_sesion,
        "dia": texto(_DEFECTO, v=sesion.horario.dia_semana),
        "fecha": texto(_DIA_FECHA, v=sesion.fecha),
        "desde": texto(_HORA, v=sesion.horario.hora_desde),
        "hasta": texto(_HORA, v=sesion.horario.hora_hasta),
        "estado": sesion.estado,
        "presentes": conteo("presentes"),
        "ausentes": conteo("ausentes"),
        "asistencia_url": reverse(asistencia_url_name, kwargs={"sesion_pk": sesion.pk}),
    }


def _horario(horario, context):
    return {
        "id": horario.pk,
        "dia": texto("{{ v }}", v=horario.dia_semana),
        "dia_semana_id": horario.dia_semana_id,
        "desde": texto(_HORA, v=horario.hora_desde),
        "hasta": texto(_HORA, v=horario.hora_hasta),
        "duracion": texto("{{ v }}", v=horario.duracion_label),
        "aula_espacio": texto("{{ v|default:'' }}", v=horario.aula_espacio),
        "vigente": bool(horario.vigente),
        "update_url": reverse(
            context["horario_update_url_name"], kwargs={"pk": horario.pk}
        ),
        "delete_url": reverse(
            context["horario_delete_url_name"], kwargs={"pk": horario.pk}
        ),
    }


def _resultados(context):
    """Pestaña «Resultados» (solo curso, con ``puede_gestionar_resultados``)."""
    if not context.get("puede_gestionar_resultados"):
        return None
    acta = context["acta_cierre"]
    resumen = context["resumen_resultados"]
    return {
        "aprobado": context["resultado_aprobado"],
        "desaprobado": context["resultado_desaprobado"],
        "resumen": {
            clave: texto("{{ v }}", v=resumen[clave])
            for clave in ("aprobados", "desaprobados", "sin_calificar", "inscriptos")
        },
        "alumnos": [
            {
                "id": alumno.pk,
                "apellido": texto(_DEFECTO, v=alumno.ciudadano.apellido),
                "nombre": texto(_DEFECTO, v=alumno.ciudadano.nombre),
                "documento": texto(
                    "{{ c.get_tipo_documento_display }} "
                    "{{ c.numero_documento|default:'—' }}",
                    c=alumno.ciudadano,
                ),
                "resultado": alumno.resultado_final or "",
            }
            for alumno in context["alumnos_resultados"]
        ],
        "profesor_id": acta.profesor_id if acta else None,
        "profesor_texto": (
            texto(
                "{{ p.apellido }}, {{ p.nombre }} — DNI {{ p.documento }} — {{ p.email }}",
                p=acta.profesor,
            )
            if acta
            else ""
        ),
        "fecha_fin": texto("{{ v|date:'Y-m-d' }}", v=context["acta_fecha_fin_inicial"]),
        "numero_acta": (acta.numero_acta or "") if acta else "",
    }


_CAMPOS_RAPIDA = (
    "apellido",
    "nombre",
    "tipo_documento",
    "documento",
    "fecha_nacimiento",
    "sexo",
)


def _formularios(context):
    """Campos de los formularios de los modales (alta rápida y profesor nuevo)."""
    rapida = context["ciudadano_rapido_form"]
    profesor = context.get("profesor_form")
    return {
        "rapida": (
            [campo_formulario(rapida[nombre]) for nombre in _CAMPOS_RAPIDA]
            if context.get("puede_agregar_inscripcion")
            else None
        ),
        "profesor": (
            [campo_formulario(campo) for campo in profesor]
            if context.get("puede_gestionar_resultados")
            else None
        ),
    }


def proyectar(context, request):
    """JSON del contexto del detalle nativo (oferta o curso)."""
    comision = context["comision"]
    es_curso = "metricas_comision" in context
    lista_espera = context["lista_espera"]
    resultados = _resultados(context)
    horario_create = reverse(context["horario_create_url_name"])
    return {
        "tipo": "curso" if es_curso else "oferta",
        "id": comision.pk,
        "codigo": comision.codigo_comision,
        "nombre": texto("{{ c.nombre|default:c.codigo_comision }}", c=comision),
        "titulo_tipo": context["comision_tipo_titulo"],
        "subtitulo": texto("{{ v }}", v=context["comision_subtitle"]),
        "estado_label": texto("{{ c.get_estado_display }}", c=comision),
        "acepta_lista_espera": bool(getattr(comision, "acepta_lista_espera", False)),
        "ubicacion": texto(_DEFECTO, v=comision.ubicacion),
        "fecha_inicio": texto(
            "{{ v|date:'d/m/Y'|default:'—' }}", v=comision.fecha_inicio
        ),
        "fecha_fin": texto("{{ v|date:'d/m/Y'|default:'—' }}", v=comision.fecha_fin),
        "cupo": texto("{{ v }}", v=comision.cupo),
        "cupo_lista_espera": texto(
            _DEFECTO, v=getattr(comision, "cupo_lista_espera", "")
        ),
        "cupo_ocupado": texto("{{ v }}", v=context["cupo_ocupado"]),
        "clases_dictadas": texto("{{ v }}", v=context.get("clases_dictadas", "")),
        "clases_pendientes": texto("{{ v }}", v=context.get("clases_pendientes", "")),
        "metricas": [
            {
                "valor": texto("{{ m.valor }}{{ m.sufijo }}", m=metrica),
                "label": metrica["label"],
            }
            for metrica in context.get("metricas_comision", [])
        ],
        "horarios": [_horario(h, context) for h in context["horarios"]],
        "sesiones": [
            _sesion(s, context["asistencia_url_name"]) for s in context["sesiones"]
        ],
        "inscripciones": [
            _inscripcion(i, espera=False) for i in context["inscripciones"]
        ],
        "lista_espera": [_inscripcion(i, espera=True) for i in lista_espera],
        "permisos": {
            clave.removeprefix("puede_"): bool(context.get(clave, False))
            for clave in _PERMISOS
        },
        "urls": {
            "eliminar": context["comision_delete_url"],
            "exportar_preinscriptos": context.get("export_preinscriptos_url"),
            "exportar_inscriptos": context.get("export_inscriptos_url"),
            "horario_nuevo": (
                f"{horario_create}?{context['horario_create_query_param']}={comision.pk}"
            ),
        },
        "resultados": resultados,
        "formularios": _formularios(context),
        "messages": mensajes_pendientes(
            request._request  # pylint: disable=protected-access
        ),
    }


class _ComisionDetalleWebView(VatNativeReadView):
    """GET del contexto de la vista nativa."""

    def get(self, request, pk):
        _, context = self.detalle(pk)
        return Response(proyectar(context, request))


class ComisionDetalleOfertaWebView(_ComisionDetalleWebView):
    """``GET .../comisiones-detalle/<pk>/``."""

    native_class = ComisionDetailView
    codigos = ["VAT.view_comision"]


class ComisionDetalleCursoWebView(_ComisionDetalleWebView):
    """``GET .../comisiones-detalle/cursos/<pk>/``."""

    native_class = ComisionCursoDetailView
    codigos = ["VAT.view_comisioncurso"]


class _ComisionCursoAccionWebView(VatNativeReadView):
    """Acciones de la pestaña «Resultados»: la vista nativa de la ruta, con su 404."""

    native_class = None
    codigos = ["VAT.change_inscripcion"]

    def ejecutar(self, metodo, pk):
        vista = self.native(pk=pk)
        try:
            return getattr(vista, metodo)(vista.request, pk=pk)
        except Http404 as exc:
            raise NotFound() from exc


class ComisionCursoResultadosWebView(_ComisionCursoAccionWebView):
    """``POST .../comisiones-detalle/cursos/<pk>/resultados/``."""

    http_method_names = ["post"]
    native_class = ComisionCursoResultadosView

    def post(self, request, pk):
        respuesta = self.ejecutar("post", pk)
        return Response({"ok": True, "redirect": respuesta["Location"]})


class ProfesorCentroBuscarWebView(_ComisionCursoAccionWebView):
    """``GET .../comisiones-detalle/cursos/<pk>/profesores/buscar/``."""

    native_class = ProfesorCentroBuscarView

    def get(self, request, pk):
        return Response(json.loads(self.ejecutar("get", pk).content))


class ProfesorCentroCrearWebView(_ComisionCursoAccionWebView):
    """``POST .../comisiones-detalle/cursos/<pk>/profesores/nuevo/``."""

    http_method_names = ["post"]
    native_class = ProfesorCentroCrearView

    def post(self, request, pk):
        respuesta = self.ejecutar("post", pk)
        return Response(json.loads(respuesta.content), status=respuesta.status_code)
