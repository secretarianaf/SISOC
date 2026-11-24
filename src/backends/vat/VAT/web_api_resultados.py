"""Web API (G1 v1) de resultados de evaluación de VAT (V08.01 y V08.02).

``/api/web/vat/resultados-evaluacion/`` corre las vistas nativas
``ResultadoEvaluacion{List,Detail,Create,Update,Delete}View`` y proyecta su contexto:
lista, detalle, formulario (alta y edición, con ``form_valid`` nativo, que fija
``registrado_por`` y encola el mensaje) y baja lógica nativa. El POST responde
``{"ok": true, "redirect": <url>}`` o, con el formulario inválido, 400 con los
campos y errores. Acceso: ``VAT.view/add/change/delete_resultadoevaluacion``.
"""

from django.http import Http404
from django.urls import reverse
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from VAT.views.evaluacion import (
    ResultadoEvaluacionCreateView,
    ResultadoEvaluacionDeleteView,
    ResultadoEvaluacionDetailView,
    ResultadoEvaluacionListView,
    ResultadoEvaluacionUpdateView,
)
from VAT.web_api_common import (
    VatNativeReadView,
    campo_formulario,
    mensajes_pendientes,
    texto,
)

_FECHA = "{{ v|date:'d/m/Y' }}"
_FECHA_HORA = "{{ v|date:'d/m/Y H:i' }}"
_CALIFICACION = "{{ v|default:'—' }}"


def _aprobo(valor):
    """``None`` (pendiente), ``True`` (Sí) o ``False`` (No), como el template."""
    return None if valor is None else bool(valor)


class ResultadoListWebView(VatNativeReadView):
    """``GET .../resultados-evaluacion/``: ``resultado_list.html``."""

    native_class = ResultadoEvaluacionListView
    codigos = ["VAT.view_resultadoevaluacion"]

    def get(self, request):
        user = request.user

        def extra(context, _request):
            return {
                "results": [
                    {
                        "id": r.pk,
                        "evaluacion": r.evaluacion.nombre,
                        "persona": r.inscripcion.ciudadano.nombre_completo,
                        "calificacion": texto(_CALIFICACION, v=r.calificacion),
                        "aprobo": _aprobo(r.aprobo),
                        "fecha": texto(_FECHA, v=r.fecha_registro),
                        "detail_url": reverse(
                            "vat_resultado_evaluacion_detail", args=[r.pk]
                        ),
                        "update_url": reverse(
                            "vat_resultado_evaluacion_update", args=[r.pk]
                        ),
                        "delete_url": reverse(
                            "vat_resultado_evaluacion_delete", args=[r.pk]
                        ),
                    }
                    for r in context["resultados"]
                ],
                "busqueda": request.GET.get("busqueda", ""),
                "permisos": {
                    "editar": user.has_perm("VAT.change_resultadoevaluacion"),
                    "eliminar": user.has_perm("VAT.delete_resultadoevaluacion"),
                },
                "urls": {
                    "list": reverse("vat_resultado_evaluacion_list"),
                    "create": reverse("vat_resultado_evaluacion_create"),
                },
            }

        return self.lista(extra)


class ResultadoDetailWebView(VatNativeReadView):
    """``GET .../resultados-evaluacion/<pk>/``: ``resultado_detail.html``."""

    native_class = ResultadoEvaluacionDetailView
    codigos = ["VAT.view_resultadoevaluacion"]

    def get(self, request, pk):
        vista, _context = self.detalle(pk)
        r = vista.object
        django_request = request._request  # pylint: disable=protected-access
        return Response(
            {
                "id": r.pk,
                "titulo": texto("{{ v }}", v=r),
                "evaluacion": r.evaluacion.nombre,
                "tipo_label": r.evaluacion.get_tipo_display(),
                "persona": r.inscripcion.ciudadano.nombre_completo,
                "comision": r.evaluacion.comision.codigo_comision,
                "calificacion": texto(_CALIFICACION, v=r.calificacion),
                "aprobo": _aprobo(r.aprobo),
                "fecha_registro": texto(_FECHA_HORA, v=r.fecha_registro),
                "registrado_por": texto("{{ v }}", v=r.registrado_por),
                "observaciones": r.observaciones or "",
                "fecha_creacion": texto(_FECHA_HORA, v=r.fecha_creacion),
                "fecha_modificacion": texto(_FECHA_HORA, v=r.fecha_modificacion),
                "urls": {
                    "list": reverse("vat_resultado_evaluacion_list"),
                    "update": reverse("vat_resultado_evaluacion_update", args=[r.pk]),
                    "delete": reverse("vat_resultado_evaluacion_delete", args=[r.pk]),
                },
                "messages": mensajes_pendientes(django_request),
            }
        )


class _ResultadoEscrituraView(VatNativeReadView):
    http_method_names = ["get", "head", "post"]

    def preparar(self, kwargs):
        vista = self.native(**kwargs)
        try:
            vista.object = self.objeto(vista)
        except Http404 as exc:
            raise NotFound() from exc
        return vista

    def objeto(self, vista):
        return vista.get_object()

    @staticmethod
    def redireccion(respuesta):
        return Response({"ok": True, "redirect": respuesta["Location"]})


class _ResultadoFormView(_ResultadoEscrituraView):
    def get(self, request, **kwargs):
        vista = self.preparar(kwargs)
        return self.formulario(vista.get_form())

    def post(self, request, **kwargs):
        vista = self.preparar(kwargs)
        form = vista.get_form()
        if form.is_valid():
            return self.redireccion(vista.form_valid(form))
        return self.formulario(form, status=400)

    @staticmethod
    def formulario(form, status=200):
        return Response(
            {
                "editing": form.instance.pk is not None,
                "fields": [campo_formulario(form[nombre]) for nombre in form.fields],
                "urls": {"list": reverse("vat_resultado_evaluacion_list")},
            },
            status=status,
        )


class ResultadoCreateWebView(_ResultadoFormView):
    """``GET|POST .../resultados-evaluacion/nuevo/``."""

    native_class = ResultadoEvaluacionCreateView
    codigos = ["VAT.add_resultadoevaluacion"]

    def objeto(self, vista):
        return None


class ResultadoUpdateWebView(_ResultadoFormView):
    """``GET|POST .../resultados-evaluacion/<pk>/editar/``."""

    native_class = ResultadoEvaluacionUpdateView
    codigos = ["VAT.change_resultadoevaluacion"]


class ResultadoDeleteWebView(_ResultadoEscrituraView):
    """``GET|POST .../resultados-evaluacion/<pk>/eliminar/``: baja lógica nativa."""

    native_class = ResultadoEvaluacionDeleteView
    codigos = ["VAT.delete_resultadoevaluacion"]

    def get(self, request, **kwargs):
        r = self.preparar(kwargs).object
        return Response(
            {
                "persona": r.inscripcion.ciudadano.nombre_completo,
                "evaluacion": r.evaluacion.nombre,
                "calificacion": texto(_CALIFICACION, v=r.calificacion),
                "urls": {
                    "detail": reverse("vat_resultado_evaluacion_detail", args=[r.pk])
                },
            }
        )

    def post(self, request, **kwargs):
        vista = self.preparar(kwargs)
        return self.redireccion(vista.form_valid(vista.get_form()))
