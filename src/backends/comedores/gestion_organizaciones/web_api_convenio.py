"""Web API (G1 v1) of the project convenio (O01).

``GET/POST .../organizaciones/proyectos/<proyecto_id>/convenio/`` runs the
native ``ConvenioProyectoView`` itself (active project lookup, the
"sin línea" guard, ``ConvenioProyectoForm`` validation, ``form.save()``, the
success and sum-mismatch messages). Access is today's:
``organizaciones.view_organizacion`` on the route, no object scope (see
``docs/registro/decisiones/2026-11-10-2785-brechas-acceso-conservadas.md``).
Decimals travel as text. The legajo "Datos de Convenio" summary
(``legajo/convenios.html``) is delivered as a section (``web_api_secciones``).
"""

from django.template.defaultfilters import date as formato_fecha
from django.urls import reverse
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from core.web_gate import WebGatePermission
from gestion_organizaciones.services.programas import resumen_convenio
from gestion_organizaciones.templatetags.organizaciones_tags import monto
from gestion_organizaciones.views import ConvenioProyectoView
from gestion_organizaciones.web_api import _pending_messages
from gestion_organizaciones.web_api_abm import OrganizacionAbmAccess, _campo
from gestion_organizaciones.web_api_secciones import seccion

SIN_INFORMACION = "Sin información"
COMPONENTES = (
    ("componente_alimentario", "Componente alimentario"),
    ("componente_gastos_generales", "Componente gastos generales"),
    ("componente_siph", "Componente SIPH"),
    ("componente_gasto_bancario", "Componente gasto bancario"),
)


def _resumen(resumen):
    """``resumen_convenio`` formatted by the ``monto`` filter of the legajo."""
    if resumen is None:
        return None
    return {
        "suma": str(monto(resumen["suma"])),
        "total": str(monto(resumen["total"])),
        "diferencia": str(monto(resumen["diferencia"])),
        "coincide": resumen["coincide"],
    }


def _campo_convenio(bound):
    campo = _campo(bound)
    # The native amounts are drawn by hand with this extra widget attribute.
    inputmode = bound.field.widget.attrs.get("inputmode")
    if inputmode:
        campo["attrs"]["inputmode"] = str(inputmode)
    return campo


def _formulario(form):
    return {
        "fields": [_campo_convenio(form[nombre]) for nombre in form.fields],
        "components": [campo.name for campo in form.componentes()],
        "non_field_errors": [str(e) for e in form.non_field_errors()],
    }


def _texto(valor):
    return str(valor) if valor else SIN_INFORMACION


@seccion("organizaciones/partials/legajo/convenios.html")
def seccion_convenios(contexto):
    """``legajo/convenios.html``: per project of the line, its convenio and sums."""
    filas = []
    for fila in contexto.get("convenios") or []:
        convenio = fila["convenio"]
        filas.append(
            {
                "project": {
                    "id": fila["proyecto"].pk,
                    "code": fila["proyecto"].codigo,
                },
                "convenio": convenio
                and {
                    "number": convenio.numero,
                    "date": formato_fecha(convenio.fecha, "d/m/Y"),
                    "months": convenio.meses,
                    "total": str(monto(convenio.monto_total)),
                    "components": [
                        {
                            "label": etiqueta,
                            "amount": str(monto(getattr(convenio, nombre))),
                        }
                        for nombre, etiqueta in COMPONENTES
                    ],
                    "imprevistos": str(monto(convenio.imprevistos) or "-"),
                },
                "summary": _resumen(fila["resumen"]),
                "url": reverse(
                    "organizacion_proyecto_convenio", args=[fila["proyecto"].pk]
                ),
            }
        )
    return {
        "kind": "convenios",
        "program": contexto["programa"].nombre,
        "color": contexto.get("color") or "",
        "is_tradicional": bool(contexto.get("es_linea_tradicional")),
        "can_manage": bool(contexto.get("puede_gestionar_organizaciones")),
        "rows": filas,
    }


class ConvenioWebView(APIView):
    """``GET/POST .../proyectos/<proyecto_id>/convenio/``: ``ConvenioProyectoView``."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, OrganizacionAbmAccess]
    renderer_classes = [JSONRenderer]
    http_method_names = ["get", "head", "post"]

    @staticmethod
    def _vista(request, proyecto_id):
        """The native view, or the 409 answer of its "sin línea" guard."""
        django_request = request._request  # pylint: disable=protected-access
        vista = ConvenioProyectoView()
        vista.setup(django_request, proyecto_id=proyecto_id)
        vista.get_proyecto()  # inactive or unknown: 404
        sin_linea = vista._sin_linea()  # pylint: disable=protected-access
        if sin_linea is None:
            return vista, None
        mensajes = _pending_messages(django_request)
        return vista, Response(
            {
                "error": mensajes[-1]["message"] if mensajes else "",
                "redirect": sin_linea.url,
                "messages": mensajes,
            },
            status=status.HTTP_409_CONFLICT,
        )

    @staticmethod
    def _datos(vista, form, convenio):
        proyecto = vista.get_proyecto()
        organizacion = proyecto.organizacion
        linea = proyecto.linea.programa
        return {
            "project": {"id": proyecto.pk, "code": proyecto.codigo},
            "organization": {
                "id": organizacion.pk,
                "name": organizacion.nombre,
                "cuit": _texto(organizacion.cuit),
                "region": _texto(organizacion.region_abordaje),
                "subzone": _texto(organizacion.subzona_abordaje),
            },
            "line": str(linea),
            "is_tradicional": form.permite_imprevistos,
            "exists": convenio is not None,
            "form": _formulario(form),
            "summary": _resumen(resumen_convenio(convenio)) if convenio else None,
            "urls": {
                "cancel": reverse("organizacion_detalle", args=[organizacion.pk])
                + f"?programa={linea.pk}"
            },
        }

    def get(self, request, proyecto_id):
        vista, rechazo = self._vista(request, proyecto_id)
        if rechazo is not None:
            return rechazo
        vista.object = vista.get_object()
        contexto = vista.get_context_data()
        return Response(
            {
                **self._datos(vista, contexto["form"], vista.object),
                "messages": _pending_messages(
                    request._request  # pylint: disable=protected-access
                ),
            }
        )

    def post(self, request, proyecto_id):
        django_request = request._request  # pylint: disable=protected-access
        vista, rechazo = self._vista(request, proyecto_id)
        if rechazo is not None:
            return rechazo
        respuesta = vista.post(django_request)
        if respuesta.status_code in (301, 302):
            return Response(
                {
                    "redirect": respuesta.url,
                    "messages": _pending_messages(django_request),
                }
            )
        form = respuesta.context_data["form"]
        return Response(
            {
                "errors": {
                    nombre: [str(e) for e in errores]
                    for nombre, errores in form.errors.items()
                    if nombre != "__all__"
                },
                **self._datos(vista, form, vista.object),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
