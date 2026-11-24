"""Web API (G1 v1) of the CDI centre detail / legajo (CDI09.01) for the React page.

``/api/web/cdi/`` is published by this backend. In a split deploy the core
checks the session and the web prerequisites and signs each request; the
runtime only serves what its ``WebGateMiddleware`` verified. In the monolith
``WebGatePermission`` evaluates the same policy locally. After that the native
URL guard applies unchanged: ``centrodeinfancia.view_centrodeinfancia`` through
the same predicate as ``permissions_any_required`` (superuser bypass included).

``GET /api/web/cdi/centros/<pk>/`` runs ``CentroDeInfanciaDetailView`` itself
(the scoped centre, 404 outside the actor's scope, the paginated observation
table, the workers, the recent forms and the centre users), so scope and
numbers cannot drift from the HTML page; this module only projects its context
to JSON. Cell texts use the same template expressions as
``centrodeinfancia_detail.html``. The temporary passwords of the users table
follow the native per-row rule (superuser or own account) and the response is
``private, no-store`` (CDI-CR1): it is never part of a shared context.

The writes of the page stay the native views behind the same G1 gate, URL
permission and CDI-A3 read-only veto: the user status change
(``cambiar_estado_usuario_cdi``) and the worker soft delete
(``TrabajadorCentroInfanciaDeleteView``). A native redirect becomes
``{"ok": true, "redirect": <Location>}``; the flash message stays in the
session for the next GET. The observation modal reuses
``/api/web/cdi/centros/<pk>/observaciones/crear/``.

While ``CDI_INTERVENCIONES_VISIBLE`` is on the interventions card and its modal
are not served here (409); the preview entry then serves the native page.
"""

from urllib.parse import quote

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import Http404, JsonResponse
from django.template import Context, Template
from django.urls import reverse
from django.utils import timezone
from django.utils.text import Truncator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from centrodeinfancia.views import (
    CentroDeInfanciaDetailView,
    TrabajadorCentroInfanciaDeleteView,
)
from centrodeinfancia.views_usuario_cdi import cambiar_estado_usuario_cdi
from centrodeinfancia.web_api import pending_messages
from centrodeinfancia.web_api_centros import PuedeVerCentros
from centrodeinfancia.web_api_observaciones import SIN_PERMISO, _gate, _json
from core.decorators import permissions_any_required
from core.templatetags.custom_filters import google_maps_address, has_perm_code
from core.web_gate import WebGatePermission

PERMISO_VER = "centrodeinfancia.view_centrodeinfancia"
PERMISO_BAJA_TRABAJADOR = "centrodeinfancia.delete_trabajador"
VER_FORMULARIOS = "centrodeinfancia.view_formulariocdi"
AGREGAR_FORMULARIOS = "centrodeinfancia.add_formulariocdi"
CAMBIAR_FORMULARIOS = "centrodeinfancia.change_formulariocdi"
NO_ENCONTRADO = "No encontrado."
NO_DISPONIBLE = "Las intervenciones no están disponibles en esta pantalla."

_PLANTILLAS = {}


def _render(contexto, expresion, vacio="-"):
    """``{{ expresion|default:"-" }}`` as ``centrodeinfancia_detail.html`` shows it."""
    texto = "{{ " + expresion + '|default:"' + vacio + '" }}'
    if texto not in _PLANTILLAS:
        _PLANTILLAS[texto] = Template(texto)
    return _PLANTILLAS[texto].render(Context(contexto, autoescape=False))


def _items(contexto, campos):
    return [
        {"icon": icono, "label": etiqueta, "value": _render(contexto, expresion)}
        for icono, etiqueta, expresion in campos
    ]


_GENERAL = (
    ("bi-diagram-3", "Organización", "centro_info_basica.organizacion"),
    ("bi-upc-scan", "CUIT", "centro_info_basica.cuit_organizacion_gestiona"),
    ("bi-bounding-box", "Ámbito", "centro_info_basica.ambito"),
    ("bi-envelope", "Correo electrónico", "centro_info_basica.mail"),
    ("bi-map", "Provincia", "centro.provincia"),
    ("bi-signpost-2", "Departamento", "centro.departamento"),
    ("bi-bar-chart", "Decil de IPI", "centro.departamento.decil_ipi"),
    ("bi-pin-map", "Municipio", "centro.municipio"),
    ("bi-geo-alt", "Localidad", "centro.localidad"),
    ("bi-mailbox", "Código postal", "centro.codigo_postal"),
)
_GENERAL_COLA = (
    ("bi-telephone", "Teléfono", "centro.telefono"),
    ("bi-crosshair", "Latitud", "centro.latitud"),
    ("bi-crosshair2", "Longitud", "centro.longitud"),
)
_REFERENTE_COLA = (
    ("bi-phone", "Teléfono", "centro.telefono_referente"),
    ("bi-envelope", "Correo electrónico", "centro.email_referente"),
)
_FUNCIONAMIENTO = (
    (
        "bi-calendar3",
        "Meses de funcionamiento",
        "centro_funcionamiento.meses_funcionamiento",
    ),
    (
        "bi-calendar-week",
        "Días de funcionamiento",
        "centro_funcionamiento.dias_funcionamiento",
    ),
)
_FUNCIONAMIENTO_COLA = (
    ("bi-collection", "Oferta de servicios", "centro_funcionamiento.oferta_servicios"),
)


def _domicilio(centro):
    if not centro.calle:
        return "-"
    return f"{centro.calle} {centro.numero or ''}".strip()


def _con_otra(principal, otra):
    return f"{principal} ({otra})" if otra else principal


def _mapa(centro):
    consulta = google_maps_address(
        centro.calle,
        centro.numero,
        centro.localidad,
        centro.municipio,
        centro.provincia,
    )
    if centro.calle and centro.municipio and centro.provincia and consulta:
        return f"https://maps.google.com/maps?q={consulta}&output=embed"
    return None


def _usuarios(vista, context):
    if not context["puede_ver_usuarios_cdi"]:
        return None
    request = vista.request
    credenciales = context["puede_ver_credenciales_cdi"]
    administrar = context["puede_administrar_usuarios_cdi"]
    filas = []
    for acceso in context["usuarios_cdi"]:
        usuario = acceso.user
        nombre = _render({"u": usuario}, "u.get_full_name")
        fila = {
            "id": acceso.pk,
            "username": usuario.username,
            "responsable": bool(acceso.es_responsable),
            "nombre": nombre,
            "email": usuario.email or "-",
            "estado": acceso.estado,
            "motivo": acceso.motivo_estado or "",
        }
        if credenciales:
            if request.user.is_superuser or acceso.user_id == request.user.id:
                temporal = usuario.profile.temporary_password_plaintext
                fila["password"] = (
                    {"kind": "value", "value": temporal}
                    if temporal
                    else {"kind": "changed", "value": ""}
                )
            else:
                fila["password"] = {"kind": "unavailable", "value": ""}
        if administrar:
            if (
                acceso.es_responsable
                or acceso.user_id == request.user.id
                or acceso.estado == "baja"
            ):
                fila["acciones"] = None
            else:
                fila["acciones"] = {
                    "activo": acceso.estado == "activo",
                    "usuario": usuario.get_full_name() or usuario.username,
                    "url": f"/api/web/cdi/centros/{context['centro'].pk}/usuarios/{acceso.pk}/estado/",
                }
        filas.append(fila)
    return {
        "credenciales": bool(credenciales),
        "administrar": bool(administrar),
        "generar_url": (
            reverse("centrodeinfancia_generar_usuario", args=[context["centro"].pk])
            if context["puede_generar_usuario_cdi"]
            else None
        ),
        "columnas": context["usuarios_cdi_columnas"],
        "filas": filas,
    }


def _trabajadores(context):
    centro = context["centro"]
    editar = bool(context["puede_editar_trabajadores"])
    eliminar = bool(context["puede_eliminar_trabajadores"])
    filas = []
    for trabajador in context["trabajadores"]:
        ctx = {"t": trabajador}
        if trabajador.funcion_cdi:
            funcion = trabajador.get_funcion_cdi_display()
        elif trabajador.funcion_egp:
            funcion = trabajador.get_funcion_egp_display()
        else:
            funcion = "-"
        nombre = f"{trabajador.apellido}, {trabajador.nombre}"
        args = [centro.pk, trabajador.pk]
        filas.append(
            {
                "id": trabajador.pk,
                "nombre": nombre,
                "subcomponente": _render(ctx, "t.get_subcomponente_display"),
                "funcion": funcion,
                "fecha_carga": _render(ctx, "t.fecha_carga"),
                "ver": reverse("centrodeinfancia_trabajador_ver", args=args),
                "editar": (
                    reverse("centrodeinfancia_trabajador_editar", args=args)
                    if editar
                    else None
                ),
                "eliminar": (
                    f"/api/web/cdi/centros/{centro.pk}/trabajadores/{trabajador.pk}/eliminar/"
                    if eliminar
                    else None
                ),
            }
        )
    return {
        "crear_url": (
            reverse("centrodeinfancia_trabajador_crear", args=[centro.pk])
            if editar
            else None
        ),
        "filas": filas,
    }


def _formularios(vista, context):
    user = vista.request.user
    if not (
        context["cdi_formularios_visible"] and has_perm_code(user, VER_FORMULARIOS)
    ):
        return None
    centro = context["centro"]
    filas = []
    for item in context["formularios_recent"]:
        filas.append(
            {
                "id": f"{item['id_codigo_cdi']} / {item['id']}",
                "fecha": _render(item, 'fecha_relevamiento|date:"d/m/Y"'),
                "respondente": _render(item, "nombre_completo_respondente"),
                "actualizado": _render(item, 'updated_at|date:"d/m/Y H:i"', ""),
                "ver": item["detail_url"],
                "editar": (
                    item["edit_url"]
                    if has_perm_code(user, CAMBIAR_FORMULARIOS)
                    else None
                ),
            }
        )
    return {
        "listado_url": reverse("centrodeinfancia_formulario_listado", args=[centro.pk]),
        "crear_url": (
            reverse("centrodeinfancia_formulario_crear", args=[centro.pk])
            if has_perm_code(user, AGREGAR_FORMULARIOS)
            else None
        ),
        "filas": filas,
    }


def _calidad(context):
    if not context["calidad_puede_ver"]:
        return None
    centro = context["centro"]
    borrador = context["calidad_borrador"]
    filas = []
    for formulario in context["calidad_recientes"]:
        ctx = {"f": formulario}
        filas.append(
            {
                "id": str(formulario.pk),
                "fecha": _render(ctx, 'f.fecha_envio|date:"d/m/Y H:i"', ""),
                "enviado_por": _render(
                    ctx, "f.enviado_por.get_full_name|default:f.enviado_por.username"
                ),
                "ver": reverse(
                    "centrodeinfancia_calidad_detalle", args=[centro.pk, formulario.pk]
                ),
            }
        )
    return {
        "listado_url": reverse("centrodeinfancia_calidad_listado", args=[centro.pk]),
        "cargar_url": (
            reverse("centrodeinfancia_calidad_cargar", args=[centro.pk])
            if context["calidad_puede_editar"]
            else None
        ),
        "borrador": bool(borrador),
        "borrador_fecha": (
            _render({"b": borrador}, 'b.modificado|date:"d/m/Y H:i"', "")
            if borrador
            else ""
        ),
        "total": context["calidad_total"],
        "filas": filas,
    }


def _observaciones(vista, context):
    pagina = context["observaciones_page_obj"]
    campo = context["observacion_form"]["observacion"]
    filas = []
    for obs in pagina:
        filas.append(
            {
                "id": obs.pk,
                "fecha": _fecha_observacion(obs),
                "observador": obs.observador or "Sin observador",
                "texto": _truncar(obs.observacion),
                "ver": reverse(
                    "centrodeinfancia_observacion_detalle", kwargs={"pk": obs.pk}
                ),
            }
        )
    otros = "".join(
        f"{clave}={quote(valor, safe='/')}&"
        for clave, valor in vista.request.GET.items()
        if clave not in ("observaciones_page", "busqueda")
    )
    return {
        "filas": filas,
        "paginated": bool(context["observaciones_is_paginated"]),
        "number": pagina.number,
        "previous": pagina.previous_page_number() if pagina.has_previous() else None,
        "next": pagina.next_page_number() if pagina.has_next() else None,
        "range": list(context["observaciones_page_range"]),
        # An empty page is falsy, so the native component omits the total line.
        "count": pagina.paginator.count if filas else None,
        "query_prefix": otros,
        "crear_url": f"/api/web/cdi/centros/{context['centro'].pk}/observaciones/crear/",
        "campo": {
            "label": str(campo.label),
            "rows": int(campo.field.widget.attrs.get("rows", 4)),
            "placeholder": str(campo.field.widget.attrs.get("placeholder", "")),
        },
    }


def _fecha_observacion(obs):
    if not obs.fecha_visita:
        return "-"
    fecha = obs.fecha_visita
    if timezone.is_naive(fecha):
        fecha = timezone.make_aware(fecha)
    return timezone.localtime(fecha).strftime("%d/%m/%Y %H:%M")


def _truncar(texto):
    valor = Truncator(texto or "").chars(80)
    return valor if valor else "-"


class CentroDetalleWebView(APIView):
    """``GET /api/web/cdi/centros/<pk>/``: the native centre detail as JSON."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, PuedeVerCentros]
    renderer_classes = [JSONRenderer]
    http_method_names = ["get", "head"]

    def get(self, request, pk):
        django_request = request._request  # pylint: disable=protected-access
        if settings.CDI_INTERVENCIONES_VISIBLE:
            return Response({"detail": NO_DISPONIBLE}, status=409)
        vista = CentroDeInfanciaDetailView()
        vista.setup(django_request, pk=pk)
        try:
            vista.object = vista.get_object()
            context = vista.get_context_data(object=vista.object)
        except Http404 as exc:
            raise NotFound() from exc
        response = Response(self._payload(vista, context))
        response["Cache-Control"] = "private, no-store"
        response["Vary"] = "Cookie"
        return response

    def _payload(self, vista, context):
        centro = context["centro"]
        user = vista.request.user
        ctx = {
            "centro": centro,
            "centro_info_basica": context["centro_info_basica"],
            "centro_funcionamiento": context["centro_funcionamiento"],
        }
        referente = " ".join(
            parte
            for parte in (centro.nombre_referente, centro.apellido_referente)
            if parte
        )
        funcionamiento = context["centro_funcionamiento"]
        formularios = _formularios(vista, context)
        general = _items(ctx, _GENERAL)
        general.append(
            {"icon": "bi-signpost", "label": "Domicilio", "value": _domicilio(centro)}
        )
        general += _items(ctx, _GENERAL_COLA)
        func = _items(ctx, _FUNCIONAMIENTO)
        func.append(
            {
                "icon": "bi-arrow-left-right",
                "label": "Tipo de jornada",
                "value": _con_otra(
                    funcionamiento["tipo_jornada"], funcionamiento["tipo_jornada_otra"]
                ),
            }
        )
        func.append(
            {
                "icon": "bi-building",
                "label": "Modalidad de gestión",
                "value": _con_otra(
                    funcionamiento["modalidad_gestion"],
                    funcionamiento["modalidad_gestion_otra"],
                ),
            }
        )
        func += _items(ctx, _FUNCIONAMIENTO_COLA)
        return {
            "centro": {
                "id": centro.pk,
                "nombre": centro.nombre,
                "codigo_cdi": centro.codigo_cdi or "",
                "lista_url": reverse("centrodeinfancia"),
            },
            "hero": {
                "nomina": context["nomina_total"],
                "trabajadores": len(context["trabajadores"]),
                "formularios": context["formularios_total"] if formularios else None,
                "anio_inicio": context["centro_info_basica"]["fecha_inicio"],
            },
            "header": {
                "nomina_url": reverse("centrodeinfancia_nomina_ver", args=[centro.pk]),
                "historial_url": (
                    reverse(
                        "audittrail:log_instance",
                        args=["centrodeinfancia", "centrodeinfancia", centro.pk],
                    )
                    if user.has_perm("auditlog.view_logentry")
                    else None
                ),
                "generar_usuario_url": (
                    reverse("centrodeinfancia_generar_usuario", args=[centro.pk])
                    if context["puede_generar_usuario_cdi"]
                    else None
                ),
                "editar_url": reverse("centrodeinfancia_editar", args=[centro.pk]),
                "eliminar_url": reverse("centrodeinfancia_eliminar", args=[centro.pk]),
            },
            "general": general,
            "mapa": _mapa(centro),
            "referente": {
                "nombre": referente or "-",
                "items": _items(ctx, _REFERENTE_COLA),
            },
            "funcionamiento": {
                "items": func,
                "horarios": [
                    {
                        "dia": str(h["dia"]),
                        "apertura": h["apertura"],
                        "cierre": h["cierre"],
                    }
                    for h in funcionamiento["horarios"]
                ],
            },
            "usuarios": _usuarios(vista, context),
            "nomina": {
                "asistencia_url": (
                    reverse("centrodeinfancia_nomina_asistencia", args=[centro.pk])
                    if context["puede_tomar_asistencia_nomina"]
                    else None
                ),
                "ver_url": reverse("centrodeinfancia_nomina_ver", args=[centro.pk]),
                "hombres": context["nomina_hombres"],
                "mujeres": context["nomina_mujeres"],
                "x": context["nomina_x"],
                "menores": context["nomina_menores"],
            },
            "trabajadores": _trabajadores(context),
            "formularios": formularios,
            "calidad": _calidad(context),
            "observaciones": _observaciones(vista, context),
            "messages": pending_messages(vista.request),
        }


def _post_nativo(permiso, nativa):
    """The native write view behind G1, the URL permission and the CDI-A3 veto."""

    @ensure_csrf_cookie
    @csrf_protect
    def vista(request, *args, **kwargs):
        if request.method != "POST":
            respuesta = _json({"detail": "Método no permitido."}, 405)
            respuesta["Allow"] = "POST"
            return respuesta
        bloqueo = _gate(request)
        if bloqueo is not None:
            return bloqueo
        guardada = permissions_any_required([permiso])(
            lambda req: nativa(req, *args, **kwargs)
        )
        try:
            respuesta = guardada(request)
        except PermissionDenied as exc:
            return _json({"detail": str(exc) or SIN_PERMISO}, 403)
        except Http404:
            return _json({"detail": NO_ENCONTRADO}, 404)
        if respuesta.status_code == 302:
            convertida = JsonResponse({"ok": True, "redirect": respuesta["Location"]})
            convertida.cookies = respuesta.cookies
            return _json_privada(convertida)
        return _json_privada(respuesta)

    return vista


def _json_privada(respuesta):
    respuesta["Cache-Control"] = "private, no-store"
    respuesta["Vary"] = "Cookie"
    return respuesta


usuario_estado_web = _post_nativo(PERMISO_VER, cambiar_estado_usuario_cdi)
trabajador_eliminar_web = _post_nativo(
    PERMISO_BAJA_TRABAJADOR, TrabajadorCentroInfanciaDeleteView.as_view()
)
