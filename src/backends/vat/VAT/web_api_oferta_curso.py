"""Web API (G1 v1) de la lista y el detalle de ofertas institucionales y del detalle de curso de VAT (V05.01, U6).

``/api/web/vat/ofertas-institucionales/`` y ``.../<pk>/`` corren ``OfertaInstitucionalListView`` y
``OfertaInstitucionalDetailView``; ``/api/web/vat/cursos-detalle/<pk>/`` corre ``CursoDetailView``. Cada respuesta proyecta
el contexto de la vista nativa con el texto que imprime su plantilla (``d/m/Y``, coma decimal, ``default``) y trae
``messages``. Acceso: ``VAT.view_ofertainstitucional`` y ``VAT.view_curso``, la regla de cada ruta nativa. El alcance es el
queryset nativo (fuera de él, 404).
"""

from django.urls import reverse
from rest_framework.response import Response

from VAT.views.curso import CursoDetailView
from VAT.views.oferta_institucional import (
    OfertaInstitucionalDetailView,
    OfertaInstitucionalListView,
)
from VAT.web_api_common import VatNativeReadView, mensajes_pendientes, texto

_PLAN = "{{ o.plan_curricular }}"
_FECHA_HORA = "{{ v|date:'d/m/Y H:i' }}"


class OfertaInstitucionalListWebView(VatNativeReadView):
    """``GET .../ofertas-institucionales/``: ``oferta_list.html`` con su queryset y su filtro nativos."""

    native_class = OfertaInstitucionalListView
    codigos = ["VAT.view_ofertainstitucional"]

    def get(self, request):
        user = request.user

        def extra(context, _request):
            return {
                "results": [
                    {
                        "id": o.pk,
                        "centro": o.centro.nombre,
                        "plan": texto(_PLAN, o=o),
                        "ciclo": texto("{{ o.ciclo_lectivo }}", o=o),
                        "estado": o.estado,
                        "estado_label": o.get_estado_display(),
                        "usa_voucher": bool(o.usa_voucher),
                        "detail_url": reverse(
                            "vat_oferta_institucional_detail", args=[o.pk]
                        ),
                        "update_url": reverse(
                            "vat_oferta_institucional_update", args=[o.pk]
                        ),
                        "delete_url": reverse(
                            "vat_oferta_institucional_delete", args=[o.pk]
                        ),
                    }
                    for o in context["ofertas"]
                ],
                "busqueda": request.GET.get("busqueda", ""),
                "permisos": {
                    "editar": user.has_perm("VAT.change_ofertainstitucional"),
                    "eliminar": user.has_perm("VAT.delete_ofertainstitucional"),
                },
                "urls": {
                    "list": reverse("vat_oferta_institucional_list"),
                    "create": reverse("vat_oferta_institucional_create"),
                },
            }

        return self.lista(extra)


class OfertaInstitucionalDetailWebView(VatNativeReadView):
    """``GET .../ofertas-institucionales/<pk>/``: ``oferta_detail.html``."""

    native_class = OfertaInstitucionalDetailView
    codigos = ["VAT.view_ofertainstitucional"]

    def get(self, request, pk):
        vista, _context = self.detalle(pk)
        o = vista.object
        django_request = request._request  # pylint: disable=protected-access
        return Response(
            {
                "id": o.pk,
                "titulo": texto("{{ o }}", o=o),
                "centro": o.centro.nombre,
                "plan": texto(_PLAN, o=o),
                "programa": texto("{{ o.programa }}", o=o),
                "ciclo": texto("{{ o.ciclo_lectivo }}", o=o),
                "estado_label": o.get_estado_display(),
                "nombre_local": texto("{{ o.nombre_local|default:'—' }}", o=o),
                "costo": texto("{% if o.costo %}${{ o.costo }}{% endif %}", o=o),
                "usa_voucher": bool(o.usa_voucher),
                "fecha_publicacion": texto(
                    "{{ o.fecha_publicacion|date:'d/m/Y'|default:'—' }}", o=o
                ),
                "observaciones": o.observaciones or "",
                "fecha_creacion": texto(_FECHA_HORA, v=o.fecha_creacion),
                "fecha_modificacion": texto(_FECHA_HORA, v=o.fecha_modificacion),
                "urls": {
                    "list": reverse("vat_oferta_institucional_list"),
                    "update": reverse("vat_oferta_institucional_update", args=[o.pk]),
                    "delete": reverse("vat_oferta_institucional_delete", args=[o.pk]),
                },
                "messages": mensajes_pendientes(django_request),
            }
        )


class CursoDetailWebView(VatNativeReadView):
    """``GET .../cursos-detalle/<pk>/``: ``curso_detail.html`` en modo solo lectura."""

    native_class = CursoDetailView
    codigos = ["VAT.view_curso"]

    def get(self, request, pk):
        vista, context = self.detalle(pk)
        c = vista.object
        django_request = request._request  # pylint: disable=protected-access
        return Response(
            {
                "id": c.pk,
                "nombre": c.nombre,
                "centro": c.centro.nombre,
                "plan_titulo": texto(
                    "{{ c.plan_estudio|default:'Sin plan curricular' }}", c=c
                ),
                "plan": texto("{{ c.plan_estudio|default:'-' }}", c=c),
                "estado": c.estado,
                "estado_label": c.get_estado_display(),
                "tipo": texto("{{ c.tipo|join:', '|default:'-' }}", c=c),
                "prioritario": texto("{{ c.prioritario|yesno:'Sí,No' }}", c=c),
                "inscripcion_libre": texto(
                    "{{ c.inscripcion_libre|yesno:'Sí,No' }}", c=c
                ),
                "observaciones": texto("{{ c.observaciones|default:'-' }}", c=c),
                "usa_voucher": texto("{{ c.usa_voucher|yesno:'Sí,No' }}", c=c),
                "costo_creditos": texto("{{ c.costo_creditos }}", c=c),
                "vouchers": [p.nombre for p in c.voucher_parametrias.all()],
                "comisiones_count": context["comisiones_count"],
                "puede_editar": bool(context["puede_editar_curso"]),
                "urls": {"update": reverse("vat_curso_update", args=[c.pk])},
                "messages": mensajes_pendientes(django_request),
            }
        )
