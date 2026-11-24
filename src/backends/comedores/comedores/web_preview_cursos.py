"""Explicit local React preview of the global app-mobile course catalog (CO04.01).

Never mounted by a production URLconf. Each entry keeps the native URL, the native
route decorator (``auth.role_admin``) and the native view's dispatch (login, list
paging, object lookup): users the decorator rejects get the native 403 and a missing
course the native 404. Only then a GET returns the frozen React ``index.html``, which
loads its data from ``/api/web/comedores/cursos-app-mobile/``. Every POST stays
native. Assets are served under ``/comedores/react/`` like the other comedor previews.
"""

from pathlib import Path

from django.urls import path
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from comedores.views.cursos_app_mobile import (
    CursoAppMobileCreateView,
    CursoAppMobileDeleteView,
    CursoAppMobileListView,
    CursoAppMobileUpdateView,
)
from comedores.web_preview_catalogos import (
    BUILD_ASSETS,
    PUBLIC_ASSETS,
    ReactAssetView,
    _frozen_assets,
    _index,
)
from core.decorators import permissions_any_required

PERMISOS = ["auth.role_admin"]


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ListadoEntry(CursoAppMobileListView):
    index_bytes = b""

    def get(self, request, *args, **kwargs):
        # Same 404 as the native page for a page out of range.
        self.object_list = self.get_queryset()
        self.get_context_data()
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CrearEntry(CursoAppMobileCreateView):
    index_bytes = b""

    def get(self, request, *args, **kwargs):
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class EditarEntry(CursoAppMobileUpdateView):
    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.get_object()
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class BajaEntry(CursoAppMobileDeleteView):
    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.get_object()
        return _index(request, self.index_bytes)


def cursos_preview_patterns(build_directory):
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

    def entry(vista):
        return permissions_any_required(PERMISOS)(
            vista.as_view(index_bytes=index_bytes)
        )

    return [
        path("comedores/configuracion/cursos-app-mobile/", entry(ListadoEntry)),
        path("comedores/configuracion/cursos-app-mobile/crear/", entry(CrearEntry)),
        path(
            "comedores/configuracion/cursos-app-mobile/<int:pk>/editar/",
            entry(EditarEntry),
        ),
        path(
            "comedores/configuracion/cursos-app-mobile/<int:pk>/eliminar/",
            entry(BajaEntry),
        ),
        path(
            "comedores/react/<path:asset_path>",
            ReactAssetView.as_view(assets=_frozen_assets(root)),
        ),
    ]
