"""Web API (G1 v1) del alta, edición y baja de los catálogos de VAT (V07.02).

``/api/web/vat/catalogos/{sectores,subsectores,modalidades-cursado,titulos-referencia}/`` suma ``nuevo|nueva/``,
``<pk>/editar/`` y ``<pk>/eliminar/``: corren las vistas nativas (``*CreateView``, ``*UpdateView``, ``*DeleteView``),
su formulario, su ``form_valid`` (mensaje y guardado) y su baja. El POST responde ``{"ok": true, "redirect": <url>}``
o, con el formulario inválido, 400 con los campos y errores. Acceso: ``VAT.add|change|delete_<modelo>``.
"""

from django.http import Http404
from django.urls import reverse
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from VAT.views.catalogo import (
    ModalidadCursadaCreateView,
    ModalidadCursadaDeleteView,
    ModalidadCursadaUpdateView,
    SectorCreateView,
    SectorDeleteView,
    SectorUpdateView,
    SubsectorCreateView,
    SubsectorDeleteView,
    SubsectorUpdateView,
    TituloReferenciaCreateView,
    TituloReferenciaDeleteView,
    TituloReferenciaUpdateView,
)
from VAT.web_api_common import (
    VatNativeReadView,
    campo_formulario,
    mensajes_pendientes,
    texto,
)


class CatalogoEscrituraView(VatNativeReadView):
    """Base de las vistas de escritura: corre la vista nativa sobre su objeto (404 si no existe)."""

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

    def mensajes(self):
        django_request = self.request._request  # pylint: disable=protected-access
        return mensajes_pendientes(django_request)


class CatalogoFormView(CatalogoEscrituraView):
    """``GET|POST`` de un formulario de catálogo (alta y edición)."""

    lista = ""
    con_contexto = False

    def get(self, request, **kwargs):
        vista = self.preparar(kwargs)
        return self.formulario(vista, vista.get_form())

    def post(self, request, **kwargs):
        vista = self.preparar(kwargs)
        form = vista.get_form()
        if form.is_valid():
            return self.redireccion(vista.form_valid(form))
        return self.formulario(vista, form, status=400)

    def formulario(self, vista, form, status=200):
        cuerpo = {
            "editing": form.instance.pk is not None,
            "fields": [campo_formulario(form[nombre]) for nombre in form.fields],
            "non_field_errors": [str(e) for e in form.non_field_errors()],
            "urls": {"list": reverse(self.lista), "vat": reverse("vat_centro_list")},
            "messages": self.mensajes() if status == 400 else [],
        }
        if self.con_contexto:
            context = vista.get_context_data(form=form)
            cuerpo["page"] = {
                clave: str(context[clave])
                for clave in ("page_title", "page_description", "submit_text")
            }
            cuerpo["urls"]["cancel"] = str(context["cancel_url"])
        return Response(cuerpo, status=status)


class CatalogoDeleteView(CatalogoEscrituraView):
    """``GET|POST`` de la confirmación y la baja nativa de un catálogo."""

    detalle = ""
    # Plantillas del texto «¿Eliminar <strong>…</strong>?» con el contexto de la vista nativa.
    nombre = ""
    sector = ""

    def get(self, request, **kwargs):
        vista = self.preparar(kwargs)
        context = vista.get_context_data(object=vista.object)
        return Response(
            {
                "nombre": texto(self.nombre, **context),
                "sector": texto(self.sector, **context) if self.sector else "",
                "urls": {"detail": reverse(self.detalle, args=[vista.object.pk])},
            }
        )

    def post(self, request, **kwargs):
        vista = self.preparar(kwargs)
        return self.redireccion(vista.post(vista.request, **kwargs))


def _crear(native, accion, modelo, lista, con_contexto=False):
    class _Vista(CatalogoFormView):
        native_class = native
        codigos = [f"VAT.{accion}_{modelo}"]

        def objeto(self, vista):
            return None if accion == "add" else vista.get_object()

    _Vista.lista = lista
    _Vista.con_contexto = con_contexto
    return _Vista


def _baja(native, modelo, detalle, nombre, sector=""):
    class _Vista(CatalogoDeleteView):
        native_class = native
        codigos = [f"VAT.delete_{modelo}"]

    _Vista.detalle = detalle
    _Vista.nombre = nombre
    _Vista.sector = sector
    return _Vista


SectorCreateWebView = _crear(SectorCreateView, "add", "sector", "vat_sector_list")
SectorUpdateWebView = _crear(SectorUpdateView, "change", "sector", "vat_sector_list")
SectorDeleteWebView = _baja(
    SectorDeleteView, "sector", "vat_sector_detail", "{{ sector.nombre }}"
)
SubsectorCreateWebView = _crear(
    SubsectorCreateView, "add", "subsector", "vat_subsector_list"
)
SubsectorUpdateWebView = _crear(
    SubsectorUpdateView, "change", "subsector", "vat_subsector_list"
)
SubsectorDeleteWebView = _baja(
    SubsectorDeleteView,
    "subsector",
    "vat_subsector_detail",
    "{{ subsector.nombre }}",
    "{{ subsector.sector.nombre }}",
)
ModalidadCursadaCreateWebView = _crear(
    ModalidadCursadaCreateView,
    "add",
    "modalidadcursada",
    "vat_modalidadcursada_list",
    con_contexto=True,
)
ModalidadCursadaUpdateWebView = _crear(
    ModalidadCursadaUpdateView,
    "change",
    "modalidadcursada",
    "vat_modalidadcursada_list",
    con_contexto=True,
)
ModalidadCursadaDeleteWebView = _baja(
    ModalidadCursadaDeleteView,
    "modalidadcursada",
    "vat_modalidadcursada_detail",
    "{{ modalidad.nombre }}",
)
TituloReferenciaCreateWebView = _crear(
    TituloReferenciaCreateView, "add", "tituloreferencia", "vat_titulorreferencia_list"
)
TituloReferenciaUpdateWebView = _crear(
    TituloReferenciaUpdateView,
    "change",
    "tituloreferencia",
    "vat_titulorreferencia_list",
)
# La plantilla nativa imprime ``titulo.nombre`` pero la vista expone ``tituloreferencia``.
TituloReferenciaDeleteWebView = _baja(
    TituloReferenciaDeleteView,
    "tituloreferencia",
    "vat_titulorreferencia_detail",
    "{{ tituloreferencia.nombre }}",
)
