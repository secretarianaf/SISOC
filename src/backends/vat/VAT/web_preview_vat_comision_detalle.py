"""Explicit local React preview of the VAT commission detail pages (V04.01, U4); never mounted by a production URLconf.

Each entry keeps the native URL and the native guards: the same
``permissions_any_required`` decorator as ``VAT/urls.py`` and the native view's own scoped
queryset (404 outside the user's scope). Only then the GET returns the frozen React
``index.html``, which loads its data from ``/api/web/vat/``. The writes are sent by React to
the web API.
"""

from pathlib import Path

from django.urls import path
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from VAT.views.curso import ComisionCursoDetailView
from VAT.views.oferta_institucional import ComisionDetailView
from VAT.web_preview_vat import (
    BUILD_ASSETS,
    PUBLIC_ASSETS,
    ReactAssetView,
    _detail_get,
    _entry,
    _frozen_assets,
)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ComisionOfertaDetailEntry(ComisionDetailView):
    index_bytes = b""
    get = _detail_get


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ComisionCursoDetailEntry(ComisionCursoDetailView):
    index_bytes = b""
    get = _detail_get


def comision_detalle_preview_patterns(build_directory):
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
            "vat/comisiones/<int:pk>/",
            _entry(ComisionOfertaDetailEntry, "VAT.view_comision", index_bytes),
        ),
        path(
            "vat/cursos/comisiones/<int:pk>/",
            _entry(ComisionCursoDetailEntry, "VAT.view_comisioncurso", index_bytes),
        ),
        path(
            "vat/react/<path:asset_path>",
            ReactAssetView.as_view(assets=_frozen_assets(root)),
        ),
    ]
