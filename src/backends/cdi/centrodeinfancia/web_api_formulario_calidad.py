"""Session transport for the native CDI Formulario de Calidad views."""

from django.http import JsonResponse
from django.template.defaultfilters import date
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.formats import localize
from django.utils.timezone import template_localtime
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie

from centrodeinfancia.formulario_calidad_schema import CARTEL_INICIAL
from centrodeinfancia.views_formulario_calidad import (
    FormularioCalidadCargarView,
    FormularioCalidadDetailView,
    FormularioCalidadListView,
)
from centrodeinfancia.web_api import pending_messages
from centrodeinfancia.web_api_observaciones import (
    PERMISO_VER,
    _ObservacionTransportMixin,
)


def _centro(centro):
    return {
        "id": centro.pk,
        "nombre": centro.nombre,
        "url": reverse("centrodeinfancia_detalle", args=[centro.pk]),
    }


def _fecha(value):
    return date(template_localtime(value), "d/m/Y H:i")


def _autor(user):
    return (user.get_full_name() or user.username) if user else "-"


class CalidadHistorialWebView(_ObservacionTransportMixin, FormularioCalidadListView):
    """Use the native authorization, ordering and page validation."""

    permission_code = PERMISO_VER
    http_method_names = ["get", "head"]

    def render_to_response(self, context, **response_kwargs):
        centro = context["centro"]
        page = context["page_obj"]
        borrador = context["borrador"]
        return JsonResponse(
            {
                "centro": _centro(centro),
                "cargar_url": (
                    reverse("centrodeinfancia_calidad_cargar", args=[centro.pk])
                    if context["puede_editar"]
                    else None
                ),
                "borrador_modificado": (
                    _fecha(borrador.modificado) if borrador else None
                ),
                "rows": [
                    {
                        "id": formulario.pk,
                        "fecha_envio": _fecha(formulario.fecha_envio),
                        "enviado_por": _autor(formulario.enviado_por),
                        "url": reverse(
                            "centrodeinfancia_calidad_detalle",
                            args=[centro.pk, formulario.pk],
                        ),
                    }
                    for formulario in context["formularios"]
                ],
                "page": {
                    "number": page.number,
                    "previous": (
                        page.previous_page_number() if page.has_previous() else None
                    ),
                    "next": page.next_page_number() if page.has_next() else None,
                },
                "messages": pending_messages(self.request),
            }
        )


class CalidadDetalleWebView(_ObservacionTransportMixin, FormularioCalidadDetailView):
    """Only a submitted form within the scoped centre is visible."""

    permission_code = PERMISO_VER
    http_method_names = ["get", "head"]

    def render_to_response(self, context, **response_kwargs):
        centro = context["centro"]
        formulario = context["formulario"]
        return JsonResponse(
            {
                "centro": _centro(centro),
                "id": formulario.pk,
                "historial_url": reverse(
                    "centrodeinfancia_calidad_listado", args=[centro.pk]
                ),
                "fecha_envio": _fecha(formulario.fecha_envio),
                "enviado_por": _autor(formulario.enviado_por),
                "jurisdiccion": str(formulario.jurisdiccion or "-"),
                "departamento": str(formulario.departamento or "-"),
                "secciones": [
                    {
                        "id": bloque["seccion"].id,
                        "titulo": bloque["seccion"].titulo,
                        "respuestas": [
                            {
                                "numero": item["pregunta"].numero,
                                "texto": item["pregunta"].texto,
                                "subtitulo": item["pregunta"].subtitulo,
                                "valor": (
                                    str(localize(item["valor"]))
                                    if item["valor"] is not None
                                    else None
                                ),
                                "filas": [
                                    {
                                        "etiqueta": fila["etiqueta"],
                                        "valor": str(localize(fila["valor"])),
                                    }
                                    for fila in item["filas"]
                                ],
                                "especificar": item.get("especificar"),
                            }
                            for item in bloque["items"]
                        ],
                    }
                    for bloque in context["detalle"]
                ],
                "messages": pending_messages(self.request),
            }
        )


def _campo(campo, opciones=()):
    valor = campo.value()
    return {
        "nombre": campo.html_name,
        "valor": (
            valor
            if isinstance(valor, bool)
            else str(valor) if valor is not None else ""
        ),
        "opciones": [[str(value), label] for value, label in opciones],
    }


def _pregunta(item):
    pregunta = item["pregunta"]
    condicion = pregunta.visible_si
    especificar = pregunta.especificar
    filas = item["filas"] or [{"etiqueta": "", "campo": item["campo"]}]
    return {
        "numero": pregunta.numero,
        "texto": pregunta.texto,
        "subtitulo": pregunta.subtitulo,
        "nota": pregunta.nota,
        "tipo": pregunta.tipo,
        "error": item["error"],
        "control": (
            {
                "nombre": condicion.campo,
                "valores": [str(value) for value in condicion.valores],
                "negar": condicion.negar,
            }
            if condicion
            else None
        ),
        "filas": [
            {
                "etiqueta": fila["etiqueta"],
                "campo": _campo(fila["campo"], pregunta.choices),
            }
            for fila in filas
        ],
        "especificar": (
            {
                "etiqueta": especificar.etiqueta,
                "control": pregunta.campo_control_especificar,
                "valor": str(especificar.cuando),
                "campo": _campo(item["especificar"]),
            }
            if especificar
            else None
        ),
    }


@method_decorator(ensure_csrf_cookie, name="dispatch")
@method_decorator(csrf_protect, name="dispatch")
class CalidadCargarWebView(_ObservacionTransportMixin, FormularioCalidadCargarView):
    """Project the native form, including incomplete-send errors and draft."""

    permission_code = PERMISO_VER

    def render_form(self, form, errores=None):
        centro = self.get_centro()
        return JsonResponse(
            {
                "centro": _centro(centro),
                "codigo": centro.codigo_cdi or "Sin código",
                "cartel": CARTEL_INICIAL,
                "es_borrador_existente": bool(form.instance.pk),
                "errores": errores or {},
                "secciones": [
                    {
                        "id": bloque["seccion"].id,
                        "titulo": bloque["seccion"].titulo,
                        "preguntas": [_pregunta(item) for item in bloque["preguntas"]],
                    }
                    for bloque in form.secciones(errores)
                ],
                "messages": pending_messages(self.request),
            },
            status=400 if self.request.method == "POST" else 200,
        )
