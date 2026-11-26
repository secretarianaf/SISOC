"""Web API (G1 v1) de inscripciones de VAT (V03.02, U3) para React.

``/api/web/vat/inscripciones/`` corre las vistas nativas de ``VAT/views/persona.py``
(``InscripcionListView``, ``InscripcionDetailView``, ``InscripcionCreateView``,
``InscripcionUpdateView``, ``InscripcionDeleteView``) y proyecta su contexto a JSON. Las
escrituras ejecutan el ``form_valid`` o el ``post`` nativo (servicio, mensaje y baja lógica
incluidos) y responden ``{"ok": true, "redirect": <url>}``; con el formulario inválido, 400
con los campos y errores. Acceso: el decorador ``permissions_any_required`` de cada ruta nativa.
"""

from django.http import Http404
from django.urls import reverse
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from VAT.views.persona import (
    InscripcionCreateView,
    InscripcionDeleteView,
    InscripcionDetailView,
    InscripcionListView,
    InscripcionUpdateView,
)
from VAT.web_api_common import (
    VatNativeReadView,
    campo_formulario,
    mensajes_pendientes,
    texto,
)

_FECHA = "{{ v|date:'d/m/Y' }}"
_FECHA_HORA = "{{ v|date:'d/m/Y H:i' }}"
_DEFECTO_FECHA_HORA = "{{ v|date:'d/m/Y H:i'|default:'—' }}"


class InscripcionListWebView(VatNativeReadView):
    """``GET .../inscripciones/``: ``inscripcion_list.html`` con su queryset nativo."""

    native_class = InscripcionListView
    codigos = ["VAT.view_inscripcion"]

    def get(self, request):
        user = request.user

        def extra(context, _request):
            return {
                "results": [
                    {
                        "id": i.pk,
                        "ciudadano": i.ciudadano.nombre_completo,
                        "comision": texto(
                            "{{ v.codigo_comision }}", v=i.entidad_comision
                        ),
                        "programa": str(i.programa),
                        "canal": i.get_origen_canal_display(),
                        "fecha": texto(_FECHA, v=i.fecha_inscripcion),
                        "estado": i.estado,
                        "estado_label": i.get_estado_display(),
                        "detail_url": reverse("vat_inscripcion_detail", args=[i.pk]),
                        "update_url": reverse("vat_inscripcion_update", args=[i.pk]),
                        "delete_url": reverse("vat_inscripcion_delete", args=[i.pk]),
                    }
                    for i in context["inscripciones"]
                ],
                "busqueda": request.GET.get("busqueda", ""),
                "permisos": {
                    "editar": user.has_perm("VAT.change_inscripcion"),
                    "eliminar": user.has_perm("VAT.delete_inscripcion"),
                },
                "urls": {
                    "list": reverse("vat_inscripcion_list"),
                    "create": reverse("vat_inscripcion_create"),
                },
            }

        return self.lista(extra)


class InscripcionDetailWebView(VatNativeReadView):
    """``GET .../inscripciones/<pk>/``: ``inscripcion_detail.html``."""

    native_class = InscripcionDetailView
    codigos = ["VAT.view_inscripcion"]

    def get(self, request, pk):
        vista, context = self.detalle(pk)
        i = vista.object
        user = request.user
        return Response(
            {
                "id": i.pk,
                "ciudadano": i.ciudadano.nombre_completo,
                # El template nativo imprime ``ciudadano.dni``, atributo que no existe: queda vacío.
                "dni": texto("{{ c.dni }}", c=i.ciudadano),
                "comision_codigo": context["comision_codigo"],
                "comision_label": context["comision_label"],
                "programa": str(i.programa),
                "estado": i.estado,
                "estado_label": i.get_estado_display(),
                "canal": i.get_origen_canal_display(),
                "fecha_inscripcion": texto(_FECHA_HORA, v=i.fecha_inscripcion),
                "fecha_validacion": texto(
                    _DEFECTO_FECHA_HORA, v=i.fecha_validacion_presencial
                ),
                "observaciones": i.observaciones or "",
                "fecha_creacion": texto(_FECHA_HORA, v=i.fecha_creacion),
                "fecha_modificacion": texto(_FECHA_HORA, v=i.fecha_modificacion),
                "permisos": {
                    "editar": bool(
                        user.has_perm("VAT.change_inscripcion")
                        and context["permite_editar_inscripcion"]
                    ),
                    "eliminar": bool(
                        user.has_perm("VAT.delete_inscripcion")
                        and context["permite_eliminar_inscripcion"]
                    ),
                },
                "urls": {
                    "comision": str(context["comision_detail_url"]),
                    "update": reverse("vat_inscripcion_update", args=[i.pk]),
                    "delete": reverse("vat_inscripcion_delete", args=[i.pk]),
                },
                "messages": mensajes_pendientes(
                    request._request  # pylint: disable=protected-access
                ),
            }
        )


class _InscripcionEscrituraView(VatNativeReadView):
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


class _InscripcionFormView(_InscripcionEscrituraView):
    def get(self, request, **kwargs):
        vista = self.preparar(kwargs)
        return self.formulario(request, vista.get_form())

    def post(self, request, **kwargs):
        vista = self.preparar(kwargs)
        form = vista.get_form()
        if form.is_valid():
            respuesta = vista.form_valid(form)
            if respuesta.status_code == 302:
                return self.redireccion(respuesta)
            # El servicio rechazó la alta (``ValueError``): la vista nativa vuelve a
            # mostrar el formulario con el mensaje de error encolado.
        return self.formulario(request, form, status=400)

    @staticmethod
    def formulario(request, form, status=200):
        return Response(
            {
                "editing": form.instance.pk is not None,
                "fields": [campo_formulario(form[nombre]) for nombre in form.fields],
                "urls": {"list": reverse("vat_inscripcion_list")},
                "messages": mensajes_pendientes(
                    request._request  # pylint: disable=protected-access
                ),
            },
            status=status,
        )


class InscripcionCreateWebView(_InscripcionFormView):
    """``GET|POST .../inscripciones/nueva/`` (acepta ``?ciudadano=`` y ``?comision=``)."""

    native_class = InscripcionCreateView
    codigos = ["VAT.add_inscripcion"]

    def objeto(self, vista):
        return None


class InscripcionUpdateWebView(_InscripcionFormView):
    """``GET|POST .../inscripciones/<pk>/editar/``."""

    native_class = InscripcionUpdateView
    codigos = ["VAT.change_inscripcion"]


class InscripcionDeleteWebView(_InscripcionEscrituraView):
    """``GET|POST .../inscripciones/<pk>/eliminar/``: confirmación y baja lógica nativa."""

    native_class = InscripcionDeleteView
    codigos = ["VAT.delete_inscripcion"]

    def get(self, request, **kwargs):
        i = self.preparar(kwargs).object
        return Response(
            {
                "ciudadano": i.ciudadano.nombre_completo,
                "comision": texto("{{ v.codigo_comision }}", v=i.entidad_comision),
                "estado_label": i.get_estado_display(),
                "urls": {"detail": reverse("vat_inscripcion_detail", args=[i.pk])},
            }
        )

    def post(self, request, **kwargs):
        vista = self.preparar(kwargs)
        return self.redireccion(vista.form_valid(vista.get_form()))
