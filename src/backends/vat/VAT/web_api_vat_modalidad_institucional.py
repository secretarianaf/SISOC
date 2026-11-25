"""Web API (G1 v1) de modalidades institucionales de VAT (V06.01).

``/api/web/vat/modalidades-institucionales/`` corre las vistas nativas
``ModalidadInstitucional{List,Detail,Create,Update,Delete}View`` y proyecta su contexto: lista
(filtro ``activo``), detalle, formulario (alta y edición, con ``form_valid`` nativo y su mensaje) y
baja nativa. Acceso: ``VAT.view/add/change/delete_modalidadinstitucional``, como cada ruta.
"""

from django.urls import reverse
from rest_framework.response import Response

from VAT.views.modalidad_institucional import (
    ModalidadInstitucionalCreateView,
    ModalidadInstitucionalDeleteView,
    ModalidadInstitucionalDetailView,
    ModalidadInstitucionalListView,
    ModalidadInstitucionalUpdateView,
)
from VAT.web_api_common import VatNativeReadView, mensajes_pendientes, texto
from VAT.web_api_vat_centros_base import VatBajaWebView, VatFormWebView

_FECHA = "{{ v|date:'d/m/Y' }}"
_FECHA_HORA = "{{ v|date:'d/m/Y H:i' }}"
_DESCRIPCION = "{{ v|truncatewords:10|default:'—' }}"
_LISTA = "vat_modalidad_institucional_list"


class ModalidadListWebView(VatNativeReadView):
    """``GET .../modalidades-institucionales/``: ``list.html``."""

    native_class = ModalidadInstitucionalListView
    codigos = ["VAT.view_modalidadinstitucional"]

    def get(self, request):
        user = request.user

        def extra(context, _request):
            return {
                "results": [
                    {
                        "id": m.pk,
                        "nombre": m.nombre,
                        "descripcion": texto(_DESCRIPCION, v=m.descripcion),
                        "activo": bool(m.activo),
                        "creado": texto(_FECHA, v=m.fecha_creacion),
                        "detail_url": reverse(
                            "vat_modalidad_institucional_detail", args=[m.pk]
                        ),
                        "update_url": reverse(
                            "vat_modalidad_institucional_update", args=[m.pk]
                        ),
                        "delete_url": reverse(
                            "vat_modalidad_institucional_delete", args=[m.pk]
                        ),
                    }
                    for m in context["modalidades"]
                ],
                "busqueda": request.GET.get("busqueda", ""),
                "permisos": {
                    "editar": user.has_perm("VAT.change_modalidadinstitucional"),
                    "eliminar": user.has_perm("VAT.delete_modalidadinstitucional"),
                },
                "urls": {
                    "list": reverse(_LISTA),
                    "create": reverse("vat_modalidad_institucional_create"),
                },
            }

        return self.lista(extra)


class ModalidadDetailWebView(VatNativeReadView):
    """``GET .../modalidades-institucionales/<pk>/``: ``detail.html``."""

    native_class = ModalidadInstitucionalDetailView
    codigos = ["VAT.view_modalidadinstitucional"]

    def get(self, request, pk):
        vista, _context = self.detalle(pk)
        m = vista.object
        return Response(
            {
                "id": m.pk,
                "nombre": m.nombre,
                "descripcion": m.descripcion or "",
                "activo": bool(m.activo),
                "creado": texto(_FECHA_HORA, v=m.fecha_creacion),
                "modificado": texto(_FECHA_HORA, v=m.fecha_modificacion),
                "urls": {
                    "list": reverse(_LISTA),
                    "update": reverse(
                        "vat_modalidad_institucional_update", args=[m.pk]
                    ),
                    "delete": reverse(
                        "vat_modalidad_institucional_delete", args=[m.pk]
                    ),
                },
                "messages": mensajes_pendientes(
                    request._request  # pylint: disable=protected-access
                ),
            }
        )


class ModalidadCreateWebView(VatFormWebView):
    """``GET|POST .../modalidades-institucionales/nueva/``."""

    native_class = ModalidadInstitucionalCreateView
    codigos = ["VAT.add_modalidadinstitucional"]
    crear = True
    lista_name = _LISTA


class ModalidadUpdateWebView(ModalidadCreateWebView):
    """``GET|POST .../modalidades-institucionales/<pk>/editar/``."""

    native_class = ModalidadInstitucionalUpdateView
    codigos = ["VAT.change_modalidadinstitucional"]
    crear = False


class ModalidadDeleteWebView(VatBajaWebView):
    """``GET|POST .../modalidades-institucionales/<pk>/eliminar/``."""

    native_class = ModalidadInstitucionalDeleteView
    codigos = ["VAT.delete_modalidadinstitucional"]

    def resumen(self, objeto):
        return {
            "nombre": objeto.nombre,
            "urls": {
                "detail": reverse(
                    "vat_modalidad_institucional_detail", args=[objeto.pk]
                )
            },
        }
