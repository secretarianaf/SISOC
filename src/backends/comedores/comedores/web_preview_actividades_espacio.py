"""Explicit local React preview of the comedor activity screens (CO03.02).

Never mounted by a production URLconf. Each entry keeps the native URL, the
native route decorator and the native view's dispatch (login, scoped comedor, the
"only PNUD comedores" 404, the permission of the mixin): users the decorator
rejects get the native 403, anything out of scope the native 404. Only then a GET
returns the frozen React ``index.html``, which loads its data from
``/api/web/comedores/actividades-espacio/``. Assets are served under
``/comedores/react/`` like the other comedor previews.
"""

from pathlib import Path

from django.urls import path
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from comedores.views.actividad_espacio_pwa import (
    ActividadEspacioPWACreateView,
    ActividadEspacioPWAUpdateView,
)
from comedores.web_preview_catalogos import (
    BUILD_ASSETS,
    PUBLIC_ASSETS,
    ReactAssetView,
    _frozen_assets,
    _index,
)
from core.decorators import permissions_any_required

PERMISOS = ["auth.role_admin", "pwa.manage_colaboradores_pwa"]


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CrearEntry(ActividadEspacioPWACreateView):
    index_bytes = b""

    def get(self, request, *args, **kwargs):
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class EditarEntry(ActividadEspacioPWAUpdateView):
    index_bytes = b""

    def get(self, request, *args, **kwargs):
        # Same 404 as the native page for an activity outside the comedor.
        self.get_object()
        return _index(request, self.index_bytes)


def actividades_espacio_preview_patterns(build_directory):
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
            "comedores/<int:pk>/actividades/crear/",
            permissions_any_required(PERMISOS)(
                CrearEntry.as_view(index_bytes=index_bytes)
            ),
        ),
        path(
            "comedores/<int:pk>/actividades/<int:pk2>/editar/",
            permissions_any_required(PERMISOS)(
                EditarEntry.as_view(index_bytes=index_bytes)
            ),
        ),
        path(
            "comedores/react/<path:asset_path>",
            ReactAssetView.as_view(assets=_frozen_assets(root)),
        ),
    ]
