"""Explicit local React preview of the payment-file imports (EX02); never mounted by a production URLconf.

Each entry keeps the native URL, its route decorator and the native view's
dispatch: anonymous users get the native login redirect or 403, users without
the code the native 403, a missing batch or an invalid ``page`` the native 404.
Only then a GET returns the frozen React ``index.html``, which loads its data
from ``/api/web/comedores/importarexpedientes/``. Other methods reach the native
view unchanged (the native 405 of the import and delete routes included).
Assets are served under the backend's own prefix ``/importarexpedientes/react/``.
"""

from pathlib import Path

from django.urls import path
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from core.decorators import permission_code_required, permissions_any_required
from comedores.web_preview_catalogos import (
    BUILD_ASSETS,
    ReactAssetView,
    _frozen_assets,
    _index,
)
from importarexpediente.views import (
    ImportarExpedienteDetalleListView,
    ImportarExpedienteListView,
    ImportarFechasAcreditacionView,
    ImportExpedientesView,
)
from importarexpediente.web_api_importarexpedientes import (
    ACREDITACION_CODES,
    VIEW_CODE,
)

PUBLIC_ASSETS = "/importarexpedientes/react/assets/"


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ListEntry(ImportarExpedienteListView):
    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        # Same Http404 as the native list for an invalid page.
        self.paginate_queryset(self.object_list, self.get_paginate_by(self.object_list))
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class DetailEntry(ImportarExpedienteDetalleListView):
    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        self.paginate_queryset(self.object_list, self.get_paginate_by(self.object_list))
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class UploadEntry(ImportExpedientesView):
    index_bytes = b""

    def get(self, request, *args, **kwargs):
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class AccreditationEntry(ImportarFechasAcreditacionView):
    index_bytes = b""

    def get(self, request, *args, **kwargs):
        return _index(request, self.index_bytes)


def importarexpedientes_preview_patterns(build_directory):
    """Freeze an explicit local ``apps/sisoc`` build for a disposable preview URLconf.

    The caller supplies its own isolated build directory, never a request path.
    """
    original = Path(build_directory)
    root = original.resolve(strict=True)
    index = root / "index.html"
    if original.is_symlink() or not index.is_file() or index.is_symlink():
        raise ValueError(
            "Importarexpedientes preview requires a regular fixed index.html"
        )
    index_bytes = (
        index.read_text(encoding="utf-8")
        .replace(BUILD_ASSETS, PUBLIC_ASSETS)
        .encode("utf-8")
    )

    def entry(vista):
        return vista.as_view(index_bytes=index_bytes)

    def con_permiso(vista):
        return permission_code_required(VIEW_CODE)(entry(vista))

    fechas = permissions_any_required(ACREDITACION_CODES)(entry(AccreditationEntry))
    return [
        path("importarexpedientes/upload", entry(UploadEntry)),
        path("importarexpedientes/listar", con_permiso(ListEntry)),
        path("importarexpedientes/<int:id_archivo>/", con_permiso(DetailEntry)),
        path("importarexpedientes/<int:id_archivo>/fechas-acreditacion/", fechas),
        path(
            "importarexpedientes/react/<path:asset_path>",
            ReactAssetView.as_view(assets=_frozen_assets(root)),
        ),
    ]
