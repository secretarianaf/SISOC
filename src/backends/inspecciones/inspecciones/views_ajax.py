"""Búsquedas AJAX de los Select2 del panel (respuesta ``{"results": [...]}``)."""

from django.http import JsonResponse
from django.views import View

from inspecciones.forms import AsignacionForm
from inspecciones.services.asignaciones import buscar_inspectores, otras_asignaciones
from inspecciones.services.catalogo import buscar_escuelas_select
from inspecciones.services.geografia import opciones_de_localidad
from inspecciones.views import GestionInspeccionesMixin


class _AjaxView(GestionInspeccionesMixin, View):
    http_method_names = ["get"]

    def resultados(self, request):
        raise NotImplementedError

    def get(self, request):
        return JsonResponse({"results": self.resultados(request)})


class LocalidadesAjaxView(_AjaxView):
    """Localidades de la provincia, con el municipio ("Localidad · Municipio")."""

    def resultados(self, request):
        provincia = request.GET.get("provincia", "")
        if not provincia.isdigit():
            return []
        return opciones_de_localidad(int(provincia), request.GET.get("q", ""))


class InspectoresAjaxView(_AjaxView):
    """Desde 3 letras: usuario, nombre, apellido o DNI; hasta 20.

    Por defecto sólo rol inspector (alta de asignaciones). ``alcance=programa``
    suma a coordinación, para los filtros de los listados.
    """

    def resultados(self, request):
        return buscar_inspectores(
            request.GET.get("q", ""),
            solo_inspectores=request.GET.get("alcance") != "programa",
        )


class EscuelasAjaxView(_AjaxView):
    """Desde 3 letras: nombre, Cueanexo o domicilio; hasta 20."""

    def resultados(self, request):
        return buscar_escuelas_select(request.GET.get("q", ""))


class VerificarAsignacionAjaxView(GestionInspeccionesMixin, View):
    """Aviso del modal: quién más tiene asignada la escuela esa jornada."""

    http_method_names = ["get"]

    def get(self, request):
        form = AsignacionForm(request.GET)
        form.is_valid()
        datos = getattr(form, "cleaned_data", {})
        escuela, fecha = datos.get("escuela"), datos.get("fecha")
        if not (escuela and fecha):
            return JsonResponse({"otras": []})
        inspector = datos.get("inspector")
        return JsonResponse(
            {
                "escuela": escuela.nombre,
                "otras": otras_asignaciones(
                    escuela,
                    fecha,
                    excluir_inspector_id=inspector.pk if inspector else None,
                ),
            }
        )
