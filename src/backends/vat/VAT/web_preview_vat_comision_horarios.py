"""Explicit local React preview of the VAT commission schedule list and detail screens (V04.01, U4); never mounted by a production URLconf.

Each entry keeps the native URL and the native guard (the same ``permissions_any_required`` decorator as ``VAT/urls.py``)
and the native view's own dispatch (login redirect, scoped queryset 404, invalid ``page`` 404). Only then the GET returns
the frozen React ``index.html``, which loads its data from ``/api/web/vat/``.
"""

from pathlib import Path

from django.urls import path
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from VAT.views.oferta_institucional import (
    ComisionHorarioDetailView,
    ComisionHorarioListView,
)
from VAT.web_preview_vat import (
    BUILD_ASSETS,
    PUBLIC_ASSETS,
    ReactAssetView,
    _detail_get,
    _entry,
    _frozen_assets,
    _list_get,
)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ComisionHorarioListEntry(ComisionHorarioListView):
    index_bytes = b""
    get = _list_get


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ComisionHorarioDetailEntry(ComisionHorarioDetailView):
    index_bytes = b""
    get = _detail_get


def comision_horarios_preview_patterns(build_directory):
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
    return [
        path(
            "vat/comisiones/horarios/",
            _entry(ComisionHorarioListEntry, "VAT.view_comisionhorario", index_bytes),
        ),
        path(
            "vat/comisiones/horarios/<int:pk>/",
            _entry(ComisionHorarioDetailEntry, "VAT.view_comisionhorario", index_bytes),
        ),
        path(
            "vat/react/<path:asset_path>",
            ReactAssetView.as_view(assets=_frozen_assets(root)),
        ),
    ]
