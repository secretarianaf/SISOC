"""Web API (G1 v1) de las acciones en página del detalle de un centro de VAT (V06.01, V05.01).

La página nativa ``centro_detail.html`` abre modales para agregar y editar contactos, ubicaciones, cursos y comisiones de curso.
Este módulo expone lo que esos modales necesitan y que los endpoints de formularios existentes no dan:

* ``centros-acciones/contactos/<pk>/editar/`` y ``centros-acciones/ubicaciones/<pk>/editar/`` (GET): todos los campos que dibuja
  ``form.as_p`` en el fragmento ``?modal=1`` de la vista nativa de edición (la plantilla de página omite ``nombre_ubicacion``).
* ``centros-acciones/cursos/nuevo/?centro=<id>`` y ``centros-acciones/cursos/<pk>/editar/`` (POST): corren ``CursoCreateView`` y
  ``CursoUpdateView`` (guarda de ``dispatch`` incluida) con su ``form_valid`` y responden ``{"ok": true, "redirect": <url>}`` o,
  con el formulario inválido, 400 con los campos y sus errores.

Los POST de contactos, ubicaciones y comisiones de curso son los de sus endpoints existentes. Acceso: el de cada ruta nativa.
"""

from django.forms import SelectMultiple
from django.http import HttpResponse
from django.urls import reverse
from rest_framework.response import Response

from VAT.views.curso import CursoCreateView, CursoUpdateView
from VAT.views.institucion import (
    InstitucionContactoUpdateView,
    InstitucionUbicacionUpdateView,
)
from VAT.web_api_common import campo_formulario
from VAT.web_api_vat_centros_base import VatFormWebView, con_mensaje, redireccion


def campo_modal(form, nombre):
    """One field as ``form.as_p`` draws it in the native modal (a locked field is ``disabled``)."""
    bound = form[nombre]
    widget = bound.field.widget
    if nombre == "localidad":
        # ``LocalidadSelectBajoDemanda`` draws only the chosen option; the rest comes by AJAX.
        grupos = widget.optgroups(bound.html_name, widget.format_value(bound.value()))
        bound.field.choices = [
            (o["value"], o["label"])
            for _nombre, opciones, _i in grupos
            for o in opciones
        ]
    campo = campo_formulario(bound)
    if isinstance(widget, SelectMultiple):
        campo["attrs"]["multiple"] = "multiple"
        campo["value"] = ",".join(str(v) for v in (bound.value() or []))
    if bound.field.disabled:
        campo["attrs"]["disabled"] = "disabled"
    # ``field.field.required`` (the asterisk of the native labels), not the ``required`` attribute of the widget.
    campo["required"] = bool(bound.field.required)
    return campo


def campos_modal(form):
    """The visible fields of ``form`` in form order, like the ``{% for field in form %}`` of the template."""
    return [
        campo_modal(form, nombre)
        for nombre, campo in form.fields.items()
        if not campo.widget.is_hidden
    ]


def planes_curriculares(form):
    """The rows of the plan selector modal: label (``nombre``, else título de referencia, else sector) and normativa."""
    filas = []
    for plan in form.fields["plan_estudio"].queryset:
        if plan.nombre:
            etiqueta = plan.nombre
        elif plan.titulo_referencia:
            etiqueta = plan.titulo_referencia.nombre
        else:
            etiqueta = plan.sector.nombre
        filas.append(
            {
                "id": plan.pk,
                "etiqueta": etiqueta,
                "normativa": plan.normativa or "",
            }
        )
    return filas


class _EdicionModalWebView(VatFormWebView):
    """GET of the update form of a native view as the modal fragment draws it (every visible field)."""

    http_method_names = ["get", "head"]

    def formulario(self, vista, form, status=200):
        return Response({"fields": campos_modal(form)}, status=status)


class ContactoEdicionModalWebView(_EdicionModalWebView):
    """``GET .../centros-acciones/contactos/<pk>/editar/``: ``contacto_form_modal.html``."""

    native_class = InstitucionContactoUpdateView
    codigos = ["VAT.change_institucioncontacto"]


class UbicacionEdicionModalWebView(_EdicionModalWebView):
    """``GET .../centros-acciones/ubicaciones/<pk>/editar/``: ``ubicacion_form_modal.html``."""

    native_class = InstitucionUbicacionUpdateView
    codigos = ["VAT.change_institucionubicacion"]


def _con_guarda(native_class):
    """The native view with its ``dispatch`` intact (the ``?centro=`` guard) and without running its ``get``/``post``."""

    class _Guarda(native_class):
        def get(self, request, *args, **kwargs):
            return HttpResponse()

        post = get

    return _Guarda


class _CursoEscrituraWebView(VatFormWebView):
    """POST of the course modal: the native create/update view, its form and its ``form_valid``."""

    http_method_names = ["post"]

    def formulario(self, vista, form, status=200):
        return Response(
            {
                "editing": form.instance.pk is not None,
                "fields": campos_modal(form),
                "planes": planes_curriculares(form),
                "non_field_errors": [str(e) for e in form.non_field_errors()],
                "urls": {"list": reverse("vat_centro_list")},
            },
            status=status,
        )

    def post(self, request, **kwargs):
        vista = self.preparar(kwargs)
        form = vista.get_form()
        if form.is_valid():
            return redireccion(vista.form_valid(form))
        return con_mensaje(self.formulario(vista, form, status=400), vista, form)


class CursoCreateModalWebView(_CursoEscrituraWebView):
    """``POST .../centros-acciones/cursos/nuevo/?centro=<id>``: ``CursoCreateView`` (needs an editable centro)."""

    native_class = CursoCreateView
    codigos = ["VAT.add_curso"]
    crear = True

    def preparar(self, kwargs):
        # ``CursoCreateView.dispatch`` raises 403 without ``?centro=`` or for a centro the user cannot edit.
        vista = _con_guarda(self.native_class)()
        django_request = self.request._request  # pylint: disable=protected-access
        vista.setup(django_request, **kwargs)
        vista.dispatch(django_request, **kwargs)
        vista.object = None
        return vista


class CursoUpdateModalWebView(_CursoEscrituraWebView):
    """``POST .../centros-acciones/cursos/<pk>/editar/``: ``CursoUpdateView`` (queryset scoped to the user's centros)."""

    native_class = CursoUpdateView
    codigos = ["VAT.change_curso"]
