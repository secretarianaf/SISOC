"""Web API (G1 v1) de ubicaciones de institución de VAT (V06.01).

``/api/web/vat/institucion/ubicaciones/`` corre las vistas nativas ``InstitucionUbicacion{List,Detail,Create,Update,Delete}View``
y proyecta su contexto: lista (filtros ``centro_id``, ``rol_ubicacion`` y ``busqueda``), detalle, formulario (alta y edición,
con la guarda de ``dispatch`` y el ``form_valid`` nativos y su mensaje; ``?centro=`` bloquea el centro como la vista nativa)
y baja nativa. El formulario lleva las URLs de la cascada Departamento -> Localidad que consulta ``ubicacion_form.html``.
Acceso: ``VAT.view/add/change/delete_institucionubicacion``, como cada ruta.
"""

from django.core.exceptions import PermissionDenied
from django.urls import reverse
from rest_framework.response import Response

from VAT.models import Centro
from VAT.services.access_scope import can_user_edit_centro
from VAT.views.institucion import (
    InstitucionUbicacionCreateView,
    InstitucionUbicacionDeleteView,
    InstitucionUbicacionDetailView,
    InstitucionUbicacionListView,
    InstitucionUbicacionUpdateView,
)
from VAT.web_api_common import (
    VatNativeReadView,
    campo_formulario,
    mensajes_pendientes,
    texto,
)
from VAT.web_api_vat_centros_base import VatBajaWebView, VatFormWebView

_FECHA_HORA = "{{ v|date:'d/m/Y H:i' }}"
_VIGENCIA = "{{ v|date:'d/m/Y'|default:'Vigente' }}"
_VACIO = "{{ v|default:'—' }}"
_DOMICILIO = "{{ v|default:'—'|truncatechars:40 }}"
_LISTA = "vat_institucion_ubicacion_list"
# The native template renders these widgets only (``nombre_ubicacion`` is a form field it never draws).
_CAMPOS = (
    "centro",
    "departamento",
    "localidad",
    "rol_ubicacion",
    "domicilio",
    "es_principal",
    "observaciones",
)


def _campo(form, nombre):
    """The field as its native widget renders it (a locked field is ``disabled``)."""
    bound = form[nombre]
    if nombre == "localidad":
        # ``LocalidadSelectBajoDemanda`` draws only the chosen option; the rest comes by AJAX. The
        # field keeps those options so the projection does not walk every localidad of the province.
        widget = bound.field.widget
        grupos = widget.optgroups(bound.html_name, widget.format_value(bound.value()))
        bound.field.choices = [
            (o["value"], o["label"])
            for _nombre, opciones, _i in grupos
            for o in opciones
        ]
    campo = campo_formulario(bound)
    if form.fields[nombre].disabled:
        campo["attrs"]["disabled"] = "disabled"
    return campo


class UbicacionListWebView(VatNativeReadView):
    """``GET .../institucion/ubicaciones/``: ``ubicacion_list.html``."""

    native_class = InstitucionUbicacionListView
    codigos = ["VAT.view_institucionubicacion"]

    def get(self, request):
        user = request.user

        def extra(context, _request):
            return {
                "results": [
                    {
                        "id": u.pk,
                        "centro": u.centro.nombre,
                        "localidad": str(u.localidad),
                        "rol": u.get_rol_ubicacion_display(),
                        "domicilio": texto(_DOMICILIO, v=u.domicilio),
                        "es_principal": bool(u.es_principal),
                        "detail_url": reverse(
                            "vat_institucion_ubicacion_detail", args=[u.pk]
                        ),
                        "update_url": reverse(
                            "vat_institucion_ubicacion_update", args=[u.pk]
                        ),
                        "delete_url": reverse(
                            "vat_institucion_ubicacion_delete", args=[u.pk]
                        ),
                    }
                    for u in context["ubicaciones"]
                ],
                "busqueda": request.GET.get("busqueda", ""),
                "permisos": {
                    "editar": user.has_perm("VAT.change_institucionubicacion"),
                    "eliminar": user.has_perm("VAT.delete_institucionubicacion"),
                },
                "urls": {
                    "list": reverse(_LISTA),
                    "create": reverse("vat_institucion_ubicacion_create"),
                },
            }

        return self.lista(extra)


class UbicacionDetailWebView(VatNativeReadView):
    """``GET .../institucion/ubicaciones/<pk>/``: ``ubicacion_detail.html``."""

    native_class = InstitucionUbicacionDetailView
    codigos = ["VAT.view_institucionubicacion"]

    def get(self, request, pk):
        vista, _context = self.detalle(pk)
        u = vista.object
        return Response(
            {
                "id": u.pk,
                "title": str(u),
                "centro": u.centro.nombre,
                "rol": u.get_rol_ubicacion_display(),
                "localidad": str(u.localidad),
                "domicilio": texto(_VACIO, v=u.domicilio),
                "es_principal": bool(u.es_principal),
                "vigencia_hasta": texto(_VIGENCIA, v=u.vigencia_hasta),
                "latitud": texto(_VACIO, v=u.latitud),
                "longitud": texto(_VACIO, v=u.longitud),
                "observaciones": u.observaciones or "",
                "creado": texto(_FECHA_HORA, v=u.fecha_creacion),
                "modificado": texto(_FECHA_HORA, v=u.fecha_modificacion),
                "urls": {
                    "list": reverse(_LISTA),
                    "update": reverse("vat_institucion_ubicacion_update", args=[u.pk]),
                    "delete": reverse("vat_institucion_ubicacion_delete", args=[u.pk]),
                },
                "messages": mensajes_pendientes(
                    request._request  # pylint: disable=protected-access
                ),
            }
        )


class UbicacionCreateWebView(VatFormWebView):
    """``GET|POST .../institucion/ubicaciones/nuevo/`` (``?centro=<id>`` locks the centro)."""

    native_class = InstitucionUbicacionCreateView
    codigos = ["VAT.add_institucionubicacion"]
    crear = True
    lista_name = _LISTA

    def preparar(self, kwargs):
        # ``InstitucionUbicacionCreateView.dispatch``: the centro sent must be editable by the user.
        django_request = self.request._request  # pylint: disable=protected-access
        centro_id = django_request.GET.get("centro") or django_request.POST.get(
            "centro"
        )
        if centro_id:
            try:
                centro = Centro.objects.get(pk=centro_id)
            except (Centro.DoesNotExist, TypeError, ValueError) as exc:
                raise PermissionDenied from exc
            if not can_user_edit_centro(django_request.user, centro):
                raise PermissionDenied
        return super().preparar(kwargs)

    def cancelar(self, vista):  # pylint: disable=unused-argument
        return reverse(_LISTA)

    def formulario(self, vista, form, status=200):
        return Response(
            {
                "editing": form.instance.pk is not None,
                "non_field_errors": [str(e) for e in form.non_field_errors()],
                **self.extra(vista, form),
            },
            status=status,
        )

    def extra(self, vista, form):
        return {
            "fields": [_campo(form, nombre) for nombre in _CAMPOS],
            "urls": {
                "list": self.cancelar(vista),
                "municipios": reverse("vat_ajax_municipios_por_centro"),
                "localidades": reverse("ajax_load_localidades"),
            },
        }


class UbicacionUpdateWebView(UbicacionCreateWebView):
    """``GET|POST .../institucion/ubicaciones/<pk>/editar/``."""

    native_class = InstitucionUbicacionUpdateView
    codigos = ["VAT.change_institucionubicacion"]
    crear = False

    def preparar(self, kwargs):
        return VatFormWebView.preparar(self, kwargs)

    def cancelar(self, vista):
        return vista.get_success_url()


class UbicacionDeleteWebView(VatBajaWebView):
    """``GET|POST .../institucion/ubicaciones/<pk>/eliminar/``."""

    native_class = InstitucionUbicacionDeleteView
    codigos = ["VAT.delete_institucionubicacion"]

    def resumen(self, objeto):
        return {
            "rol": objeto.get_rol_ubicacion_display(),
            "localidad": str(objeto.localidad),
            "centro": objeto.centro.nombre,
            "urls": {
                "detail": reverse("vat_institucion_ubicacion_detail", args=[objeto.pk])
            },
        }
