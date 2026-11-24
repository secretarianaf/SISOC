"""Web API (G1 v1) de las inscripciones a comisiones de oferta de VAT (V03.01).

``/api/web/vat/inscripciones-oferta/`` corre las vistas nativas ``InscripcionOferta{List,Detail,Create,Update,Delete}View``
y proyecta su contexto: lista, detalle, formulario (alta y edición, con el ``form_valid`` nativo, que encola el
mensaje) y baja nativa (``post`` de ``DeleteView``). El POST responde ``{"ok": true, "redirect": <url>}`` o, con el
formulario inválido, 400 con los campos, los errores generales y los mensajes encolados. Acceso:
``VAT.view/add/change/delete_inscripcionoferta`` (la regla de cada ruta nativa).
"""

from django.http import Http404
from django.urls import reverse
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from VAT.views.oferta import (
    InscripcionOfertaCreateView,
    InscripcionOfertaDeleteView,
    InscripcionOfertaDetailView,
    InscripcionOfertaListView,
    InscripcionOfertaUpdateView,
)
from VAT.web_api_common import (
    VatNativeReadView,
    campo_formulario,
    mensajes_pendientes,
    texto,
)

_FECHA_HORA = "{{ v|date:'d/m/Y H:i' }}"
_OFERTA = "{{ i.oferta.plan_curricular.titulo_referencia.nombre }}"
_CENTRO = "{{ i.oferta.centro.nombre }}"
_DIAS = "{% for dia in i.oferta.dias_semana.all %}{{ dia.nombre }}\n{% endfor %}"


class InscripcionOfertaListWebView(VatNativeReadView):
    """``GET .../inscripciones-oferta/``: ``list.html`` con su queryset nativo."""

    native_class = InscripcionOfertaListView
    codigos = ["VAT.view_inscripcionoferta"]

    def get(self, request):
        user = request.user

        def extra(context, _request):
            return {
                "results": [
                    {
                        "id": i.pk,
                        "ciudadano": i.ciudadano.nombre_completo,
                        "documento": texto("{{ v }}", v=i.ciudadano.documento),
                        "oferta": texto(_OFERTA, i=i),
                        "centro": texto(_CENTRO, i=i),
                        "estado": i.estado,
                        "estado_label": i.get_estado_display(),
                        "fecha": texto(_FECHA_HORA, v=i.fecha_inscripcion),
                        "detail_url": reverse(
                            "vat_inscripcion_oferta_detail", args=[i.pk]
                        ),
                        "update_url": reverse(
                            "vat_inscripcion_oferta_update", args=[i.pk]
                        ),
                        "delete_url": reverse(
                            "vat_inscripcion_oferta_delete", args=[i.pk]
                        ),
                    }
                    for i in context["inscripciones"]
                ],
                "busqueda": request.GET.get("busqueda", ""),
                "permisos": {
                    "editar": user.has_perm("VAT.change_inscripcionoferta"),
                    "eliminar": user.has_perm("VAT.delete_inscripcionoferta"),
                },
                "urls": {
                    "list": reverse("vat_inscripcion_oferta_list"),
                    "create": reverse("vat_inscripcion_oferta_create"),
                },
            }

        return self.lista(extra)


class InscripcionOfertaDetailWebView(VatNativeReadView):
    """``GET .../inscripciones-oferta/<pk>/``: ``detail.html``."""

    native_class = InscripcionOfertaDetailView
    codigos = ["VAT.view_inscripcionoferta"]

    def get(self, request, pk):
        vista, _context = self.detalle(pk)
        i = vista.object
        user = request.user
        django_request = request._request  # pylint: disable=protected-access
        return Response(
            {
                "id": i.pk,
                "ciudadano": i.ciudadano.nombre_completo,
                "documento": texto("{{ v }}", v=i.ciudadano.documento),
                "oferta": texto(_OFERTA, i=i),
                "centro": texto(_CENTRO, i=i),
                "estado": i.estado,
                "estado_label": i.get_estado_display(),
                "periodo": texto(
                    "{{ i.oferta.fecha_inicio|date:'d/m/Y' }} - {{ i.oferta.fecha_fin|date:'d/m/Y' }}",
                    i=i,
                ),
                "horario": texto(
                    "{{ i.oferta.horario_desde|time:'H:i' }} - {{ i.oferta.horario_hasta|time:'H:i' }}",
                    i=i,
                ),
                "dias": [d for d in texto(_DIAS, i=i).split("\n") if d],
                "costo": texto(
                    "{% if i.oferta.costo_por_participante %}${{ i.oferta.costo_por_participante }}{% endif %}",
                    i=i,
                ),
                "inscrito_por": texto("{{ i.inscrito_por.get_full_name }}", i=i),
                "fecha_inscripcion": texto(_FECHA_HORA, v=i.fecha_inscripcion),
                "fecha_modificacion": texto(_FECHA_HORA, v=i.fecha_modificacion),
                "permisos": {
                    "editar": user.has_perm("VAT.change_inscripcionoferta"),
                    "eliminar": user.has_perm("VAT.delete_inscripcionoferta"),
                },
                "urls": {
                    "list": reverse("vat_inscripcion_oferta_list"),
                    "update": reverse("vat_inscripcion_oferta_update", args=[i.pk]),
                    "delete": reverse("vat_inscripcion_oferta_delete", args=[i.pk]),
                },
                "messages": mensajes_pendientes(django_request),
            }
        )


class _EscrituraView(VatNativeReadView):
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


class _FormView(_EscrituraView):
    def get(self, request, **kwargs):
        vista = self.preparar(kwargs)
        return self.formulario(vista.get_form())

    def post(self, request, **kwargs):
        vista = self.preparar(kwargs)
        form = vista.get_form()
        if form.is_valid():
            respuesta = vista.form_valid(form)
            if respuesta.status_code == 302:
                return self.redireccion(respuesta)
        else:
            vista.form_invalid(form)
        # ``form_invalid`` (o un error del servicio) encoló el mensaje nativo.
        return self.formulario(form, status=400)

    def mensajes(self):
        """Mensajes que ``form_invalid`` y el servicio encolaron en la sesión."""
        django_request = self.request._request  # pylint: disable=protected-access
        return mensajes_pendientes(django_request)

    def formulario(self, form, status=200):
        return Response(
            {
                "editing": form.instance.pk is not None,
                "fields": [campo_formulario(form[nombre]) for nombre in form.fields],
                "non_field_errors": [str(e) for e in form.non_field_errors()],
                "urls": {"list": reverse("vat_inscripcion_oferta_list")},
                "messages": self.mensajes() if status == 400 else [],
            },
            status=status,
        )


class InscripcionOfertaCreateWebView(_FormView):
    """``GET|POST .../inscripciones-oferta/nueva/``."""

    native_class = InscripcionOfertaCreateView
    codigos = ["VAT.add_inscripcionoferta"]

    def objeto(self, vista):
        return None


class InscripcionOfertaUpdateWebView(_FormView):
    """``GET|POST .../inscripciones-oferta/<pk>/editar/``."""

    native_class = InscripcionOfertaUpdateView
    codigos = ["VAT.change_inscripcionoferta"]


class InscripcionOfertaDeleteWebView(_EscrituraView):
    """``GET|POST .../inscripciones-oferta/<pk>/eliminar/``: confirmación y baja nativa."""

    native_class = InscripcionOfertaDeleteView
    codigos = ["VAT.delete_inscripcionoferta"]

    def get(self, request, **kwargs):
        i = self.preparar(kwargs).object
        return Response(
            {
                "ciudadano": i.ciudadano.nombre_completo,
                "oferta": texto(_OFERTA, i=i),
                "estado_label": i.get_estado_display(),
                "urls": {
                    "detail": reverse("vat_inscripcion_oferta_detail", args=[i.pk])
                },
            }
        )

    def post(self, request, **kwargs):
        vista = self.preparar(kwargs)
        return self.redireccion(vista.post(vista.request, **kwargs))
