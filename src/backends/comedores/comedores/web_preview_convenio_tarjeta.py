"""Explicit local React preview of the comedor convenio PNUD and card holder pages (CO07.03).

Never mounted by a production URLconf. The entry keeps the native URL, the
native route decorator and the native view's dispatch (login, object scope and
the "only PNUD or Abordaje Comunitario" refusal with its flash message and
redirect). Only then a GET returns the frozen React ``index.html``, which loads
its data from ``/api/web/comedores/comedores/<pk>/convenio-pnud/``. Unlike the
native GET, the entry does not create the empty convenio record: the React page
does it when it reads the API, as the native page did. Assets are served under
``/convenio-tarjeta/react/``.

The card holder entry (``comedores/<pk>/responsable-tarjeta/editar``) keeps the
native route decorator (``auth.role_tecnico_comedor``) and the native dispatch:
the exact ``Tecnico Comedor`` group, the Alimentar Comunidad program and the
object scope decide first (404 otherwise); only then the frozen index is served
and the page reads ``/api/web/comedores/comedores/<pk>/responsable-tarjeta/``.
"""

from pathlib import Path

from django.urls import path
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from core.decorators import permissions_any_required
from comedores.views.comedor import (
    ComedorDatosConvenioPnudUpdateView,
    ResponsableTarjetaComedorUpdateView,
)
from comedores.web_api_convenio import EDIT_PERMISSIONS
from comedores.web_api_tarjeta import TARJETA_PERMISSIONS
from comedores.web_preview_catalogos import (
    BUILD_ASSETS,
    ReactAssetView,
    _frozen_assets,
    _index,
)

PUBLIC_ASSETS = "/convenio-tarjeta/react/assets/"


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ConvenioEntry(ComedorDatosConvenioPnudUpdateView):
    index_bytes = b""

    def get(self, request, *args, **kwargs):
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class TarjetaEntry(ResponsableTarjetaComedorUpdateView):
    index_bytes = b""

    def get(self, request, *args, **kwargs):
        return _index(request, self.index_bytes)


def convenio_tarjeta_preview_patterns(build_directory):
    """Freeze an explicit local ``apps/sisoc`` build for a disposable preview URLconf.

    The caller supplies its own isolated build directory, never a request path.
    """
    original = Path(build_directory)
    root = original.resolve(strict=True)
    index = root / "index.html"
    if original.is_symlink() or not index.is_file() or index.is_symlink():
        raise ValueError("Convenio preview requires a regular fixed index.html")
    index_bytes = (
        index.read_text(encoding="utf-8")
        .replace(BUILD_ASSETS, PUBLIC_ASSETS)
        .encode("utf-8")
    )
    return [
        path(
            "comedores/<int:pk>/convenio-pnud/",
            permissions_any_required(EDIT_PERMISSIONS)(
                ConvenioEntry.as_view(index_bytes=index_bytes)
            ),
        ),
        path(
            "comedores/<int:pk>/responsable-tarjeta/editar",
            permissions_any_required(TARJETA_PERMISSIONS)(
                TarjetaEntry.as_view(index_bytes=index_bytes)
            ),
        ),
        path(
            "convenio-tarjeta/react/<path:asset_path>",
            ReactAssetView.as_view(assets=_frozen_assets(root)),
        ),
    ]
