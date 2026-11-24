"""Explicit local React preview of the CDI intervention form; never mounted by a production URLconf.

Each entry keeps the native URL, the same ``permissions_any_required`` decorator
as ``centrodeinfancia/urls.py`` and the native view's own dispatch (login, scope
of the edited object). Only then the GET returns the frozen React ``index.html``.
Other methods keep the native behaviour.
"""

from pathlib import Path

from django.urls import path
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from centrodeinfancia.views import (
    IntervencionCentroInfanciaCreateView,
    IntervencionCentroInfanciaUpdateView,
)
from centrodeinfancia.web_preview import (
    BUILD_ASSETS,
    PUBLIC_ASSETS,
    ReactAssetView,
    _entry,
    _frozen_assets,
    index_response,
)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class IntervencionCrearEntry(IntervencionCentroInfanciaCreateView):
    """Native guards, then the index; POST stays native."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        return index_response(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class IntervencionEditarEntry(IntervencionCentroInfanciaUpdateView):
    """Native guards and the scoped intervention (404), then the index; POST stays native."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return index_response(request, self.index_bytes)


def intervencion_form_preview_patterns(build_directory):
    """Freeze an explicit local ``apps/sisoc`` build for a disposable preview URLconf."""
    original = Path(build_directory)
    root = original.resolve(strict=True)
    index = root / "index.html"
    if original.is_symlink() or not index.is_file() or index.is_symlink():
        raise ValueError("CDI preview requires a regular fixed index.html")
    index_bytes = (
        index.read_text(encoding="utf-8")
        .replace(BUILD_ASSETS, PUBLIC_ASSETS)
        .encode("utf-8")
    )
    return [
        path(
            "centrodeinfancia/intervencion/crear/<int:pk>",
            _entry(
                IntervencionCrearEntry,
                "centrodeinfancia.add_intervencioncentroinfancia",
                index_bytes,
            ),
        ),
        path(
            "centrodeinfancia/intervencion/editar/<int:pk>/<int:pk2>",
            _entry(
                IntervencionEditarEntry,
                "centrodeinfancia.change_intervencioncentroinfancia",
                index_bytes,
            ),
        ),
        path(
            "centrodeinfancia/react/<path:asset_path>",
            ReactAssetView.as_view(assets=_frozen_assets(root)),
        ),
    ]
