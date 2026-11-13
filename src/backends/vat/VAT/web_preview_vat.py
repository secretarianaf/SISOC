"""Explicit local React preview of the VAT vouchers and evaluaciones (V01.01, V08.01); never mounted by a production URLconf.

Each entry keeps the native URL and the native guards: the same
``permissions_any_required`` decorator as ``VAT/urls.py`` and the native view's
own dispatch (login redirect, queryset 404, invalid ``page`` 404). Only then
the GET returns the frozen React ``index.html``, which loads its data from
``/api/web/vat/``. POSTs (recarga, cancelación) stay the native views. Assets
are served under the backend's own prefix ``/vat/react/``.
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

from core.decorators import permissions_any_required
from VAT.views.evaluacion import (
    EvaluacionCreateView,
    EvaluacionDeleteView,
    EvaluacionDetailView,
    EvaluacionListView,
    EvaluacionUpdateView,
    ResultadoEvaluacionCreateView,
    ResultadoEvaluacionDeleteView,
    ResultadoEvaluacionDetailView,
    ResultadoEvaluacionListView,
    ResultadoEvaluacionUpdateView,
)
from VAT.views.reporte import ReporteInscriptosAsistenciasView
from VAT.views.voucher import (
    VoucherAsignacionMasivaView,
    VoucherCreateView,
    VoucherDetailView,
    VoucherListView,
)
from VAT.views.voucher_parametria import (
    VoucherParametriaCreateView,
    VoucherParametriaDetailView,
    VoucherParametriaListView,
)

BUILD_ASSETS = "/v2/sisoc/assets/"
PUBLIC_ASSETS = "/vat/react/assets/"
ASSET_SUFFIXES = {".js", ".css", ".woff", ".woff2", ".svg", ".png", ".jpg", ".ico"}


def index_response(request, index_bytes):
    response = HttpResponse(
        b"" if request.method == "HEAD" else index_bytes,
        content_type="text/html; charset=utf-8",
    )
    response["Content-Length"] = str(len(index_bytes))
    patch_cache_control(response, private=True, no_store=True)
    patch_vary_headers(response, ("Cookie",))
    return response


def _list_get(view, request, *args, **kwargs):
    """Same ``Http404`` as the native list for an invalid or out-of-range page."""
    view.object_list = view.get_queryset()
    view.get_context_data()
    return index_response(request, view.index_bytes)


def _detail_get(view, request, *args, **kwargs):
    """Same ``Http404`` as the native detail outside its queryset."""
    view.object = view.get_object()
    return index_response(request, view.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class VoucherListEntry(VoucherListView):
    index_bytes = b""
    get = _list_get


@method_decorator(ensure_csrf_cookie, name="dispatch")
class VoucherDetailEntry(VoucherDetailView):
    index_bytes = b""
    get = _detail_get


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ParametriaListEntry(VoucherParametriaListView):
    index_bytes = b""
    get = _list_get


@method_decorator(ensure_csrf_cookie, name="dispatch")
class EvaluacionListEntry(EvaluacionListView):
    index_bytes = b""
    get = _list_get


@method_decorator(ensure_csrf_cookie, name="dispatch")
class EvaluacionDetailEntry(EvaluacionDetailView):
    index_bytes = b""
    get = _detail_get


@method_decorator(ensure_csrf_cookie, name="dispatch")
class EvaluacionCreateEntry(EvaluacionCreateView):
    """GET the React index; POST stays the native form."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.object = None
        return index_response(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class EvaluacionUpdateEntry(EvaluacionUpdateView):
    index_bytes = b""
    get = _detail_get


@method_decorator(ensure_csrf_cookie, name="dispatch")
class EvaluacionDeleteEntry(EvaluacionDeleteView):
    index_bytes = b""
    get = _detail_get


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ResultadoListEntry(ResultadoEvaluacionListView):
    index_bytes = b""
    get = _list_get


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ResultadoDetailEntry(ResultadoEvaluacionDetailView):
    index_bytes = b""
    get = _detail_get


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ResultadoCreateEntry(ResultadoEvaluacionCreateView):
    """GET the React index; POST stays the native form."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.object = None
        return index_response(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ResultadoUpdateEntry(ResultadoEvaluacionUpdateView):
    index_bytes = b""
    get = _detail_get


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ResultadoDeleteEntry(ResultadoEvaluacionDeleteView):
    index_bytes = b""
    get = _detail_get


@method_decorator(ensure_csrf_cookie, name="dispatch")
class VoucherCreateEntry(VoucherCreateView):
    """GET the React index; POST stays the native form."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.object = None
        return index_response(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ParametriaCreateEntry(VoucherParametriaCreateView):
    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.object = None
        return index_response(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class VoucherMasivoEntry(VoucherAsignacionMasivaView):
    index_bytes = b""

    def get(self, request, *args, **kwargs):
        return index_response(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ParametriaDetailEntry(VoucherParametriaDetailView):
    index_bytes = b""
    get = _detail_get


EXPORTS = {
    "csv",
    "xlsx",
    "excel",
    "detalle_csv",
    "detalle-csv",
    "detalle_xlsx",
    "detalle_excel",
    "detalle-xlsx",
}


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ReporteEntry(ReporteInscriptosAsistenciasView):
    """GET the React index; the ``export`` downloads stay the native view."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        if (request.GET.get("export") or "").lower() in EXPORTS:
            return super().get(request, *args, **kwargs)
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
        raise ValueError("VAT preview assets must not be symlinks")
    assets = {}
    for file in asset_root.rglob("*"):
        if not file.is_file() or file.suffix not in ASSET_SUFFIXES:
            continue
        if file.is_symlink() or not file.resolve().is_relative_to(root):
            raise ValueError("VAT preview assets must stay inside the build")
        body = file.read_bytes()
        content_type = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
        assets[file.relative_to(root).as_posix()] = (
            body,
            content_type,
            hashlib.sha256(body).hexdigest(),
        )
    return MappingProxyType(assets)


def _entry(view_class, permission, index_bytes):
    return permissions_any_required([permission])(
        view_class.as_view(index_bytes=index_bytes)
    )


def _entry_any(view_class, permissions, index_bytes):
    return permissions_any_required(permissions)(
        view_class.as_view(index_bytes=index_bytes)
    )


def vat_preview_patterns(build_directory):
    """Freeze an explicit local ``apps/sisoc`` build for a disposable preview URLconf.

    The caller supplies its own isolated build directory, never a request path.
    """
    original = Path(build_directory)
    root = original.resolve(strict=True)
    index = root / "index.html"
    if original.is_symlink() or not index.is_file() or index.is_symlink():
        raise ValueError("VAT preview requires a regular fixed index.html")
    index_bytes = (
        index.read_text(encoding="utf-8")
        .replace(BUILD_ASSETS, PUBLIC_ASSETS)
        .encode("utf-8")
    )
    return [
        path(
            "vat/vouchers/",
            _entry(VoucherListEntry, "VAT.view_voucher", index_bytes),
        ),
        path(
            "vat/vouchers/parametrias/",
            _entry(ParametriaListEntry, "VAT.view_voucher", index_bytes),
        ),
        path(
            "vat/vouchers/<int:pk>/",
            _entry(VoucherDetailEntry, "VAT.view_voucher", index_bytes),
        ),
        path(
            "vat/evaluaciones/",
            _entry(EvaluacionListEntry, "VAT.view_evaluacion", index_bytes),
        ),
        path(
            "vat/evaluaciones/<int:pk>/",
            _entry(EvaluacionDetailEntry, "VAT.view_evaluacion", index_bytes),
        ),
        path(
            "vat/evaluaciones/nueva/",
            _entry(EvaluacionCreateEntry, "VAT.add_evaluacion", index_bytes),
        ),
        path(
            "vat/evaluaciones/<int:pk>/editar/",
            _entry(EvaluacionUpdateEntry, "VAT.change_evaluacion", index_bytes),
        ),
        path(
            "vat/evaluaciones/<int:pk>/eliminar/",
            _entry(EvaluacionDeleteEntry, "VAT.delete_evaluacion", index_bytes),
        ),
        path(
            "vat/resultados-evaluacion/",
            _entry(ResultadoListEntry, "VAT.view_resultadoevaluacion", index_bytes),
        ),
        path(
            "vat/resultados-evaluacion/<int:pk>/",
            _entry(ResultadoDetailEntry, "VAT.view_resultadoevaluacion", index_bytes),
        ),
        path(
            "vat/resultados-evaluacion/nuevo/",
            _entry(ResultadoCreateEntry, "VAT.add_resultadoevaluacion", index_bytes),
        ),
        path(
            "vat/resultados-evaluacion/<int:pk>/editar/",
            _entry(ResultadoUpdateEntry, "VAT.change_resultadoevaluacion", index_bytes),
        ),
        path(
            "vat/resultados-evaluacion/<int:pk>/eliminar/",
            _entry(ResultadoDeleteEntry, "VAT.delete_resultadoevaluacion", index_bytes),
        ),
        path(
            "vat/vouchers/parametrias/<int:pk>/",
            _entry(ParametriaDetailEntry, "VAT.view_voucher", index_bytes),
        ),
        path(
            "vat/vouchers/asignar/",
            _entry(VoucherCreateEntry, "VAT.add_voucher", index_bytes),
        ),
        path(
            "vat/vouchers/asignar-masivo/",
            _entry(VoucherMasivoEntry, "VAT.add_voucher", index_bytes),
        ),
        path(
            "vat/vouchers/parametrias/nueva/",
            _entry(ParametriaCreateEntry, "VAT.add_voucher", index_bytes),
        ),
        path(
            "vat/reportes/inscripciones-asistencias/",
            _entry_any(
                ReporteEntry,
                [
                    "VAT.view_inscripcion",
                    "VAT.view_comisioncurso",
                    "VAT.view_centro",
                ],
                index_bytes,
            ),
        ),
        path(
            "vat/react/<path:asset_path>",
            ReactAssetView.as_view(assets=_frozen_assets(root)),
        ),
    ]
