"""Explicit local React preview of the VAT curricular plan screens (V07.01); never mounted by a production URLconf.

Each entry keeps the native URL and the native guard (the same ``permissions_any_required`` decorator as ``VAT/urls.py``)
and the native view's own dispatch (role guard, login redirect, scoped queryset 404, invalid ``page`` 404). Only then the
GET returns the frozen React ``index.html``, which loads its data from ``/api/web/vat/``. POSTs go to the web API; the
delete confirmation (``eliminar/``) stays the native page.
"""

from pathlib import Path

from django.urls import path
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from VAT.views.catalogo import (
    PlanVersionCurricularCreateView,
    PlanVersionCurricularDetailView,
    PlanVersionCurricularListView,
    PlanVersionCurricularUpdateView,
)
from VAT.web_preview_vat import (
    BUILD_ASSETS,
    PUBLIC_ASSETS,
    ReactAssetView,
    _detail_get,
    _entry,
    _frozen_assets,
    _list_get,
    index_response,
)


def _new_get(view, request, *args, **kwargs):
    """The create form has no object: the React index is served as is."""
    view.object = None
    return index_response(request, view.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class PlanListEntry(PlanVersionCurricularListView):
    index_bytes = b""
    get = _list_get


@method_decorator(ensure_csrf_cookie, name="dispatch")
class PlanDetailEntry(PlanVersionCurricularDetailView):
    index_bytes = b""
    get = _detail_get


@method_decorator(ensure_csrf_cookie, name="dispatch")
class PlanCreateEntry(PlanVersionCurricularCreateView):
    index_bytes = b""
    get = _new_get


@method_decorator(ensure_csrf_cookie, name="dispatch")
class PlanUpdateEntry(PlanVersionCurricularUpdateView):
    index_bytes = b""
    get = _detail_get


def planes_preview_patterns(build_directory):
    """Freeze an explicit local ``apps/sisoc`` build for a disposable preview URLconf."""
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
    base = "vat/catalogos/planes-curriculares/"
    return [
        path(
            base,
            _entry(PlanListEntry, "VAT.view_planversioncurricular", index_bytes),
        ),
        path(
            f"{base}nuevo/",
            _entry(PlanCreateEntry, "VAT.add_planversioncurricular", index_bytes),
        ),
        path(
            f"{base}<int:pk>/",
            _entry(PlanDetailEntry, "VAT.view_planversioncurricular", index_bytes),
        ),
        path(
            f"{base}<int:pk>/editar/",
            _entry(PlanUpdateEntry, "VAT.change_planversioncurricular", index_bytes),
        ),
        path(
            "vat/react/<path:asset_path>",
            ReactAssetView.as_view(assets=_frozen_assets(root)),
        ),
    ]
