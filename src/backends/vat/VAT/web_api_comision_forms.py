"""Web API (G1 v1) del alta, edición y baja de las comisiones de VAT (V04.02, U5).

``/api/web/vat/comisiones-formularios/`` (oferta) y ``/api/web/vat/comisiones-formularios/cursos/`` (curso) suman ``nueva/``,
``<pk>/editar/`` y ``<pk>/eliminar/``: corren las vistas nativas (``Comision*View`` y ``ComisionCurso*View``), su formulario,
su ``form_valid`` (guardado, regeneración de clases y mensaje) y su baja lógica. El POST responde
``{"ok": true, "redirect": <url>}`` o, con el formulario inválido, 400 con los campos y errores.
Acceso: ``VAT.add|change|delete_comision`` y ``VAT.add|change|delete_comisioncurso``, igual que las rutas nativas.
"""

from django.http import HttpResponse
from django.urls import reverse
from rest_framework.response import Response

from VAT.views.curso import (
    ComisionCursoCreateView,
    ComisionCursoDeleteView,
    ComisionCursoUpdateView,
)
from VAT.views.oferta_institucional import (
    ComisionCreateView,
    ComisionDeleteView,
    ComisionUpdateView,
)
from VAT.web_api_catalogos_forms import CatalogoEscrituraView
from VAT.web_api_common import campo_formulario, texto

# Campos que dibuja la plantilla nativa ``comision_form.html``; ``acepta_lista_espera`` no está (se conserva).
CAMPOS_OFERTA = (
    "oferta",
    "ubicacion",
    "codigo_comision",
    "nombre",
    "fecha_inicio",
    "fecha_fin",
    "cupo",
    "estado",
    "observaciones",
)


def _con_guarda(native_class):
    """La vista nativa con el ``dispatch`` intacto (guarda de ``?curso=``) y sin ejecutar su ``get``/``post``."""

    class _Guarda(native_class):
        def get(self, request, *args, **kwargs):
            return HttpResponse()

        post = get

    return _Guarda


class ComisionEscrituraView(CatalogoEscrituraView):
    """Base de las vistas de escritura de comisiones: corre la vista nativa sobre su objeto (404 si no existe)."""

    alta = False
    guarda_dispatch = False

    def preparar(self, kwargs):
        if self.alta and self.guarda_dispatch:
            # ``ComisionCursoCreateView.dispatch``: el curso enviado debe ser editable por el usuario.
            vista = _con_guarda(self.native_class)()
            django_request = self.request._request  # pylint: disable=protected-access
            vista.setup(django_request, **kwargs)
            vista.dispatch(django_request, **kwargs)
            vista.object = None
            return vista
        return super().preparar(kwargs)

    def objeto(self, vista):
        return None if self.alta else vista.get_object()

    @staticmethod
    def destino(respuesta):
        return Response({"ok": True, "redirect": respuesta["Location"]})


class ComisionFormView(ComisionEscrituraView):
    """``GET|POST`` del formulario de comisión (alta y edición)."""

    campos = None
    lista = ""
    detalle = ""

    def get(self, request, **kwargs):
        vista = self.preparar(kwargs)
        return self.formulario(vista, vista.get_form())

    def post(self, request, **kwargs):
        vista = self.preparar(kwargs)
        form = vista.get_form()
        if form.is_valid():
            return self.destino(vista.form_valid(form))
        return self.formulario(vista, form, status=400)

    def formulario(self, vista, form, status=200):
        editando = form.instance.pk is not None
        nombres = self.campos or tuple(form.fields)
        cuerpo = {
            "editing": editando,
            "fields": [
                {
                    **campo_formulario(form[nombre]),
                    "required": form.fields[nombre].required,
                }
                for nombre in nombres
            ],
            "non_field_errors": [str(e) for e in form.non_field_errors()],
            "urls": {"list": reverse(self.lista)},
            "messages": self.mensajes() if status == 400 else [],
        }
        cuerpo.update(self.extra(vista, form, editando))
        return Response(cuerpo, status=status)

    def extra(self, vista, form, editando):  # pylint: disable=unused-argument
        return {}


class ComisionOfertaFormView(ComisionFormView):
    """Formulario de comisión de oferta: el subtítulo del encabezado y el enlace al detalle son los de la plantilla."""

    campos = CAMPOS_OFERTA
    lista = "vat_comision_list"

    def extra(self, vista, form, editando):
        if not editando:
            return {
                "subtitulo": "",
                "urls": {"list": reverse(self.lista), "detail": ""},
            }
        return {
            "subtitulo": texto(
                "{{ i.codigo_comision }} — {{ i.nombre }}", i=form.instance
            ),
            "urls": {
                "list": reverse(self.lista),
                "detail": reverse("vat_comision_detail", args=[form.instance.pk]),
            },
        }


class ComisionCursoFormView(ComisionFormView):
    """Formulario de comisión de curso: todos los campos del formulario y la ruta de cancelación nativa."""

    lista = "vat_centro_list"

    def extra(self, vista, form, editando):
        if not editando:
            return {"urls": {"list": reverse(self.lista), "cancel": ""}}
        centro_id = form.instance.curso.centro_id
        return {
            "urls": {
                "list": reverse(self.lista),
                "cancel": f"{reverse('vat_centro_detail', args=[centro_id])}#cursos",
            }
        }


class ComisionBajaView(ComisionEscrituraView):
    """``GET|POST`` de la confirmación y la baja lógica nativa de una comisión."""

    titulo = ""
    subtitulo = ""
    contexto = ""

    def get(self, request, **kwargs):
        vista = self.preparar(kwargs)
        objeto = {self.contexto: vista.object}
        return Response(
            {
                "titulo": texto(self.titulo, **objeto),
                "subtitulo": texto(self.subtitulo, **objeto) if self.subtitulo else "",
                "urls": {"detail": self.cancelar(vista.object)},
            }
        )

    def post(self, request, **kwargs):
        vista = self.preparar(kwargs)
        return self.destino(vista.post(vista.request, **kwargs))

    def cancelar(self, objeto):
        raise NotImplementedError


class ComisionCreateWebView(ComisionOfertaFormView):
    native_class = ComisionCreateView
    codigos = ["VAT.add_comision"]
    alta = True


class ComisionUpdateWebView(ComisionOfertaFormView):
    native_class = ComisionUpdateView
    codigos = ["VAT.change_comision"]


class ComisionDeleteWebView(ComisionBajaView):
    native_class = ComisionDeleteView
    codigos = ["VAT.delete_comision"]
    titulo = "{{ comision.codigo_comision }} - {{ comision.nombre }}"
    subtitulo = "{{ comision.oferta }}"
    contexto = "comision"

    def cancelar(self, objeto):
        return reverse("vat_comision_detail", args=[objeto.pk])


class ComisionCursoCreateWebView(ComisionCursoFormView):
    native_class = ComisionCursoCreateView
    codigos = ["VAT.add_comisioncurso"]
    alta = True
    guarda_dispatch = True


class ComisionCursoUpdateWebView(ComisionCursoFormView):
    native_class = ComisionCursoUpdateView
    codigos = ["VAT.change_comisioncurso"]


class ComisionCursoDeleteWebView(ComisionBajaView):
    native_class = ComisionCursoDeleteView
    codigos = ["VAT.delete_comisioncurso"]
    titulo = "{{ comision_curso.codigo_comision }} - {{ comision_curso.nombre }}"
    contexto = "comision_curso"

    def cancelar(self, objeto):
        return f"{reverse('vat_centro_detail', args=[objeto.curso.centro_id])}#cursos"
