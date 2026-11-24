"""Web API (G1 v1) de la lista de comisiones de oferta de VAT (V04.01, U4).

``/api/web/vat/comisiones-lista/`` corre ``ComisionListView`` (``comision_list.html``) y proyecta su contexto: el queryset
con su alcance y sus filtros nativos (``busqueda``, ``q``, ``estado``, ``oferta_id``), la paginación y el texto que imprime
la plantilla (``d/m/Y``, ``default``). Acceso: ``VAT.view_comision``, la regla de la ruta nativa. El prefijo no es
``comisiones/`` porque ese recurso es del front INET.
"""

from django.urls import reverse

from VAT.views.oferta_institucional import ComisionListView
from VAT.web_api_common import VatNativeReadView, texto

_FECHA = "{{ v|date:'d/m/Y'|default:'—' }}"


class ComisionListWebView(VatNativeReadView):
    """``GET .../comisiones-lista/``: ``comision_list.html``."""

    native_class = ComisionListView
    codigos = ["VAT.view_comision"]

    def get(self, request):
        user = request.user

        def extra(context, _request):
            return {
                "results": [
                    {
                        "id": c.pk,
                        "codigo": c.codigo_comision,
                        "nombre": c.nombre or "",
                        "oferta": texto("{{ v }}", v=c.oferta),
                        "fecha_inicio": texto(_FECHA, v=c.fecha_inicio),
                        "fecha_fin": texto(_FECHA, v=c.fecha_fin),
                        "cupo": texto("{{ v }}", v=c.cupo),
                        "estado": c.estado,
                        "estado_label": c.get_estado_display(),
                        "detail_url": reverse("vat_comision_detail", args=[c.pk]),
                        "update_url": reverse("vat_comision_update", args=[c.pk]),
                        "delete_url": reverse("vat_comision_delete", args=[c.pk]),
                    }
                    for c in context["comisiones"]
                ],
                "busqueda": request.GET.get("busqueda", ""),
                "permisos": {
                    "editar": user.has_perm("VAT.change_comision"),
                    "eliminar": user.has_perm("VAT.delete_comision"),
                },
                "urls": {
                    "list": reverse("vat_comision_list"),
                    "create": reverse("vat_comision_create"),
                },
            }

        return self.lista(extra)
