"""Explicit local React preview of the identity review queue (C02); never mounted by a production URLconf.

``ciudadanos/revision/`` keeps the native URL and guards (login redirect, ``ciudadanos.revision_identidad``,
the native 404 of a page out of range) and only then returns the frozen React ``index.html``. The
resolve actions are the web API ones; assets are shared with the ficha preview under ``/ciudadanos/react/``.
"""

from pathlib import Path

from django.contrib.auth.decorators import login_required
from django.urls import path
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from ciudadanos.views import ColaRevisionView
from ciudadanos.web_preview import (
    BUILD_ASSETS,
    PUBLIC_ASSETS,
    ReactAssetView,
    _frozen_assets,
    _index,
)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ColaRevisionEntry(ColaRevisionView):
    """Native login, permission and page 404 first, then the frozen React index."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        # The native paginator raises its 404 for a page out of range.
        self.get_context_data()
        return _index(request, self.index_bytes)


def cola_revision_preview_patterns(build_directory):
    """Freeze an explicit local ``apps/sisoc`` build for a disposable preview URLconf."""
    original = Path(build_directory)
    root = original.resolve(strict=True)
    index = root / "index.html"
    if original.is_symlink() or not index.is_file() or index.is_symlink():
        raise ValueError("Cola de revision preview requires a regular fixed index.html")
    index_bytes = (
        index.read_text(encoding="utf-8")
        .replace(BUILD_ASSETS, PUBLIC_ASSETS)
        .encode("utf-8")
    )
    return [
        path(
            "ciudadanos/revision/",
            login_required(ColaRevisionEntry.as_view(index_bytes=index_bytes)),
        ),
        path(
            "ciudadanos/react/<path:asset_path>",
            ReactAssetView.as_view(assets=_frozen_assets(root)),
        ),
    ]
