"""Web API (G1 v1) de los planes curriculares de VAT (V07.01): lista, detalle, alta y edición.

``/api/web/vat/catalogos/planes-curriculares/`` suma ``<pk>/``, ``nuevo/`` y ``<pk>/editar/``: corren las vistas nativas
``PlanVersionCurricular{List,Detail,Create,Update}View`` y proyectan su contexto (filtros combinables, texto de las plantillas),
su formulario y su ``form_valid`` (mensaje y guardado, con el título de referencia). Acceso: ``VAT.view|add|change_planversioncurricular``
y, además, la guarda del ``dispatch`` nativo de cada vista (rol SSE o provincial; el alta y la edición exigen SSE o provincial con el
permiso), que corre antes de cualquier dato. El alcance es el queryset nativo (fuera de él, 404). El POST responde
``{"ok": true, "redirect": <url>}`` o, con el formulario inválido, 400 con los campos y sus errores. La baja sigue nativa.
"""

from django.http import HttpResponse
from django.urls import reverse
from rest_framework.response import Response

from VAT.views.catalogo import (
    PlanVersionCurricularCreateView,
    PlanVersionCurricularDetailView,
    PlanVersionCurricularListView,
    PlanVersionCurricularUpdateView,
)
from VAT.web_api_common import VatNativeReadView, mensajes_pendientes, texto
from VAT.web_api_vat_centro_formulario import _campo
from VAT.web_api_vat_centros_base import VatFormWebView

_DEFAULT_RAYA = "{{ v|default:'—' }}"
_DEFAULT_GUION = "{{ v|default:'-' }}"
_LISTA = "vat_planversioncurricular_list"


def _con_guarda(native_class):
    """The native view with its ``dispatch`` intact (the role guard) and without running its ``get``/``post``."""

    class _Guarda(native_class):
        def get(self, request, *args, **kwargs):
            return HttpResponse()

        post = get

    return _Guarda


class _ConGuardaNativa:  # pylint: disable=too-few-public-methods,no-member
    """Mixin: the native ``dispatch`` (403 for a role it rejects) runs before the view's own work."""

    def native(self, **kwargs):  # pylint: disable=missing-function-docstring,no-member
        django_request = self.request._request  # pylint: disable=protected-access
        guarda = _con_guarda(self.native_class)()
        guarda.setup(django_request, **kwargs)
        guarda.dispatch(django_request, **kwargs)
        return super().native(**kwargs)  # pylint: disable=no-member


class PlanListWebView(_ConGuardaNativa, VatNativeReadView):
    """``GET .../catalogos/planes-curriculares/``: ``planversioncurricular_list.html`` (filtros combinables)."""

    native_class = PlanVersionCurricularListView
    codigos = ["VAT.view_planversioncurricular"]

    def get(self, request):
        user = request.user

        def extra(context, _request):
            return {
                "results": [
                    {
                        "id": plan.pk,
                        "sector": plan.sector.nombre,
                        "subsector": texto(
                            "{{ v|default:'—' }}",
                            v=plan.subsector.nombre if plan.subsector else None,
                        ),
                        "nombre": plan.nombre,
                        "modalidad": plan.modalidad_cursada.nombre,
                        "horas": texto(_DEFAULT_RAYA, v=plan.horas_reloj),
                        "activo": bool(plan.activo),
                        "detail_url": reverse(
                            "vat_planversioncurricular_detail", args=[plan.pk]
                        ),
                        "update_url": reverse(
                            "vat_planversioncurricular_update", args=[plan.pk]
                        ),
                        "delete_url": reverse(
                            "vat_planversioncurricular_delete", args=[plan.pk]
                        ),
                    }
                    for plan in context["planes"]
                ],
                "permisos": {
                    "editar": user.has_perm("VAT.change_planversioncurricular"),
                    "eliminar": user.has_perm("VAT.delete_planversioncurricular"),
                },
                "urls": {
                    "list": reverse(_LISTA),
                    "create": reverse("vat_planversioncurricular_create"),
                },
                "filters_config": context["filters_config"],
                "favorites": {
                    "section": "",
                    "url": reverse("filtros_favoritos"),
                    "detail_url_template": reverse(
                        "detalle_filtro_favorito", kwargs={"pk": 0}
                    ),
                },
            }

        return self.lista(extra)


class PlanDetailWebView(_ConGuardaNativa, VatNativeReadView):
    """``GET .../catalogos/planes-curriculares/<pk>/``: ``planversioncurricular_detail.html``."""

    native_class = PlanVersionCurricularDetailView
    codigos = ["VAT.view_planversioncurricular"]

    def get(self, request, pk):
        vista, context = self.detalle(pk)
        plan = vista.object
        user = request.user
        django_request = request._request  # pylint: disable=protected-access
        return Response(
            {
                "id": plan.pk,
                "titulo": texto("{{ v }}", v=plan),
                "nombre": texto(_DEFAULT_GUION, v=plan.nombre),
                "sector": plan.sector.nombre,
                "subsector": texto(
                    _DEFAULT_GUION, v=plan.subsector.nombre if plan.subsector else None
                ),
                "modalidad": plan.modalidad_cursada.nombre,
                "activo": bool(plan.activo),
                "normativa": texto(_DEFAULT_GUION, v=context["normativa_texto"]),
                "normativa_tipo": texto(_DEFAULT_GUION, v=context["normativa_tipo"]),
                "normativa_numero": texto(
                    _DEFAULT_GUION, v=context["normativa_numero"]
                ),
                "normativa_anio": texto(_DEFAULT_GUION, v=context["normativa_anio"]),
                "horas_reloj": texto(_DEFAULT_GUION, v=plan.horas_reloj),
                "nivel_requerido": texto(_DEFAULT_GUION, v=plan.nivel_requerido),
                "nivel_certifica": texto(_DEFAULT_GUION, v=plan.nivel_certifica),
                "permisos": {
                    "editar": user.has_perm("VAT.change_planversioncurricular"),
                    "eliminar": user.has_perm("VAT.delete_planversioncurricular"),
                },
                "urls": {
                    "list": reverse(_LISTA),
                    "update": reverse(
                        "vat_planversioncurricular_update", args=[plan.pk]
                    ),
                    "delete": reverse(
                        "vat_planversioncurricular_delete", args=[plan.pk]
                    ),
                },
                "messages": mensajes_pendientes(django_request),
            }
        )


class PlanCreateWebView(_ConGuardaNativa, VatFormWebView):
    """``GET|POST .../catalogos/planes-curriculares/nuevo/``: ``planversioncurricular_form.html``."""

    native_class = PlanVersionCurricularCreateView
    codigos = ["VAT.add_planversioncurricular"]
    crear = True
    lista_name = _LISTA

    def extra(self, vista, form):
        context = vista.get_context_data(form=form)
        return {
            "fields": [_campo(form[nombre]) for nombre in form.fields],
            "normativa_actual": str(form.normativa_texto_actual or ""),
            "page": {
                clave: str(context[clave]) for clave in ("page_title", "submit_text")
            },
            "urls": {
                "list": reverse(self.lista_name),
                "cancel": str(context["cancel_url"]),
            },
            "messages": mensajes_pendientes(
                self.request._request  # pylint: disable=protected-access
            ),
        }


class PlanUpdateWebView(PlanCreateWebView):
    """``GET|POST .../catalogos/planes-curriculares/<pk>/editar/``."""

    native_class = PlanVersionCurricularUpdateView
    codigos = ["VAT.change_planversioncurricular"]
    crear = False
