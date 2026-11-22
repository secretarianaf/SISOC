"""Explicit local React preview of the comedor "Agregar a Nómina" screen (CO01).

Never mounted by a production URLconf. Each entry keeps the native URL, the native route decorator
and the native view's login check; the scoped lookups decide first (a comedor or admission outside
the user's scope, or a direct nómina of a comedor that needs an admission, is the native 404).
Only then a GET returns the frozen React ``index.html``, which loads its data from
``/api/web/comedores/nomina-crear/``. Every POST stays native. Assets are served under
``/comedores/nomina-crear/react/``.
"""

from pathlib import Path

from django.urls import path
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from comedores.views.nomina import (
    NominaCreateView,
    NominaDirectaCreateView,
    _get_admision_del_comedor_or_404,
    _get_comedor_directo_or_404,
)
from comedores.web_api_nomina_crear import ADD_PERMISSIONS
from comedores.web_preview_catalogos import (
    BUILD_ASSETS,
    ReactAssetView,
    _frozen_assets,
    _index,
)
from core.decorators import permissions_any_required

PUBLIC_ASSETS = "/comedores/nomina-crear/react/assets/"


@method_decorator(ensure_csrf_cookie, name="dispatch")
class AdmisionEntry(NominaCreateView):
    index_bytes = b""

    def get(self, request, *args, **kwargs):
        _get_admision_del_comedor_or_404(
            self.kwargs["pk"], self.kwargs["admision_pk"], request.user
        )
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class DirectaEntry(NominaDirectaCreateView):
    index_bytes = b""

    def get(self, request, *args, **kwargs):
        _get_comedor_directo_or_404(self.kwargs["pk"], request.user)
        return _index(request, self.index_bytes)


def nomina_crear_preview_patterns(build_directory):
    """Freeze an explicit local ``apps/sisoc`` build for a disposable preview URLconf."""
    original = Path(build_directory)
    root = original.resolve(strict=True)
    index = root / "index.html"
    if original.is_symlink() or not index.is_file() or index.is_symlink():
        raise ValueError("Nomina crear preview requires a regular fixed index.html")
    index_bytes = (
        index.read_text(encoding="utf-8")
        .replace(BUILD_ASSETS, PUBLIC_ASSETS)
        .encode("utf-8")
    )
    return [
        path(
            "comedores/<int:pk>/admision/<int:admision_pk>/nomina/crear/",
            permissions_any_required(ADD_PERMISSIONS)(
                AdmisionEntry.as_view(index_bytes=index_bytes)
            ),
        ),
        path(
            "comedores/<int:pk>/nomina/crear/",
            permissions_any_required(ADD_PERMISSIONS)(
                DirectaEntry.as_view(index_bytes=index_bytes)
            ),
        ),
        path(
            "comedores/nomina-crear/react/<path:asset_path>",
            ReactAssetView.as_view(assets=_frozen_assets(root)),
        ),
    ]
