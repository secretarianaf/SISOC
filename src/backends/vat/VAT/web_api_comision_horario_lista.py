"""Web API (G1 v1) de la lista y el detalle de horarios de comisión de oferta de VAT (V04.01, U4).

``/api/web/vat/comisiones-horarios/`` y ``.../<pk>/`` corren ``ComisionHorarioListView`` y ``ComisionHorarioDetailView``
(``horario_list.html`` y ``horario_detail.html``) y proyectan su contexto con el texto que imprimen las plantillas
(``H:i``, ``d/m/Y H:i``, ``default``). Acceso: ``VAT.view_comisionhorario``, la regla de la ruta nativa; el alcance es el
queryset nativo (fuera de él, 404; los horarios de comisiones de curso no están en él). Los filtros ``comision_id`` y
``dia_semana`` son los nativos. Comparte el prefijo con las altas, ediciones y bajas de ``web_api_comision_horario_forms.py``.
"""

from django.urls import reverse
from rest_framework.response import Response

from VAT.views.oferta_institucional import (
    ComisionHorarioDetailView,
    ComisionHorarioListView,
)
from VAT.web_api_common import VatNativeReadView, mensajes_pendientes, texto

_HORA = "{{ v|time:'H:i' }}"
_AULA = "{{ v|default:'—' }}"
_FECHA_HORA = "{{ v|date:'d/m/Y H:i' }}"


class ComisionHorarioListWebView(VatNativeReadView):
    """``GET .../comisiones-horarios/``: ``horario_list.html``."""

    native_class = ComisionHorarioListView
    codigos = ["VAT.view_comisionhorario"]

    def get(self, request):
        user = request.user

        def extra(context, _request):
            return {
                "results": [
                    {
                        "id": h.pk,
                        "comision": texto("{{ v }}", v=h.comision),
                        "dia": texto("{{ v }}", v=h.dia_semana),
                        "desde": texto(_HORA, v=h.hora_desde),
                        "hasta": texto(_HORA, v=h.hora_hasta),
                        "aula": texto(_AULA, v=h.aula_espacio),
                        "vigente": bool(h.vigente),
                        "detail_url": reverse(
                            "vat_comision_horario_detail", args=[h.pk]
                        ),
                        "update_url": reverse(
                            "vat_comision_horario_update", args=[h.pk]
                        ),
                        "delete_url": reverse(
                            "vat_comision_horario_delete", args=[h.pk]
                        ),
                    }
                    for h in context["horarios"]
                ],
                "busqueda": request.GET.get("busqueda", ""),
                "permisos": {
                    "editar": user.has_perm("VAT.change_comisionhorario"),
                    "eliminar": user.has_perm("VAT.delete_comisionhorario"),
                },
                "urls": {
                    "list": reverse("vat_comision_horario_list"),
                    "create": reverse("vat_comision_horario_create"),
                },
            }

        return self.lista(extra)


class ComisionHorarioDetailWebView(VatNativeReadView):
    """``GET .../comisiones-horarios/<pk>/``: ``horario_detail.html``."""

    native_class = ComisionHorarioDetailView
    codigos = ["VAT.view_comisionhorario"]

    def get(self, request, pk):
        vista, _context = self.detalle(pk)
        h = vista.object
        return Response(
            {
                "id": h.pk,
                "title": texto("{{ v }}", v=h),
                "comision": texto("{{ v }}", v=h.comision),
                "dia": texto("{{ v }}", v=h.dia_semana),
                "aula": texto(_AULA, v=h.aula_espacio),
                "desde": texto(_HORA, v=h.hora_desde),
                "hasta": texto(_HORA, v=h.hora_hasta),
                "vigente": bool(h.vigente),
                "creado": texto(_FECHA_HORA, v=h.fecha_creacion),
                "modificado": texto(_FECHA_HORA, v=h.fecha_modificacion),
                "urls": {
                    "list": reverse("vat_comision_horario_list"),
                    "update": reverse("vat_comision_horario_update", args=[h.pk]),
                    "delete": reverse("vat_comision_horario_delete", args=[h.pk]),
                },
                "messages": mensajes_pendientes(
                    request._request  # pylint: disable=protected-access
                ),
            }
        )
