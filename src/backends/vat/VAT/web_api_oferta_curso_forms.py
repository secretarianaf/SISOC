"""Web API (G1 v1) del alta, edición y baja de ofertas institucionales y de cursos de VAT (V05.02, U7).

``/api/web/vat/ofertas-institucionales/`` suma ``nueva/``, ``<pk>/editar/`` y ``<pk>/eliminar/``; ``/api/web/vat/cursos-formularios/``
suma ``nuevo/?centro=<id>``, ``<pk>/editar/`` y ``<pk>/eliminar/``. Corren las vistas nativas (``OfertaInstitucional*View`` y
``Curso*View``), su formulario, su ``form_valid`` (guardado y mensaje) y su baja lógica. El POST responde
``{"ok": true, "redirect": <url>}`` o, con el formulario inválido, 400 con los campos y errores. Acceso:
``VAT.add|change|delete_ofertainstitucional`` y ``VAT.add|change|delete_curso``, igual que las rutas nativas; el alta de curso
exige además el ``?centro=`` editable por el usuario (la guarda del ``dispatch`` nativo, 403 si falta).
"""

from django.urls import reverse
from rest_framework.response import Response

from VAT.views.curso import CursoCreateView, CursoDeleteView, CursoUpdateView
from VAT.views.oferta_institucional import (
    OfertaInstitucionalCreateView,
    OfertaInstitucionalDeleteView,
    OfertaInstitucionalUpdateView,
)
from VAT.web_api_comision_forms import ComisionBajaView, ComisionEscrituraView
from VAT.web_api_common import campo_formulario

# Campos que dibuja la plantilla nativa ``oferta_form.html`` (``plan_curricular`` va como oculto) y ``curso_form.html``.
CAMPOS_OFERTA = (
    "plan_curricular",
    "centro",
    "titulo_referencia",
    "programa",
    "ciclo_lectivo",
    "nombre_local",
    "estado",
    "usa_voucher",
    "costo",
    "fecha_publicacion",
    "observaciones",
)
CAMPOS_CURSO = (
    "plan_estudio",
    "nombre",
    "estado",
    "inscripcion_libre",
    "observaciones",
)


def _campo(form, nombre):
    """Un campo como lo dibuja el widget nativo, con ``disabled`` si el formulario lo bloquea (rol provincial)."""
    cuerpo = campo_formulario(form[nombre])
    if form.fields[nombre].widget.is_hidden:
        # ``plan_curricular`` es un ``ModelChoiceField`` con ``HiddenInput``: se dibuja como ``<input type="hidden">``, no como select.
        cuerpo = {**cuerpo, "tag": "input", "attrs": {"type": "hidden"}, "choices": []}
    if form.fields[nombre].disabled:
        cuerpo["attrs"] = {**cuerpo["attrs"], "disabled": "disabled"}
    cuerpo["required"] = form.fields[nombre].required
    return cuerpo


def _vouchers(form):
    """El ``<select multiple>`` de vouchers: opciones con su ``data-programa-id`` y todos los valores elegidos."""
    campo = form["voucher_parametrias"]
    cuerpo = campo_formulario(campo)
    return {
        "name": cuerpo["name"],
        "id": cuerpo["id"],
        "label": cuerpo["label"],
        "help_text": cuerpo["help_text"],
        "attrs": cuerpo["attrs"],
        "errors": cuerpo["errors"],
        "values": [str(valor) for valor in (campo.value() or [])],
        "choices": [
            {
                "value": str(valor.value),
                "label": str(etiqueta),
                "programa_id": str(valor.instance.programa_id),
            }
            for valor, etiqueta in campo.field.choices
            if valor != ""
        ],
    }


class _FormView(ComisionEscrituraView):
    """``GET|POST`` del formulario (alta y edición): corre el ``get_form`` y el ``form_valid`` nativos."""

    campos = ()

    def get(self, request, **kwargs):
        vista = self.preparar(kwargs)
        return self.formulario(vista, vista.get_form())

    def post(self, request, **kwargs):
        vista = self.preparar(kwargs)
        form = vista.get_form()
        if form.is_valid():
            return self.guardado(vista, vista.form_valid(form))
        return self.formulario(vista, form, status=400)

    @staticmethod
    def guardado(vista, respuesta):
        """Redirección nativa; una respuesta sin ``Location`` (variantes ``?modal=1`` o AJAX) usa la URL de éxito."""
        destino = respuesta["Location"] if "Location" in respuesta else None
        return Response({"ok": True, "redirect": destino or vista.get_success_url()})

    def formulario(self, vista, form, status=200):
        cuerpo = {
            "editing": form.instance.pk is not None,
            "fields": [_campo(form, nombre) for nombre in self.campos],
            "non_field_errors": [str(e) for e in form.non_field_errors()],
            "messages": self.mensajes() if status == 400 else [],
        }
        cuerpo.update(self.extra(vista, form))
        return Response(cuerpo, status=status)

    def extra(self, vista, form):
        raise NotImplementedError


class _OfertaFormView(_FormView):
    campos = CAMPOS_OFERTA

    def extra(self, vista, form):
        return {
            "vouchers": _vouchers(form),
            "urls": {"list": reverse("vat_oferta_institucional_list")},
        }


class OfertaInstitucionalCreateWebView(_OfertaFormView):
    """``GET|POST .../ofertas-institucionales/nueva/`` (``?centro=`` rellena el centro si es editable)."""

    native_class = OfertaInstitucionalCreateView
    codigos = ["VAT.add_ofertainstitucional"]
    alta = True


class OfertaInstitucionalUpdateWebView(_OfertaFormView):
    """``GET|POST .../ofertas-institucionales/<pk>/editar/``."""

    native_class = OfertaInstitucionalUpdateView
    codigos = ["VAT.change_ofertainstitucional"]


class OfertaInstitucionalDeleteWebView(ComisionBajaView):
    """``GET|POST .../ofertas-institucionales/<pk>/eliminar/``: confirmación y baja lógica nativa."""

    native_class = OfertaInstitucionalDeleteView
    codigos = ["VAT.delete_ofertainstitucional"]
    titulo = "{{ oferta }}"
    subtitulo = "Ciclo {{ oferta.ciclo_lectivo }} • {{ oferta.centro.nombre }}"
    contexto = "oferta"

    def cancelar(self, objeto):
        return reverse("vat_oferta_institucional_detail", args=[objeto.pk])


class _CursoFormView(_FormView):
    campos = CAMPOS_CURSO

    def extra(self, vista, form):
        contexto = vista.get_context_data(form=form)
        return {"urls": {"cancel": contexto["cancel_url"]}}


class CursoCreateWebView(_CursoFormView):
    """``GET|POST .../cursos-formularios/nuevo/?centro=<id>``: la guarda del ``dispatch`` nativo corre primero."""

    native_class = CursoCreateView
    codigos = ["VAT.add_curso"]
    alta = True
    guarda_dispatch = True


class CursoUpdateWebView(_CursoFormView):
    """``GET|POST .../cursos-formularios/<pk>/editar/``."""

    native_class = CursoUpdateView
    codigos = ["VAT.change_curso"]


class CursoDeleteWebView(ComisionBajaView):
    """``GET|POST .../cursos-formularios/<pk>/eliminar/``: confirmación y baja lógica nativa."""

    native_class = CursoDeleteView
    codigos = ["VAT.delete_curso"]
    titulo = "{{ curso.nombre }}"
    contexto = "curso"

    def cancelar(self, objeto):
        return f"{reverse('vat_centro_detail', args=[objeto.centro_id])}#cursos"
