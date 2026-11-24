"""Canonical React entries registered by the Inspecciones activation switch.

The Actas entries keep the native URLs (``/inspecciones/actas/`` and
``/inspecciones/actas/<numero>/``) and the native views' dispatch: anonymous
users go to the login, users without ``puede_gestionar`` get the native 403
and an invalid page or a missing acta the native 404. Only then the GET
returns the frozen React ``index.html``, which loads its data from
``/api/web/inspecciones/``. Assets stay under the backend's own prefix
(``/inspecciones/react/``), so the core forwards them like any other route.
The import circuit embeds the already authorized native page context, so
the original confirmation POST returns its one-shot result without a new endpoint.
"""

import hashlib
import mimetypes
import re
from pathlib import Path
from types import MappingProxyType

from django.http import HttpResponse
from django.middleware.csrf import get_token
from django.urls import path, reverse
from django.utils.cache import patch_cache_control, patch_vary_headers
from django.utils.decorators import method_decorator
from django.utils.html import json_script
from django.views import View
from django.views.decorators.csrf import ensure_csrf_cookie

from inspecciones.views_actas import ActaDetalleView, ActasView
from inspecciones.views_asignaciones import AsignacionCrearView, AsignacionesView
from inspecciones.views_escuelas import (
    EscuelaCrearView,
    EscuelaEditarView,
    EscuelasView,
)
from inspecciones.views_importacion import (
    IMPORTACIONES,
    ConfirmarView,
    RevisionView,
    SubirArchivoView,
)
from inspecciones.views_tablero import TableroView
from inspecciones.web_api import _layout, _pestanas
from inspecciones.web_api_escuelas import _totales

BUILD_ASSETS = "/v2/sisoc/assets/"
PUBLIC_ASSETS = "/inspecciones/react/assets/"
IMPORTACION_MARKER = re.compile(
    rb'<meta name="sisoc-react-inspecciones-importacion" content="1"\s*/?>'
)
ASSET_SUFFIXES = {".js", ".css", ".woff", ".woff2", ".svg", ".png", ".jpg", ".ico"}


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ActasEntry(ActasView):
    """Native guards and page validation, then the frozen React index."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        # Same Http404 as the native list for a page that does not exist.
        self.paginate_queryset(self.object_list, self.get_paginate_by(self.object_list))
        response = HttpResponse(
            b"" if request.method == "HEAD" else self.index_bytes,
            content_type="text/html; charset=utf-8",
        )
        response["Content-Length"] = str(len(self.index_bytes))
        patch_cache_control(response, private=True, no_store=True)
        patch_vary_headers(response, ("Cookie",))
        return response


def _index_response(request, index_bytes):
    response = HttpResponse(
        b"" if request.method == "HEAD" else index_bytes,
        content_type="text/html; charset=utf-8",
    )
    response["Content-Length"] = str(len(index_bytes))
    patch_cache_control(response, private=True, no_store=True)
    patch_vary_headers(response, ("Cookie",))
    return response


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ActaDetalleEntry(ActaDetalleView):
    """Native guards and the native 404 of a missing acta, then the frozen index."""

    http_method_names = ["get", "head"]
    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.get_acta()
        return _index_response(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class EscuelasEntry(EscuelasView):
    """Native guards and the native 404 of an invalid page, then the frozen index."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        self.paginate_queryset(self.object_list, self.get_paginate_by(self.object_list))
        return _index_response(request, self.index_bytes)


def _escuela_form_entry(vista, request):
    """GET of a school form page: native guards (and the edit 404), then the index."""
    vista.get_form_kwargs()
    return _index_response(request, vista.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class EscuelaNuevaEntry(EscuelaCrearView):
    """``/inspecciones/escuelas/nueva/`` as a page; its POST stays native."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        return _escuela_form_entry(self, request)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class EscuelaEditarEntry(EscuelaEditarView):
    """``/inspecciones/escuelas/<pk>/editar/`` as a page; its POST stays native."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        return _escuela_form_entry(self, request)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class AsignacionesEntry(AsignacionesView):
    """Native guards, then the frozen index (an unknown page is the last page)."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        return _index_response(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class AsignacionNuevaEntry(AsignacionCrearView):
    """``/inspecciones/asignaciones/nueva/`` as a page; its POST stays native."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        return _index_response(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class TableroEntry(TableroView):
    """``/inspecciones/tablero/``: native guards, then the frozen index."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        return _index_response(request, self.index_bytes)


class _ImportacionEntry:
    """Keep native dispatch and forms; change only the successful page renderer."""

    index_bytes = b""

    def render_to_response(self, context, **response_kwargs):
        paso = context.get("paso", 1)
        tipo = context["tipo"]
        urls = {"volver": reverse(self.config["volver"])}
        data = {
            "paso": paso,
            "tipo": tipo,
            "titulo": self.titulo,
            "layout": _layout({**context, "request": self.request}),
            "tabs": _pestanas(),
            "totales": (
                _totales(context["totales_panel"])
                if context["mostrar_totales"]
                else None
            ),
            "urls": urls,
        }
        if paso < 3:
            data["csrf"] = get_token(self.request)
            urls["subir"] = reverse(context["url_subir"])
        if paso == 1:
            data["errores"] = [
                str(error) for error in context["form"]["archivo"].errors
            ]
        else:
            data.update(
                nombre_archivo=context["nombre_archivo"],
                resumen=context["resumen"],
                observaciones=context["observaciones"],
                total_observaciones=context["total_observaciones"],
            )
        if paso == 2:
            for accion in ("confirmar", "cancelar", "observaciones"):
                urls[accion] = reverse(
                    context[f"url_{accion}"], args=[context["token"]]
                )
        snippet = json_script(data, "inspecciones-importacion-data").encode("utf-8")
        index = self.index_bytes.replace(b"</body>", snippet + b"</body>", 1)
        return _index_response(self.request, index)


class ImportacionArchivoEntry(_ImportacionEntry, SubirArchivoView):
    """Native multipart GET/POST, including the bound form after a validation error."""


class ImportacionRevisionEntry(_ImportacionEntry, RevisionView):
    """Only render after the native revision has loaded the owner's private upload."""


class ImportacionResultadoEntry(_ImportacionEntry, ConfirmarView):
    """Only render the result of the original native POST, never a separate GET."""


def _importacion_patterns(index_bytes):
    if not IMPORTACION_MARKER.search(index_bytes) or b"</body>" not in index_bytes:
        return []
    routes = []
    for tipo in IMPORTACIONES:
        base = f"inspecciones/{tipo}/importar/"
        for suffix, view in (
            ("", ImportacionArchivoEntry),
            ("<str:token>/", ImportacionRevisionEntry),
            ("<str:token>/confirmar/", ImportacionResultadoEntry),
        ):
            routes.append(
                path(base + suffix, view.as_view(tipo=tipo, index_bytes=index_bytes))
            )
    return routes


class ReactAssetView(View):
    """Serve only frozen build assets; no request data reaches a static upstream."""

    http_method_names = ["get", "head"]
    assets = None

    def get(self, request, asset_path):
        asset = self.assets.get(asset_path) if self.assets is not None else None
        if request.META.get("QUERY_STRING") or asset is None:
            return HttpResponse(status=404)
        body, content_type, digest = asset
        response = HttpResponse(
            b"" if request.method == "HEAD" else body, content_type=content_type
        )
        response["Content-Length"] = str(len(body))
        response["ETag"] = f'"{digest}"'
        response["Cache-Control"] = "public, max-age=31536000, immutable"
        response["X-Content-Type-Options"] = "nosniff"
        return response


def _frozen_assets(root):
    asset_root = root / "assets"
    if asset_root.is_symlink():
        raise ValueError("Actas preview assets must not be symlinks")
    assets = {}
    for file in asset_root.rglob("*"):
        if not file.is_file() or file.suffix not in ASSET_SUFFIXES:
            continue
        if file.is_symlink() or not file.resolve().is_relative_to(root):
            raise ValueError("Actas preview assets must stay inside the build")
        body = file.read_bytes()
        content_type = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
        assets[file.relative_to(root).as_posix()] = (
            body,
            content_type,
            hashlib.sha256(body).hexdigest(),
        )
    return MappingProxyType(assets)


def actas_preview_patterns(build_directory):
    """Freeze an explicit local ``apps/sisoc`` build for a disposable preview URLconf.

    The caller supplies its own isolated build directory, never a request path.
    """
    original = Path(build_directory)
    root = original.resolve(strict=True)
    index = root / "index.html"
    if original.is_symlink() or not index.is_file() or index.is_symlink():
        raise ValueError("Actas preview requires a regular fixed index.html")
    index_bytes = (
        index.read_text(encoding="utf-8")
        .replace(BUILD_ASSETS, PUBLIC_ASSETS)
        .encode("utf-8")
    )
    return [
        *_importacion_patterns(index_bytes),
        path("inspecciones/actas/", ActasEntry.as_view(index_bytes=index_bytes)),
        path(
            "inspecciones/actas/<str:numero>/",
            ActaDetalleEntry.as_view(index_bytes=index_bytes),
        ),
        path("inspecciones/", EscuelasEntry.as_view(index_bytes=index_bytes)),
        path(
            "inspecciones/escuelas/nueva/",
            EscuelaNuevaEntry.as_view(index_bytes=index_bytes),
        ),
        path(
            "inspecciones/escuelas/<int:pk>/editar/",
            EscuelaEditarEntry.as_view(index_bytes=index_bytes),
        ),
        path(
            "inspecciones/asignaciones/",
            AsignacionesEntry.as_view(index_bytes=index_bytes),
        ),
        path(
            "inspecciones/asignaciones/nueva/",
            AsignacionNuevaEntry.as_view(index_bytes=index_bytes),
        ),
        path(
            "inspecciones/tablero/",
            TableroEntry.as_view(index_bytes=index_bytes),
        ),
        path(
            "inspecciones/react/<path:asset_path>",
            ReactAssetView.as_view(assets=_frozen_assets(root)),
        ),
    ]
