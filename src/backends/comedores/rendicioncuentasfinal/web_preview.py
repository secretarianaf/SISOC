"""Explicit local React preview of the final rendición screens (RF01.01); never mounted by a production URLconf.

Each entry keeps the native URL, its route decorator and the native view's
dispatch: anonymous users and users without ``view_rendicioncuentasfinal`` get
the native 403 and a comedor that does not exist the native 404. Only then a GET
returns the frozen React ``index.html``, which loads its data from
``/api/web/comedores/rendicion_cuentas_final/``. The detail entry does not run
the native ``get_or_create``: the rendición is created by the API call, as the
native GET does. Assets are served under the backend's own prefix
``/rendicion_cuentas_final/react/``.
"""

from pathlib import Path

from django.shortcuts import get_object_or_404
from django.urls import path
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from comedores.models import Comedor
from comedores.web_preview_catalogos import (
    BUILD_ASSETS,
    ReactAssetView,
    _frozen_assets,
    _index,
)
from core.decorators import permissions_any_required
from rendicioncuentasfinal.urls import _RENDICION_FINAL_PERM
from rendicioncuentasfinal.views import (
    DocumentosRendicionCuentasFinalListView,
    RendicionCuentasFinalDetailView,
)

PUBLIC_ASSETS = "/rendicion_cuentas_final/react/assets/"


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ListadoEntry(DocumentosRendicionCuentasFinalListView):
    index_bytes = b""

    def get(self, request, *args, **kwargs):
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class DetalleEntry(RendicionCuentasFinalDetailView):
    index_bytes = b""

    def get(self, request, *args, **kwargs):
        # Same Http404 as the native detail for a comedor that does not exist.
        get_object_or_404(Comedor.objects.only("id"), pk=self.kwargs["pk"])
        return _index(request, self.index_bytes)


def rendicion_final_preview_patterns(build_directory):
    """Freeze an explicit local ``apps/sisoc`` build for a disposable preview URLconf.

    The caller supplies its own isolated build directory, never a request path.
    """
    original = Path(build_directory)
    root = original.resolve(strict=True)
    index = root / "index.html"
    if original.is_symlink() or not index.is_file() or index.is_symlink():
        raise ValueError("Rendición final preview requires a regular fixed index.html")
    index_bytes = (
        index.read_text(encoding="utf-8")
        .replace(BUILD_ASSETS, PUBLIC_ASSETS)
        .encode("utf-8")
    )
    guard = permissions_any_required(_RENDICION_FINAL_PERM)
    return [
        path(
            "comedores/<int:pk>/rendicion_cuentas_final/",
            guard(DetalleEntry.as_view(index_bytes=index_bytes)),
        ),
        path(
            "rendicion_cuentas_final/listar/",
            guard(ListadoEntry.as_view(index_bytes=index_bytes)),
        ),
        path(
            "rendicion_cuentas_final/react/<path:asset_path>",
            ReactAssetView.as_view(assets=_frozen_assets(root)),
        ),
    ]
