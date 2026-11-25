"""Web API (G1 v1) of the CDF centre list, detail and users panel for React.

``/api/web/cdf/`` is published by the cdf backend (``url_prefixes`` in
``src/backends/config/backends.json``). In a split deploy the core checks the
session and the web prerequisites and signs each request; the runtime only
serves requests its ``WebGateMiddleware`` verified. In the monolith
``WebGatePermission`` evaluates the same policy locally. After that the native
URL guard applies unchanged: ``centrodefamilia.view_centro`` through the same
predicate as ``permissions_any_required`` (superuser bypass included).

Each endpoint runs the native view itself (``CentroListView`` /
``CentroDetailView``: scope, search, filters, NoCount pagination, the detail
object rule and its metrics), so it cannot drift from the HTML page; this
module only projects that context to JSON (contract #2805). The users panel
(CR1) is a separate private projection with its own predicate. Read-only:
GET/HEAD only.
"""

from urllib.parse import quote

from django.contrib import messages
from django.http import Http404
from django.template.defaultfilters import date as date_filter
from django.urls import reverse
from django.utils import formats, timezone
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import BasePermission
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from centrodefamilia.access import puede_ver_usuarios_cdf
from centrodefamilia.models import AccesoCDF
from centrodefamilia.views.centro import CentroDetailView, CentroListView
from core.decorators import _has_any_permissions
from core.pagination import build_no_count_page_range
from core.templatetags.custom_filters import google_maps_query
from core.web_gate import WebGatePermission

VIEW_CENTRO = ["centrodefamilia.view_centro"]
PAGE_SIZE = 10
MAPS_URL = "https://maps.google.com/maps?q="
MESSAGE_LEVELS = {
    messages.DEBUG: "info",
    messages.INFO: "info",
    messages.SUCCESS: "success",
    messages.WARNING: "warning",
    messages.ERROR: "error",
}


class ViewCentro(BasePermission):
    """Same rule as the native ``permissions_any_required(["...view_centro"])``."""

    def has_permission(self, request, view):
        return _has_any_permissions(request.user, VIEW_CENTRO)


class CdfWebView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, ViewCentro]
    renderer_classes = [JSONRenderer]
    http_method_names = ["get", "head"]


def pending_messages(request):
    """Consume queued Django messages exactly as the native page would."""
    django_request = request._request  # pylint: disable=protected-access
    return [
        {"message": str(item), "level": MESSAGE_LEVELS.get(item.level, "info")}
        for item in messages.get_messages(django_request)
    ]


def native_view(view_class, request, **kwargs):
    view = view_class()
    view.setup(request._request, **kwargs)  # pylint: disable=protected-access
    return view


def rendered(value):
    """``{{ value }}`` of a template: local time, localized, then text."""
    return str(formats.localize(timezone.template_localtime(value)))


def text_or_none(value):
    return None if value in (None, "") else str(value)


def _fecha(value):
    return date_filter(timezone.localtime(value), "d/m/Y H:i")


# --- List (``centro_list.html``) ---------------------------------------------


def _query_prefix(request):
    """Prefix of every ``components/pagination.html`` link (``page`` appended)."""
    busqueda = request.GET.get("busqueda")
    prefix = f"busqueda={quote(busqueda, safe='/')}&" if busqueda else ""
    return prefix + "".join(
        f"{clave}={quote(valor, safe='/')}&"
        for clave, valor in request.GET.items()
        if clave not in ("page", "busqueda")
    )


def _fila(centro):
    return {
        "id": centro.pk,
        "nombre": centro.nombre,
        "tipo": centro.tipo,
        "tipo_display": str(centro.get_tipo_display()),
        # As ``{{ centro.calle }}`` renders them (``None`` included).
        "calle": rendered(centro.calle),
        "telefono": rendered(centro.telefono),
        "celular": rendered(centro.celular),
        "activo": centro.activo,
        "urls": {
            "detail": reverse("centro_detail", args=[centro.pk]),
            "edit": reverse("centro_update", args=[centro.pk]),
            "delete": reverse("centro_delete", args=[centro.pk]),
        },
    }


class CentroListWebView(CdfWebView):
    """``GET /api/web/cdf/centros/``: the native NoCount list (envelope #2805)."""

    def get(self, request):
        vista = native_view(CentroListView, request)
        vista.object_list = vista.get_queryset()
        context = vista.get_context_data()
        page = context["page_obj"]
        user = request.user
        return Response(
            {
                "count": None,
                "page": page.number,
                "page_size": PAGE_SIZE,
                "pages": None,
                "has_next": page.has_next(),
                "has_previous": page.has_previous(),
                # The native context omits it for an empty page (falsy page_obj).
                "page_range": list(
                    context.get("page_range") or build_no_count_page_range(page)
                ),
                "filters": {
                    "busqueda": request.GET.get("busqueda", ""),
                    "filters": request.GET.get("filters", ""),
                },
                "results": [_fila(centro) for centro in context["centros"]],
                "is_paginated": bool(context["is_paginated"]),
                "query_prefix": _query_prefix(request),
                "filters_config": context["filters_config"],
                "favorites": {
                    "section": context["seccion_filtros_favoritos"],
                    "url": reverse("filtros_favoritos"),
                    "detail_url_template": reverse(
                        "detalle_filtro_favorito", kwargs={"pk": 0}
                    ),
                },
                "can_add": bool(context["can_add"]),
                "can_delete": user.has_perm("centrodefamilia.delete_centro"),
                "urls": {
                    "list": context["filters_action"],
                    "add": context["add_url"],
                    "actividad_create": reverse("actividad_create_sola"),
                    "informecabal": reverse("informecabal_list"),
                },
                "messages": pending_messages(request),
            }
        )


# --- Detail (``centro_detail.html``) -----------------------------------------


def _mapa(centro):
    """The Ubicación iframe source, exactly as the template builds it."""
    query = google_maps_query(centro.latitud, centro.longitud)
    if query:
        return f"{MAPS_URL}{query}&output=embed"
    if (
        centro.calle
        and centro.numero
        and centro.localidad
        and centro.municipio
        and centro.provincia
    ):
        partes = (
            f"{quote(centro.calle, safe='/')}+{centro.numero},"
            f"+{quote(centro.localidad.nombre, safe='/')},"
            f"+{quote(centro.municipio.nombre, safe='/')},"
            f"+{quote(centro.provincia.nombre, safe='/')}"
        )
        return f"{MAPS_URL}{partes}&output=embed"
    return None


def _centro(centro):
    campos = (
        "correo",
        "sitio_web",
        "link_redes",
        "telefono",
        "celular",
        "calle",
        "domicilio_actividad",
        "nombre_referente",
        "apellido_referente",
        "telefono_referente",
        "correo_referente",
    )
    data = {
        "id": centro.pk,
        "nombre": centro.nombre,
        "tipo": centro.tipo,
        "tipo_display": str(centro.get_tipo_display()),
        "activo": centro.activo,
        "codigo": centro.codigo,
        "numero": None if centro.numero is None else rendered(centro.numero),
        "localidad": text_or_none(centro.localidad),
        "provincia": text_or_none(centro.provincia),
        "municipio": text_or_none(centro.municipio),
        "organizacion_asociada": text_or_none(centro.organizacion_asociada),
    }
    data.update({campo: text_or_none(getattr(centro, campo)) for campo in campos})
    return data


def _pagina(page):
    return {
        "number": page.number,
        "pages": page.paginator.num_pages,
        "page_range": list(page.paginator.page_range),
        "previous": page.previous_page_number() if page.has_previous() else None,
        "next": page.next_page_number() if page.has_next() else None,
    }


def _dias(actividad):
    return [str(dia.nombre) for dia in actividad.dias.all()]


def _actividad_curso(actividad):
    return {
        "id": actividad.pk,
        "actividad": actividad.actividad.nombre,
        "categoria": actividad.actividad.categoria.nombre,
        "dias": _dias(actividad),
        "horariosdesde": rendered(actividad.horariosdesde),
        "horarioshasta": rendered(actividad.horarioshasta),
        "estado_display": str(actividad.get_estado_display()),
        "detalle_url": reverse("actividadcentro_detail", kwargs={"pk": actividad.pk}),
    }


def _actividad_otra(actividad):
    return {
        "id": actividad.pk,
        "centro": actividad.centro.nombre,
        "actividad": actividad.actividad.nombre,
        "categoria": actividad.actividad.categoria.nombre,
        "estado_display": str(actividad.get_estado_display()),
        "cantidad_personas": rendered(actividad.cantidad_personas),
        "dias": _dias(actividad),
        "horariosdesde": rendered(actividad.horariosdesde),
        "horarioshasta": rendered(actividad.horarioshasta),
        "precio": rendered(actividad.precio) if actividad.precio else None,
    }


def _usuario(user):
    return user.get_full_name() or user.username


def _cabal(centro, archivos):
    archivos = list(archivos)
    ultimo = archivos[0] if archivos else None
    return {
        "ultimo": (
            {
                "fecha_subida": _fecha(ultimo.fecha_subida),
                "usuario": _usuario(ultimo.usuario),
            }
            if ultimo
            else None
        ),
        "archivos": [
            {
                "id": archivo.pk,
                "nombre_original": archivo.nombre_original,
                "fecha_subida": _fecha(archivo.fecha_subida),
                "url": reverse(
                    "informecabal_archivo_centro_detail", args=[centro.pk, archivo.pk]
                ),
            }
            for archivo in archivos
        ],
    }


def _acciones(centro, context):
    acciones = {
        "editar_url": reverse("centro_update", args=[centro.pk]),
        "agregar_actividad_url": reverse(
            "actividadcentro_create", kwargs={"centro_id": centro.pk}
        ),
        "agregar_adherido_url": None,
        "generar_usuario_url": None,
    }
    if centro.tipo == "faro":
        acciones["agregar_adherido_url"] = (
            f"{reverse('centro_create')}?faro={centro.pk}"
        )
    if context["puede_generar_usuario_cdf"]:
        acciones["generar_usuario_url"] = reverse(
            "cdf_centro_generar_usuario", args=[centro.pk]
        )
    return acciones


def _detail_object(request, pk):
    vista = native_view(CentroDetailView, request, pk=pk)
    try:
        vista.object = vista.get_object()
    except Http404 as exc:
        raise NotFound() from exc
    return vista


class CentroDetailWebView(CdfWebView):
    """``GET /api/web/cdf/centros/<pk>/``: the native detail, credentials apart."""

    def get(self, request, pk):
        vista = _detail_object(request, pk)
        centro = vista.object
        context = vista.get_context_data()
        metricas = context["metricas"]
        curso = request.GET.get("search_actividades_curso", "")
        return Response(
            {
                "centro": _centro(centro),
                "mapa": _mapa(centro),
                "acciones": _acciones(centro, context),
                "metricas": {
                    **{
                        clave: metricas[clave]
                        for clave in (
                            "categorias",
                            "actividades",
                            "inscriptos",
                            "hombres",
                            "mujeres",
                            "mixtas",
                            "interacciones",
                        )
                    },
                    "centros_faro": None,
                    "total_recaudado": (
                        rendered(context["total_recaudado"])
                        if centro.tipo == "adherido"
                        else None
                    ),
                    "asistentes": context["asistentes"],
                },
                "actividades_curso": {
                    **_pagina(context["actividades_curso_paginadas"]),
                    "results": [
                        _actividad_curso(actividad)
                        for actividad in context["actividades_curso_paginadas"]
                    ],
                },
                "actividades_otras": {
                    **_pagina(context["actividades_paginados"]),
                    "results": [
                        _actividad_otra(actividad)
                        for actividad in context["actividades_paginados"]
                    ],
                },
                "search": {
                    "actividades_curso": curso,
                    "actividades": request.GET.get("search_actividades", ""),
                    "todas_activa": "page_act" in request.GET
                    or bool(request.GET.get("search_actividades")),
                },
                # The native pagination links (their parameter loss included).
                "links": {
                    "curso_prefix": (
                        f"?search_actividades_curso={quote(curso, safe='/')}"
                        "&page_actividades_curso="
                    ),
                    "todas_suffix": "&search_actividades="
                    + request.GET.get("search_actividades", ""),
                },
                "cabal": _cabal(centro, context["archivos_cabal_centro"]),
                "adheridos": [],
                "observaciones": [],
                "puede_ver_usuarios": bool(context["puede_ver_usuarios_cdf"]),
                "urls": {"usuarios": reverse("web_cdf_centros_usuarios", args=[pk])},
                "messages": pending_messages(request),
            }
        )


class CentroUsuariosWebView(CdfWebView):
    """``GET /api/web/cdf/centros/<pk>/usuarios/``: the CR1 credentials panel."""

    def get(self, request, pk):
        vista = _detail_object(request, pk)
        centro = vista.object
        user = request.user
        if not puede_ver_usuarios_cdf(user, centro):
            raise PermissionDenied()
        accesos = AccesoCDF.objects.filter(centro=centro)
        if not getattr(user, "is_superuser", False):
            accesos = accesos.filter(user=user, activo=True)
        accesos = accesos.select_related("user", "user__profile").order_by(
            "-activo", "user__username"
        )
        return Response(
            {
                "results": [
                    {
                        "username": acceso.user.username,
                        "nombre_completo": acceso.user.get_full_name() or None,
                        "email": acceso.user.email or None,
                        "activo": acceso.activo,
                        "contrasena_temporal": _temporal(acceso.user),
                    }
                    for acceso in accesos
                ]
            }
        )


def _temporal(user):
    profile = getattr(user, "profile", None)
    return getattr(profile, "temporary_password_plaintext", None) or None
