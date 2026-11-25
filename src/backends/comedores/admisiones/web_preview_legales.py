"""Explicit local React preview of the legal admision pages (AD03.03).

Never mounted by a production URLconf. Each entry keeps the native URL, the native route
decorator (``permissions_any_required``) and the native view's object lookup: users the
decorator rejects get the native 403, a missing admision the native 404. Only then a GET
returns the frozen React ``index.html``, which loads its data from
``/api/web/comedores/admisiones/legales/``. The native ``post()`` handlers are untouched.
"""

from pathlib import Path

from django.urls import path
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from core.decorators import permissions_any_required
from comedores.web_preview_catalogos import (
    BUILD_ASSETS,
    PUBLIC_ASSETS,
    ReactAssetView,
    _frozen_assets,
    _index,
)
from admisiones.views.web_views import (
    AdmisionesLegalesDetailView,
    InformeTecnicoComplementarioReviewView,
)
from admisiones.web_api_listas import LEGALES_PERMISSIONS


@method_decorator(ensure_csrf_cookie, name="dispatch")
class LegalDetalleEntry(AdmisionesLegalesDetailView):
    """GET serves the index after the native lookup; the native ``post()`` stays."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class RevisionEntry(InformeTecnicoComplementarioReviewView):
    """GET serves the index after the native lookup; the native ``post()`` stays."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return _index(request, self.index_bytes)


def legales_preview_patterns(build_directory):
    """Freeze an explicit local ``apps/sisoc`` build for a disposable preview URLconf."""
    original = Path(build_directory)
    root = original.resolve(strict=True)
    index = root / "index.html"
    if original.is_symlink() or not index.is_file() or index.is_symlink():
        raise ValueError("Admision preview requires a regular fixed index.html")
    index_bytes = (
        index.read_text(encoding="utf-8")
        .replace(BUILD_ASSETS, PUBLIC_ASSETS)
        .encode("utf-8")
    )

    def entry(vista):
        return permissions_any_required(LEGALES_PERMISSIONS)(
            vista.as_view(index_bytes=index_bytes)
        )

    return [
        path("comedores/admisiones/legales/ver/<int:pk>", entry(LegalDetalleEntry)),
        path(
            "comedores/admisiones/legales/revisar-complementario/<int:pk>",
            entry(RevisionEntry),
        ),
        path(
            "comedores/react/<path:asset_path>",
            ReactAssetView.as_view(assets=_frozen_assets(root)),
        ),
    ]
