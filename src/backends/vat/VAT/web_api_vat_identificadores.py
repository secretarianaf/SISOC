"""Web API (G1 v1) de identificadores históricos de institución de VAT (V06.01).

``/api/web/vat/institucion/identificadores/`` corre las vistas nativas ``InstitucionIdentificadorHist{List,Detail,Create,Update,Delete}View``
y proyecta su contexto: lista (filtros ``centro_id``, ``tipo_identificador`` y ``busqueda``), detalle, formulario (alta y edición,
con ``form_valid`` nativo y su mensaje; ``?centro=`` preselecciona el centro) y baja nativa.
Acceso: ``VAT.view/add/change/delete_institucionidentificadorhist``, como cada ruta.
"""

from django.urls import reverse
from rest_framework.response import Response

from VAT.views.institucion import (
    InstitucionIdentificadorHistCreateView,
    InstitucionIdentificadorHistDeleteView,
    InstitucionIdentificadorHistDetailView,
    InstitucionIdentificadorHistListView,
    InstitucionIdentificadorHistUpdateView,
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
_ROL = "{{ v|default:'—' }}"
_LISTA = "vat_institucion_identificador_list"
# The native template renders these widgets only (``ubicacion`` is a form field it never draws).
_CAMPOS = (
    "centro",
    "tipo_identificador",
    "valor_identificador",
    "rol_institucional",
    "es_actual",
    "vigencia_hasta",
    "motivo",
)


class IdentificadorListWebView(VatNativeReadView):
    """``GET .../institucion/identificadores/``: ``identificador_list.html``."""

    native_class = InstitucionIdentificadorHistListView
    codigos = ["VAT.view_institucionidentificadorhist"]

    def get(self, request):
        user = request.user

        def extra(context, _request):
            return {
                "results": [
                    {
                        "id": i.pk,
                        "centro": i.centro.nombre,
                        "tipo": i.get_tipo_identificador_display(),
                        "valor": i.valor_identificador,
                        "rol": texto(_ROL, v=i.get_rol_institucional_display()),
                        "es_actual": bool(i.es_actual),
                        "detail_url": reverse(
                            "vat_institucion_identificador_detail", args=[i.pk]
                        ),
                        "update_url": reverse(
                            "vat_institucion_identificador_update", args=[i.pk]
                        ),
                        "delete_url": reverse(
                            "vat_institucion_identificador_delete", args=[i.pk]
                        ),
                    }
                    for i in context["identificadores"]
                ],
                "busqueda": request.GET.get("busqueda", ""),
                "permisos": {
                    "editar": user.has_perm("VAT.change_institucionidentificadorhist"),
                    "eliminar": user.has_perm(
                        "VAT.delete_institucionidentificadorhist"
                    ),
                },
                "urls": {
                    "list": reverse(_LISTA),
                    "create": reverse("vat_institucion_identificador_create"),
                },
            }

        return self.lista(extra)


class IdentificadorDetailWebView(VatNativeReadView):
    """``GET .../institucion/identificadores/<pk>/``: ``identificador_detail.html``."""

    native_class = InstitucionIdentificadorHistDetailView
    codigos = ["VAT.view_institucionidentificadorhist"]

    def get(self, request, pk):
        vista, _context = self.detalle(pk)
        i = vista.object
        return Response(
            {
                "id": i.pk,
                "title": str(i),
                "centro": i.centro.nombre,
                "tipo": i.get_tipo_identificador_display(),
                "valor": i.valor_identificador,
                "rol": texto(_ROL, v=i.get_rol_institucional_display()),
                "es_actual": bool(i.es_actual),
                "vigencia_hasta": texto(_VIGENCIA, v=i.vigencia_hasta),
                "motivo": texto(_ROL, v=i.motivo),
                "creado": texto(_FECHA_HORA, v=i.fecha_creacion),
                "modificado": texto(_FECHA_HORA, v=i.fecha_modificacion),
                "urls": {
                    "list": reverse(_LISTA),
                    "update": reverse(
                        "vat_institucion_identificador_update", args=[i.pk]
                    ),
                    "delete": reverse(
                        "vat_institucion_identificador_delete", args=[i.pk]
                    ),
                },
                "messages": mensajes_pendientes(
                    request._request  # pylint: disable=protected-access
                ),
            }
        )


class IdentificadorCreateWebView(VatFormWebView):
    """``GET|POST .../institucion/identificadores/nuevo/`` (``?centro=<id>`` preselects the centro)."""

    native_class = InstitucionIdentificadorHistCreateView
    codigos = ["VAT.add_institucionidentificadorhist"]
    crear = True
    lista_name = _LISTA

    def extra(self, vista, form):
        return {"fields": [campo_formulario(form[nombre]) for nombre in _CAMPOS]}


class IdentificadorUpdateWebView(IdentificadorCreateWebView):
    """``GET|POST .../institucion/identificadores/<pk>/editar/``."""

    native_class = InstitucionIdentificadorHistUpdateView
    codigos = ["VAT.change_institucionidentificadorhist"]
    crear = False


class IdentificadorDeleteWebView(VatBajaWebView):
    """``GET|POST .../institucion/identificadores/<pk>/eliminar/``."""

    native_class = InstitucionIdentificadorHistDeleteView
    codigos = ["VAT.delete_institucionidentificadorhist"]

    def resumen(self, objeto):
        return {
            "valor": objeto.valor_identificador,
            "tipo": objeto.get_tipo_identificador_display(),
            "centro": objeto.centro.nombre,
            "urls": {
                "detail": reverse(
                    "vat_institucion_identificador_detail", args=[objeto.pk]
                )
            },
        }
