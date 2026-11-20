"""Explicit local React preview of the CDI form screens; never mounted by a production URLconf.

Each entry keeps the native URL, the same ``permissions_any_required`` decorator
as ``centrodeinfancia/urls.py`` and the native view's own dispatch (login,
scope, the "generar usuario" rule). Only then the GET returns the frozen React
``index.html``, which loads its data from ``/api/web/cdi/``. Other methods keep
the native behaviour. Assets are the same frozen build as
``centrodeinfancia.web_preview``.
"""

from pathlib import Path

from django.urls import path
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from centrodeinfancia.views_usuario_cdi import GenerarUsuarioCDIView
from centrodeinfancia.web_preview import (
    BUILD_ASSETS,
    PUBLIC_ASSETS,
    ReactAssetView,
    _entry,
    _frozen_assets,
    index_response,
)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class UsuarioGenerarEntry(GenerarUsuarioCDIView):
    """Native guards (404 centre, 403 rule), then the index; POST stays native."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        return index_response(request, self.index_bytes)


def formularios_preview_patterns(build_directory):
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
            "centrodeinfancia/<int:pk>/generar-usuario/",
            _entry(
                UsuarioGenerarEntry,
                "centrodeinfancia.view_centrodeinfancia",
                index_bytes,
            ),
        ),
        path(
            "centrodeinfancia/react/<path:asset_path>",
            ReactAssetView.as_view(assets=_frozen_assets(root)),
        ),
    ]
