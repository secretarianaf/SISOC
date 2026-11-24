"""Explicit local React preview of the comedor technical-team assignment (CO07).

Never mounted by a production URLconf. The entry keeps the native URL, the native route
decorator and the native view's login check; the scoped comedor lookup decides first (a comedor
outside the user's scope is the native 404). Only then a GET returns the frozen React
``index.html``, which loads its data from ``/api/web/comedores/asignar-dupla/``. The POST stays
native. Assets are served under ``/comedores/dupla/react/``.
"""

from pathlib import Path

from django.urls import path
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from comedores.services.comedor_service import ComedorService
from comedores.views.dupla import AsignarDuplaListView
from comedores.web_api_dupla_asignar import ASSIGN_PERMISSIONS
from comedores.web_preview_catalogos import (
    BUILD_ASSETS,
    ReactAssetView,
    _frozen_assets,
    _index,
)
from core.decorators import permissions_any_required

PUBLIC_ASSETS = "/comedores/dupla/react/assets/"


@method_decorator(ensure_csrf_cookie, name="dispatch")
class AsignarEntry(AsignarDuplaListView):
    index_bytes = b""

    def get(self, request, *args, **kwargs):
        ComedorService.get_scoped_comedor_or_404(self.kwargs["pk"], request.user)
        return _index(request, self.index_bytes)


def dupla_asignar_preview_patterns(build_directory):
    """Freeze an explicit local ``apps/sisoc`` build for a disposable preview URLconf."""
    original = Path(build_directory)
    root = original.resolve(strict=True)
    index = root / "index.html"
    if original.is_symlink() or not index.is_file() or index.is_symlink():
        raise ValueError("Dupla asignar preview requires a regular fixed index.html")
    index_bytes = (
        index.read_text(encoding="utf-8")
        .replace(BUILD_ASSETS, PUBLIC_ASSETS)
        .encode("utf-8")
    )
    return [
        path(
            "comedores/dupla/asignar/<int:pk>",
            permissions_any_required(ASSIGN_PERMISSIONS)(
                AsignarEntry.as_view(index_bytes=index_bytes)
            ),
        ),
        path(
            "comedores/dupla/react/<path:asset_path>",
            ReactAssetView.as_view(assets=_frozen_assets(root)),
        ),
    ]
