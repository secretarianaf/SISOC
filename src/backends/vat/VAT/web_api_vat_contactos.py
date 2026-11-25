"""Web API (G1 v1) de contactos de institución de VAT (V06.01).

``/api/web/vat/institucion/contactos/`` corre las vistas nativas ``InstitucionContacto{List,Detail,Create,Update,Delete}View``
y proyecta su contexto: lista (filtros ``centro_id``, ``tipo`` y ``busqueda``), detalle, formulario (alta y edición,
con ``form_valid`` nativo y su mensaje; ``?centro=`` bloquea el centro como la vista nativa) y baja nativa.
Acceso: ``VAT.view/add/change/delete_institucioncontacto``, como cada ruta.
"""

from django.urls import reverse
from rest_framework.response import Response

from VAT.views.institucion import (
    InstitucionContactoCreateView,
    InstitucionContactoDeleteView,
    InstitucionContactoDetailView,
    InstitucionContactoListView,
    InstitucionContactoUpdateView,
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
_LISTA = "vat_institucion_contacto_list"


def campos_con_bloqueo(form):
    """Fields as the native widgets render them, with ``disabled`` for a locked field."""
    campos = []
    for nombre in form.fields:
        campo = campo_formulario(form[nombre])
        if form.fields[nombre].disabled:
            campo["attrs"]["disabled"] = "disabled"
        campos.append(campo)
    return campos


class ContactoListWebView(VatNativeReadView):
    """``GET .../institucion/contactos/``: ``contacto_list.html``."""

    native_class = InstitucionContactoListView
    codigos = ["VAT.view_institucioncontacto"]

    def get(self, request):
        user = request.user

        def extra(context, _request):
            return {
                "results": [
                    {
                        "id": c.pk,
                        "centro": c.centro.nombre,
                        "tipo": c.get_tipo_display(),
                        "valor": c.valor,
                        "es_principal": bool(c.es_principal),
                        "detail_url": reverse(
                            "vat_institucion_contacto_detail", args=[c.pk]
                        ),
                        "update_url": reverse(
                            "vat_institucion_contacto_update", args=[c.pk]
                        ),
                        "delete_url": reverse(
                            "vat_institucion_contacto_delete", args=[c.pk]
                        ),
                    }
                    for c in context["contactos"]
                ],
                "busqueda": request.GET.get("busqueda", ""),
                "permisos": {
                    "editar": user.has_perm("VAT.change_institucioncontacto"),
                    "eliminar": user.has_perm("VAT.delete_institucioncontacto"),
                },
                "urls": {
                    "list": reverse(_LISTA),
                    "create": reverse("vat_institucion_contacto_create"),
                },
            }

        return self.lista(extra)


class ContactoDetailWebView(VatNativeReadView):
    """``GET .../institucion/contactos/<pk>/``: ``contacto_detail.html``."""

    native_class = InstitucionContactoDetailView
    codigos = ["VAT.view_institucioncontacto"]

    def get(self, request, pk):
        vista, _context = self.detalle(pk)
        c = vista.object
        return Response(
            {
                "id": c.pk,
                "title": f"{c.centro} - {c.get_tipo_display()}",
                "centro": c.centro.nombre,
                "centro_id": c.centro.id,
                "tipo": c.get_tipo_display(),
                "valor": c.valor,
                "es_principal": bool(c.es_principal),
                "vigencia_hasta": texto(_VIGENCIA, v=c.vigencia_hasta),
                "observaciones": c.observaciones or "",
                "creado": texto(_FECHA_HORA, v=c.fecha_creacion),
                "modificado": texto(_FECHA_HORA, v=c.fecha_modificacion),
                "urls": {
                    "list": reverse(_LISTA),
                    "update": reverse("vat_institucion_contacto_update", args=[c.pk]),
                    "delete": reverse("vat_institucion_contacto_delete", args=[c.pk]),
                },
                "messages": mensajes_pendientes(
                    request._request  # pylint: disable=protected-access
                ),
            }
        )


class ContactoCreateWebView(VatFormWebView):
    """``GET|POST .../institucion/contactos/nuevo/`` (``?centro=<id>`` locks the centro)."""

    native_class = InstitucionContactoCreateView
    codigos = ["VAT.add_institucioncontacto"]
    crear = True
    lista_name = _LISTA

    def extra(self, vista, form):
        return {"fields": campos_con_bloqueo(form)}


class ContactoUpdateWebView(ContactoCreateWebView):
    """``GET|POST .../institucion/contactos/<pk>/editar/``."""

    native_class = InstitucionContactoUpdateView
    codigos = ["VAT.change_institucioncontacto"]
    crear = False


class ContactoDeleteWebView(VatBajaWebView):
    """``GET|POST .../institucion/contactos/<pk>/eliminar/``."""

    native_class = InstitucionContactoDeleteView
    codigos = ["VAT.delete_institucioncontacto"]

    def resumen(self, objeto):
        return {
            "valor": objeto.valor,
            "tipo": objeto.get_tipo_display(),
            "centro": objeto.centro.nombre,
            "urls": {
                "detail": reverse("vat_institucion_contacto_detail", args=[objeto.pk])
            },
        }
