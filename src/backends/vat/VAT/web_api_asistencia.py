"""Web API (G1 v1) del registro de asistencia por sesión de VAT (V02.01).

``/api/web/vat/cursos/comisiones/sesiones/<pk>/asistencia/`` y
``/api/web/vat/comisiones/sesiones/<pk>/asistencia/`` corren las vistas nativas
``AsistenciaSesionCursoView`` y ``AsistenciaSesionView`` (``asistencia_sesion.html``):
el GET proyecta su contexto y el POST ejecuta su ``post`` nativo (guardado, estado de la
sesión y mensaje encolado) y responde ``{"ok": true, "redirect": <url>}``. Una sesión
fuera del alcance de la vista da 404 y no escribe. Acceso: ``VAT.add_asistenciasesion``
o ``VAT.change_asistenciasesion`` (la regla de la ruta nativa).
"""

from django.http import Http404
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from VAT.views.curso import AsistenciaSesionCursoView
from VAT.views.oferta_institucional import AsistenciaSesionView
from VAT.web_api_common import VatNativeReadView, mensajes_pendientes, texto

_DEFECTO = "{{ v|default:'—' }}"
_DIA = '{{ s.horario.dia_semana }} {{ s.fecha|date:"j \\d\\e F" }}'
_HORARIO = (
    '{{ s.horario.hora_desde|time:"H:i" }} a {{ s.horario.hora_hasta|time:"H:i" }} hs'
)


def _fila(fila):
    inscripcion = fila["inscripcion"]
    return {
        "id": inscripcion.pk,
        "apellido": texto(_DEFECTO, v=inscripcion.ciudadano.apellido),
        "nombre": texto(_DEFECTO, v=inscripcion.ciudadano.nombre),
        "tipo_alumno": str(inscripcion.tipo_alumno),
        "es_alumno_vat": bool(inscripcion.es_alumno_vat),
        "presente": fila["presente"],
        "observaciones": fila["observaciones"] or "",
    }


class _AsistenciaWebView(VatNativeReadView):
    """GET (contexto de la vista nativa) y POST (su ``post``) de una sesión."""

    http_method_names = ["get", "head", "post"]
    codigos = ["VAT.add_asistenciasesion", "VAT.change_asistenciasesion"]

    def get(self, request, pk):
        vista = self.native(sesion_pk=pk)
        try:
            context = vista.get_context_data()
        except Http404 as exc:
            raise NotFound() from exc
        sesion = context["sesion"]
        return Response(
            {
                "numero_sesion": sesion.numero_sesion,
                "comision_label": context["comision_label"],
                "curso": texto("{{ s.comision_curso.curso }}", s=sesion),
                "estado": texto("{{ s.comision_curso.get_estado_display }}", s=sesion),
                "dia": texto(_DIA, s=sesion),
                "horario": texto(_HORARIO, s=sesion),
                "totales": {
                    clave: (
                        str(context[f"total_{clave}"])
                        if f"total_{clave}" in context
                        else ""
                    )
                    for clave in ("presentes", "ausentes", "sin_marcar")
                },
                "filas": [_fila(fila) for fila in context["filas"]],
                "messages": mensajes_pendientes(
                    request._request  # pylint: disable=protected-access
                ),
            }
        )

    def post(self, request, pk):
        vista = self.native(sesion_pk=pk)
        try:
            respuesta = vista.post(vista.request, sesion_pk=pk)
        except Http404 as exc:
            raise NotFound() from exc
        return Response({"ok": True, "redirect": respuesta["Location"]})


class AsistenciaSesionCursoWebView(_AsistenciaWebView):
    """``.../cursos/comisiones/sesiones/<pk>/asistencia/``."""

    native_class = AsistenciaSesionCursoView


class AsistenciaSesionOfertaWebView(_AsistenciaWebView):
    """``.../comisiones/sesiones/<pk>/asistencia/``."""

    native_class = AsistenciaSesionView
