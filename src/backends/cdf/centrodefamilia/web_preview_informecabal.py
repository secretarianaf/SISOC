"""Explicit local React preview of the CDF Informe Cabal screens (CDF01); never mounted by a production URLconf.

Same contract as ``centrodefamilia.web_preview``: each entry keeps the native URL
and guard (``permissions_any_required`` with ``view_centro``, then the native
view's own dispatch and object rule) and only then answers its GET with the
frozen React ``index.html``. Other methods keep the native behaviour; the
preview, process and reprocess AJAX endpoints are not mounted here and stay
native.
"""

from pathlib import Path

from django.urls import path
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from centrodefamilia.views.centro import InformeCabalArchivoPorCentroDetailView
from centrodefamilia.views.informecabal import (
    InformeCabalArchivoDetailView,
    InformeCabalListView,
    InformeCabalRegistroDetailView,
)
from centrodefamilia.web_preview import (
    BUILD_ASSETS,
    PUBLIC_ASSETS,
    ReactAssetView,
    _entry,
    _frozen_assets,
    index_response,
)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class InformeCabalListEntry(InformeCabalListView):
    """History list entry; the CSRF cookie the native page sets stays for its AJAX posts."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        return index_response(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class InformeCabalArchivoEntry(InformeCabalArchivoDetailView):
    """File detail entry: the native object lookup (missing answers 404), then the index."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return index_response(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class InformeCabalRegistroEntry(InformeCabalRegistroDetailView):
    """Registro detail entry: the native object lookup (missing answers 404), then the index."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return index_response(request, self.index_bytes)


class InformeCabalPorCentroEntry(InformeCabalArchivoPorCentroDetailView):
    """The native file and centre lookups (missing answers 404), then the index."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.get_context_data()
        return index_response(request, self.index_bytes)


def cdf_informecabal_preview_patterns(build_directory):
    """Freeze an explicit local ``apps/sisoc`` build for a disposable preview URLconf."""
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
        path(
            "centrodefamilia/informecabal/",
            _entry(InformeCabalListEntry, index_bytes),
        ),
        path(
            "centrodefamilia/informecabal/<int:pk>/",
            _entry(InformeCabalArchivoEntry, index_bytes),
        ),
        path(
            "centrodefamilia/informecabal/registro/<int:pk>/",
            _entry(InformeCabalRegistroEntry, index_bytes),
        ),
        path(
            "centrodefamilia/centros/<int:centro_id>/informecabal/<int:pk>/",
            _entry(InformeCabalPorCentroEntry, index_bytes),
        ),
        path(
            "centrodefamilia/react/<path:asset_path>",
            ReactAssetView.as_view(assets=_frozen_assets(root)),
        ),
    ]
