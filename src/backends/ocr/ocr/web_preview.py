"""Explicit local React preview of the OCR screens; never mounted by a production URLconf.

The entries keep the native URLs, ``AdminRequiredMixin`` dispatch (login
redirect, 403 without ``ocr.use_ocr``) and the native batch lookup (a missing
or foreign batch is the native 404). Only then a GET returns the frozen
``apps/sisoc`` ``index.html``, which loads its data from ``/api/web/ocr/``.
Other methods and the text download stay native. Assets are served under the
backend's own prefix (``/ocr/react/``).
"""

import hashlib
import mimetypes
from pathlib import Path
from types import MappingProxyType

from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import path
from django.utils.cache import patch_cache_control, patch_vary_headers
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import ensure_csrf_cookie

from ocr.models import OCRJob
from ocr.views import OCRJobDetailView, OCRUploadView

BUILD_ASSETS = "/v2/sisoc/assets/"
PUBLIC_ASSETS = "/ocr/react/assets/"
ASSET_SUFFIXES = {".js", ".css", ".woff", ".woff2", ".svg", ".png", ".jpg", ".ico"}


def _index(request, index_bytes):
    response = HttpResponse(
        b"" if request.method == "HEAD" else index_bytes,
        content_type="text/html; charset=utf-8",
    )
    response["Content-Length"] = str(len(index_bytes))
    patch_cache_control(response, private=True, no_store=True)
    patch_vary_headers(response, ("Cookie",))
    return response


@method_decorator(ensure_csrf_cookie, name="dispatch")
class UploadEntry(OCRUploadView):
    index_bytes = b""

    def get(self, request, *args, **kwargs):
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class JobDetailEntry(OCRJobDetailView):
    """Native lookup first: a missing or foreign batch is the native 404."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        filters = {"pk": kwargs["pk"]}
        if not request.user.is_superuser:
            filters["requested_by"] = request.user
        get_object_or_404(OCRJob, **filters)
        return _index(request, self.index_bytes)


class ReactAssetView(View):
    """Serve only frozen build assets; no request data reaches a static upstream."""

    http_method_names = ["get", "head"]
    assets = None

    def get(self, request, asset_path):
        asset = self.assets.get(asset_path) if self.assets is not None else None
        if request.META.get("QUERY_STRING") or asset is None:
            raise Http404()
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
        raise ValueError("OCR preview assets must not be symlinks")
    assets = {}
    for file in asset_root.rglob("*"):
        if not file.is_file() or file.suffix not in ASSET_SUFFIXES:
            continue
        if file.is_symlink() or not file.resolve().is_relative_to(root):
            raise ValueError("OCR preview assets must stay inside the build")
        body = file.read_bytes()
        content_type = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
        assets[file.relative_to(root).as_posix()] = (
            body,
            content_type,
            hashlib.sha256(body).hexdigest(),
        )
    return MappingProxyType(assets)


def ocr_preview_patterns(build_directory):
    """Freeze an explicit local ``apps/sisoc`` build for a disposable preview URLconf.

    The caller supplies its own isolated build directory, never a request path.
    """
    original = Path(build_directory)
    root = original.resolve(strict=True)
    index = root / "index.html"
    if original.is_symlink() or not index.is_file() or index.is_symlink():
        raise ValueError("OCR preview requires a regular fixed index.html")
    index_bytes = (
        index.read_text(encoding="utf-8")
        .replace(BUILD_ASSETS, PUBLIC_ASSETS)
        .encode("utf-8")
    )
    return [
        path("ocr/", UploadEntry.as_view(index_bytes=index_bytes)),
        path("ocr/<int:pk>/", JobDetailEntry.as_view(index_bytes=index_bytes)),
        path(
            "ocr/react/<path:asset_path>",
            ReactAssetView.as_view(assets=_frozen_assets(root)),
        ),
    ]
