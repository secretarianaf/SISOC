"""Explicit local React preview of the comedor nómina read (CO01).

Never mounted by a production URLconf. Each entry keeps the native URL, the
native route decorator and the native view's dispatch (login, scope): users the
decorator rejects get the native 403, a comedor or admission out of scope the
native 404. Only then a GET returns the frozen React ``index.html``, which loads
its data from ``/api/web/comedores/comedores/``. The add, edit, state, derive,
delete and import routes are not listed here and stay native. Assets are served
under ``/comedores/react/`` by the shared catalog preview.
"""

from pathlib import Path

from django.urls import path
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from core.decorators import permissions_any_required
from comedores.views.nomina import NominaDetailView, NominaDirectaDetailView
from comedores.web_api_nomina import VER_NOMINA
from comedores.web_preview_catalogos import (
    BUILD_ASSETS,
    PUBLIC_ASSETS,
    ReactAssetView,
    _frozen_assets,
    _index,
)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class NominaAdmisionEntry(NominaDetailView):
    index_bytes = b""

    def get(self, request, *args, **kwargs):
        # Same scope check and 404 as the native page.
        self.get_context_data(**kwargs)
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class NominaDirectaEntry(NominaDirectaDetailView):
    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.get_context_data(**kwargs)
        return _index(request, self.index_bytes)


def nomina_preview_patterns(build_directory):
    """Freeze an explicit local ``apps/sisoc`` build for a disposable preview URLconf."""
    original = Path(build_directory)
    root = original.resolve(strict=True)
    index = root / "index.html"
    if original.is_symlink() or not index.is_file() or index.is_symlink():
        raise ValueError("Comedores preview requires a regular fixed index.html")
    index_bytes = (
        index.read_text(encoding="utf-8")
        .replace(BUILD_ASSETS, PUBLIC_ASSETS)
        .encode("utf-8")
    )
    return [
        path(
            "comedores/<int:pk>/admision/<int:admision_pk>/nomina/",
            permissions_any_required(VER_NOMINA)(
                NominaAdmisionEntry.as_view(index_bytes=index_bytes)
            ),
        ),
        path(
            "comedores/<int:pk>/nomina/",
            permissions_any_required(VER_NOMINA)(
                NominaDirectaEntry.as_view(index_bytes=index_bytes)
            ),
        ),
        path(
            "comedores/react/<path:asset_path>",
            ReactAssetView.as_view(assets=_frozen_assets(root)),
        ),
    ]
