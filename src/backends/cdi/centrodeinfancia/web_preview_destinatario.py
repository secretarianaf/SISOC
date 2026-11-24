"""Explicit local React preview of the CDI destinatario screens; never mounted by a production URLconf.

Each entry keeps the native URL, the same ``permissions_any_required`` decorator
as ``centrodeinfancia/urls.py`` and the native view's own dispatch (login,
scope, the CDI-A3 veto on writes). Only then the GET returns the frozen React
``index.html``, which loads its data from ``/api/web/cdi/``. Other methods keep
the native behaviour. Assets are the same frozen build as
``centrodeinfancia.web_preview``.
"""

from pathlib import Path

from django.urls import path
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from centrodeinfancia.views import (
    NominaCentroInfanciaCreateView,
    NominaCentroInfanciaEditView,
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
class DestinatarioCrearEntry(NominaCentroInfanciaCreateView):
    """Native guards and the scoped centre (404), then the index; POST stays native."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.object = None
        self.get_context_data()
        return index_response(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class DestinatarioEditarEntry(NominaCentroInfanciaEditView):
    """Native guards and the scoped ficha (404), then the index; POST stays native."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return index_response(request, self.index_bytes)


def destinatario_preview_patterns(build_directory):
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
            "centrodeinfancia/<int:pk>/nomina/crear/",
            _entry(
                DestinatarioCrearEntry,
                "centrodeinfancia.add_nominacentroinfancia",
                index_bytes,
            ),
        ),
        path(
            "centrodeinfancia/<int:pk>/nomina/<int:nomina_id>/editar/",
            _entry(
                DestinatarioEditarEntry,
                "centrodeinfancia.change_nominacentroinfancia",
                index_bytes,
            ),
        ),
        path(
            "centrodeinfancia/react/<path:asset_path>",
            ReactAssetView.as_view(assets=_frozen_assets(root)),
        ),
    ]
