"""Explicit local React preview of CDF screens; never mounted by a production URLconf.

Each entry keeps the native URL and the native guards: the same
``permissions_any_required`` decorator as ``centrodefamilia/urls.py`` and the
native view's own dispatch and object rule (scope 403, missing 404). Only then
the GET returns the frozen React ``index.html``, which loads its data from
``/api/web/cdf/``. Other methods keep the native behaviour. Assets stay under
the backend's own prefix (``/centrodefamilia/react/``), so the core forwards
them like any other route.
"""

import hashlib
import mimetypes
from pathlib import Path
from types import MappingProxyType

from django.http import HttpResponse
from django.urls import path
from django.utils.cache import patch_cache_control, patch_vary_headers
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import ensure_csrf_cookie

from centrodefamilia.views.beneficiarios import (
    BeneficiariosCreateView,
    BeneficiariosDetailView,
    BeneficiariosListView,
    ResponsableDetailView,
    ResponsableListView,
)
from centrodefamilia.views.centro import (
    CentroCreateView,
    CentroDeleteView,
    CentroDetailView,
    CentroListView,
    CentroUpdateView,
)
from centrodefamilia.views.generar_usuario import GenerarUsuarioCDFView
from core.decorators import permissions_any_required

BUILD_ASSETS = "/v2/sisoc/assets/"
PUBLIC_ASSETS = "/centrodefamilia/react/assets/"
ASSET_SUFFIXES = {".js", ".css", ".woff", ".woff2", ".svg", ".png", ".jpg", ".ico"}
VIEW_CENTRO = "centrodefamilia.view_centro"


def index_response(request, index_bytes):
    response = HttpResponse(
        b"" if request.method == "HEAD" else index_bytes,
        content_type="text/html; charset=utf-8",
    )
    response["Content-Length"] = str(len(index_bytes))
    patch_cache_control(response, private=True, no_store=True)
    patch_vary_headers(response, ("Cookie",))
    return response


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CentroListEntry(CentroListView):
    """Native guards, then the frozen React index (NoCount never 404s)."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        return index_response(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CentroDetailEntry(CentroDetailView):
    """The native object rule (403 out of scope, 404 missing), then the index."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return index_response(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CentroCreateEntry(CentroCreateView):
    """Create form entry; POST stays the native form."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        return index_response(request, self.index_bytes)


def _object_entry_get(view, request, *args, **kwargs):
    """After the native ``dispatch`` rule (403/404), the GET serves the index."""
    view.object = view.get_object()
    return index_response(request, view.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CentroUpdateEntry(CentroUpdateView):
    """Edit entry; the native referente/SSE rule runs first, POST stays native."""

    index_bytes = b""
    get = _object_entry_get


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CentroDeleteEntry(CentroDeleteView):
    """Delete confirmation entry; POST stays the native soft delete."""

    index_bytes = b""
    get = _object_entry_get


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CentroGenerarUsuarioEntry(GenerarUsuarioCDFView):
    """User generation entry; the native 404 and generation rule run first."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        return index_response(request, self.index_bytes)


def _list_entry_get(view, request, *args, **kwargs):
    """The native ``ListView`` pagination rule (invalid page 404), then the index."""
    queryset = view.get_queryset()
    view.paginate_queryset(queryset, view.get_paginate_by(queryset))
    return index_response(request, view.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class BeneficiariosListEntry(BeneficiariosListView):
    """Beneficiaries list entry (exact pages: a bad page answers 404)."""

    index_bytes = b""
    get = _list_entry_get


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ResponsablesListEntry(ResponsableListView):
    """Responsables list entry (NoCount pages never 404)."""

    index_bytes = b""
    get = _list_entry_get


@method_decorator(ensure_csrf_cookie, name="dispatch")
class BeneficiarioDetailEntry(BeneficiariosDetailView):
    """Beneficiary detail entry; missing or soft deleted answers 404."""

    index_bytes = b""
    get = _object_entry_get


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ResponsableDetailEntry(ResponsableDetailView):
    """Responsable detail entry; missing or soft deleted answers 404."""

    index_bytes = b""
    get = _object_entry_get


@method_decorator(ensure_csrf_cookie, name="dispatch")
class PreinscripcionEntry(BeneficiariosCreateView):
    """Preinscription entry; the native POST stays the native view."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        return index_response(request, self.index_bytes)


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
        raise ValueError("CDF preview assets must not be symlinks")
    assets = {}
    for file in asset_root.rglob("*"):
        if not file.is_file() or file.suffix not in ASSET_SUFFIXES:
            continue
        if file.is_symlink() or not file.resolve().is_relative_to(root):
            raise ValueError("CDF preview assets must stay inside the build")
        body = file.read_bytes()
        content_type = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
        assets[file.relative_to(root).as_posix()] = (
            body,
            content_type,
            hashlib.sha256(body).hexdigest(),
        )
    return MappingProxyType(assets)


def _entry(view_class, index_bytes):
    return permissions_any_required([VIEW_CENTRO])(
        view_class.as_view(index_bytes=index_bytes)
    )


def cdf_preview_patterns(build_directory):
    """Freeze an explicit local ``apps/sisoc`` build for a disposable preview URLconf.

    The caller supplies its own isolated build directory, never a request path.
    """
    original = Path(build_directory)
    root = original.resolve(strict=True)
    index = root / "index.html"
    if original.is_symlink() or not index.is_file() or index.is_symlink():
        raise ValueError("CDF preview requires a regular fixed index.html")
    index_bytes = (
        index.read_text(encoding="utf-8")
        .replace(BUILD_ASSETS, PUBLIC_ASSETS)
        .encode("utf-8")
    )
    return [
        path("centrodefamilia/centros/", _entry(CentroListEntry, index_bytes)),
        path(
            "centrodefamilia/centros/<int:pk>/",
            _entry(CentroDetailEntry, index_bytes),
        ),
        path(
            "centrodefamilia/centros/nuevo/",
            _entry(CentroCreateEntry, index_bytes),
        ),
        path(
            "centrodefamilia/centros/<int:pk>/editar/",
            _entry(CentroUpdateEntry, index_bytes),
        ),
        path(
            "centrodefamilia/centros/<int:pk>/eliminar/",
            _entry(CentroDeleteEntry, index_bytes),
        ),
        path(
            "centrodefamilia/centros/<int:pk>/generar-usuario/",
            _entry(CentroGenerarUsuarioEntry, index_bytes),
        ),
        path(
            "centrodefamilia/beneficiarios/beneficiarios/",
            _entry(BeneficiariosListEntry, index_bytes),
        ),
        path(
            "centrodefamilia/beneficiarios/beneficiarios/<int:pk>/",
            _entry(BeneficiarioDetailEntry, index_bytes),
        ),
        path(
            "centrodefamilia/beneficiarios/nuevo/",
            _entry(PreinscripcionEntry, index_bytes),
        ),
        path(
            "centrodefamilia/beneficiarios/responsables/",
            _entry(ResponsablesListEntry, index_bytes),
        ),
        path(
            "centrodefamilia/beneficiarios/responsables/<int:pk>/",
            _entry(ResponsableDetailEntry, index_bytes),
        ),
        path(
            "centrodefamilia/react/<path:asset_path>",
            ReactAssetView.as_view(assets=_frozen_assets(root)),
        ),
    ]
