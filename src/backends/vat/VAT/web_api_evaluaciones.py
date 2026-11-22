"""Web API (G1 v1) de evaluaciones de VAT (V08.01) para React.

``/api/web/vat/evaluaciones/`` corre ``EvaluacionListView`` y
``EvaluacionDetailView`` y proyecta su contexto a JSON. Solo lectura: alta,
edición y baja siguen en las pantallas nativas. Acceso: ``VAT.view_evaluacion``
(la regla de la ruta); los botones de la lista salen de ``perms.VAT.*``.
"""

from django.urls import reverse
from rest_framework.response import Response

from VAT.views.evaluacion import EvaluacionDetailView, EvaluacionListView
from VAT.web_api_common import VatNativeReadView, mensajes_pendientes, texto

CODIGOS = ["VAT.view_evaluacion"]
_FECHA = "{{ v|date:'d/m/Y' }}"
_FECHA_HORA = "{{ v|date:'d/m/Y H:i' }}"


class EvaluacionListWebView(VatNativeReadView):
    """``GET .../evaluaciones/``: ``evaluacion_list.html`` con su queryset nativo."""

    native_class = EvaluacionListView
    codigos = CODIGOS

    def get(self, request):
        user = request.user

        def extra(context, _request):
            return {
                "results": [
                    {
                        "id": e.pk,
                        "nombre": e.nombre,
                        "comision": e.comision.codigo_comision,
                        "tipo_label": e.get_tipo_display(),
                        "fecha": texto(_FECHA, v=e.fecha),
                        "es_final": e.es_final,
                        "ponderacion": texto("{{ v }}", v=e.ponderacion),
                        "detail_url": reverse("vat_evaluacion_detail", args=[e.pk]),
                        "update_url": reverse("vat_evaluacion_update", args=[e.pk]),
                        "delete_url": reverse("vat_evaluacion_delete", args=[e.pk]),
                    }
                    for e in context["evaluaciones"]
                ],
                "busqueda": request.GET.get("busqueda", ""),
                "permisos": {
                    "editar": user.has_perm("VAT.change_evaluacion"),
                    "eliminar": user.has_perm("VAT.delete_evaluacion"),
                },
                "urls": {
                    "list": reverse("vat_evaluacion_list"),
                    "create": reverse("vat_evaluacion_create"),
                },
            }

        return self.lista(extra)


class EvaluacionDetailWebView(VatNativeReadView):
    """``GET .../evaluaciones/<pk>/``: ``evaluacion_detail.html``."""

    native_class = EvaluacionDetailView
    codigos = CODIGOS

    def get(self, request, pk):
        vista, _context = self.detalle(pk)
        e = vista.object
        django_request = request._request  # pylint: disable=protected-access
        return Response(
            {
                "id": e.pk,
                "titulo": str(e),
                "nombre": e.nombre,
                "tipo_label": e.get_tipo_display(),
                "comision_codigo": e.comision.codigo_comision,
                "comision_nombre": texto("{{ v }}", v=e.comision.nombre),
                "fecha": texto(_FECHA, v=e.fecha),
                "es_final": e.es_final,
                "ponderacion": texto("{{ v }}", v=e.ponderacion),
                "descripcion": texto("{{ v|default:'—' }}", v=e.descripcion),
                "observaciones": e.observaciones or "",
                "fecha_creacion": texto(_FECHA_HORA, v=e.fecha_creacion),
                "fecha_modificacion": texto(_FECHA_HORA, v=e.fecha_modificacion),
                "urls": {
                    "list": reverse("vat_evaluacion_list"),
                    "update": reverse("vat_evaluacion_update", args=[e.pk]),
                    "delete": reverse("vat_evaluacion_delete", args=[e.pk]),
                },
                "messages": mensajes_pendientes(django_request),
            }
        )
