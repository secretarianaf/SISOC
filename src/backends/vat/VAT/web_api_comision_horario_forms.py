"""Web API (G1 v1) del alta, edición y baja de los horarios de comisión de VAT (V04.02, U5).

``/api/web/vat/comisiones-horarios/`` (oferta) y ``/api/web/vat/comisiones-horarios/cursos/`` (curso) suman
``nuevo/``, ``<pk>/editar/`` y ``<pk>/eliminar/``: corren las vistas nativas (``ComisionHorario*View`` y
``ComisionCursoHorario*View``), su formulario, su ``form_valid`` (guardado, regeneración de clases y mensaje) y su baja.
El POST responde ``{"ok": true, "redirect": <url>}`` o, con el formulario inválido, 400 con los campos y errores.
Acceso: ``VAT.add|change|delete_comisionhorario``, igual que las rutas nativas.
"""

from django.urls import reverse
from rest_framework.response import Response

from VAT.views.curso import (
    ComisionCursoHorarioCreateView,
    ComisionCursoHorarioDeleteView,
    ComisionCursoHorarioUpdateView,
)
from VAT.views.oferta_institucional import (
    ComisionHorarioCreateView,
    ComisionHorarioDeleteView,
    ComisionHorarioUpdateView,
)
from VAT.web_api_catalogos_forms import CatalogoEscrituraView
from VAT.web_api_common import campo_formulario, texto

_TITULO = '{{ horario.dia_semana }} {{ horario.hora_desde|time:"H:i" }}-{{ horario.hora_hasta|time:"H:i" }}'


class HorarioEscrituraView(CatalogoEscrituraView):
    """Base de las vistas de escritura de horarios: corre la vista nativa sobre su objeto (404 si no existe)."""

    def destino(self, vista, respuesta):
        """Redirección de la vista nativa; ``get_success_url`` si respondió otra cosa (``X-Requested-With``)."""
        if respuesta.status_code == 302:
            return self.redireccion(respuesta)
        return Response({"ok": True, "redirect": str(vista.get_success_url())})


class HorarioFormView(HorarioEscrituraView):
    """``GET|POST`` del formulario de horario (alta y edición)."""

    alta = False
    campo = "comision"

    def objeto(self, vista):
        return None if self.alta else vista.get_object()

    def get(self, request, **kwargs):
        vista = self.preparar(kwargs)
        return self.formulario(vista.get_form())

    def post(self, request, **kwargs):
        vista = self.preparar(kwargs)
        form = vista.get_form()
        if form.is_valid():
            return self.destino(vista, vista.form_valid(form))
        return self.formulario(form, status=400)

    def formulario(self, form, status=200):
        return Response(
            {
                "editing": form.instance.pk is not None,
                "campo": self.campo,
                "fields": [campo_formulario(form[nombre]) for nombre in form.fields],
                "non_field_errors": [str(e) for e in form.non_field_errors()],
                "urls": {"list": reverse("vat_comision_horario_list")},
                "messages": self.mensajes() if status == 400 else [],
            },
            status=status,
        )


class HorarioDeleteView(HorarioEscrituraView):
    """``GET|POST`` de la confirmación y la baja nativa de un horario."""

    def get(self, request, **kwargs):
        horario = self.preparar(kwargs).object
        return Response(
            {
                "titulo": texto(_TITULO, horario=horario),
                # La plantilla nativa imprime ``horario.comision``: el horario de un curso la tiene vacía («None»).
                "subtitulo": texto("{{ horario.comision }}", horario=horario),
                "urls": {
                    "detail": reverse("vat_comision_horario_detail", args=[horario.pk])
                },
            }
        )

    def post(self, request, **kwargs):
        vista = self.preparar(kwargs)
        return self.destino(vista, vista.post(vista.request, **kwargs))


class ComisionHorarioCreateWebView(HorarioFormView):
    native_class = ComisionHorarioCreateView
    codigos = ["VAT.add_comisionhorario"]
    alta = True


class ComisionHorarioUpdateWebView(HorarioFormView):
    native_class = ComisionHorarioUpdateView
    codigos = ["VAT.change_comisionhorario"]


class ComisionHorarioDeleteWebView(HorarioDeleteView):
    native_class = ComisionHorarioDeleteView
    codigos = ["VAT.delete_comisionhorario"]


class ComisionCursoHorarioCreateWebView(HorarioFormView):
    native_class = ComisionCursoHorarioCreateView
    codigos = ["VAT.add_comisionhorario"]
    alta = True
    campo = "comision_curso"


class ComisionCursoHorarioUpdateWebView(HorarioFormView):
    native_class = ComisionCursoHorarioUpdateView
    codigos = ["VAT.change_comisionhorario"]
    campo = "comision_curso"


class ComisionCursoHorarioDeleteWebView(HorarioDeleteView):
    native_class = ComisionCursoHorarioDeleteView
    codigos = ["VAT.delete_comisionhorario"]
