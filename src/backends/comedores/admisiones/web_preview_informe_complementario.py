"""Explicit local React preview of the complementary report page (AD02.02).

Never mounted by a production URLconf. The entry keeps the native URL, the native route
decorator (``permissions_any_required``) and the native view's queryset: users it rejects
get the native 403, a missing report the native 404. Only then a GET returns the frozen
React ``index.html``, which loads its data from
``/api/web/comedores/admisiones/informes/complementario/<tipo>/<pk>/``. The native
``post()`` is untouched.
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
from admisiones.views.web_views import InformeTecnicoComplementarioDetailView
from admisiones.web_api_informes import INFORME_VIEW_PERMISSIONS


@method_decorator(ensure_csrf_cookie, name="dispatch")
class InformeComplementarioEntry(InformeTecnicoComplementarioDetailView):
    """GET serves the index; the native ``post()`` still handles the form."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return _index(request, self.index_bytes)


def complementario_preview_patterns(build_directory):
    """Freeze an explicit local ``apps/sisoc`` build for a disposable preview URLconf."""
    original = Path(build_directory)
    root = original.resolve(strict=True)
    index = root / "index.html"
    if original.is_symlink() or not index.is_file() or index.is_symlink():
        raise ValueError("Report preview requires a regular fixed index.html")
    index_bytes = (
        index.read_text(encoding="utf-8")
        .replace(BUILD_ASSETS, PUBLIC_ASSETS)
        .encode("utf-8")
    )
    return [
        path(
            "comedores/admision/informe_complementario/<str:tipo>/<int:pk>/ver/",
            permissions_any_required(INFORME_VIEW_PERMISSIONS)(
                InformeComplementarioEntry.as_view(index_bytes=index_bytes)
            ),
        ),
        path(
            "comedores/react/<path:asset_path>",
            ReactAssetView.as_view(assets=_frozen_assets(root)),
        ),
    ]
