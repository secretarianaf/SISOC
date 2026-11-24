"""Explicit local React preview of the VAT catalog screens (V07.01 and V07.02); never mounted by a production URLconf.

Each entry keeps the native URL and the native guard (the same ``permissions_any_required`` decorator as
``VAT/urls.py``) and the native view's own dispatch (login redirect, queryset 404, invalid ``page`` 404). Only then the
GET returns the frozen React ``index.html``, which loads its data from ``/api/web/vat/``. POSTs go to the web API.
"""

from pathlib import Path

from django.urls import path
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from VAT.views import catalogo
from VAT.web_preview_vat import (
    BUILD_ASSETS,
    PUBLIC_ASSETS,
    ReactAssetView,
    _detail_get,
    _entry,
    _frozen_assets,
    _list_get,
    index_response,
)


def _form_get(view, request, *args, **kwargs):
    """Create forms have no object; update forms keep the native queryset 404."""
    view.object = view.get_object() if view.kwargs.get("pk") else None
    return index_response(request, view.index_bytes)


_CATALOGOS = (
    ("sectores", "nuevo", "sector", "Sector"),
    ("subsectores", "nuevo", "subsector", "Subsector"),
    ("modalidades-cursado", "nueva", "modalidadcursada", "ModalidadCursada"),
    ("titulos-referencia", "nuevo", "tituloreferencia", "TituloReferencia"),
)
_ACCIONES = (
    ("", "List", "view", _list_get),
    ("<int:pk>/", "Detail", "view", _detail_get),
    ("{nuevo}/", "Create", "add", _form_get),
    ("<int:pk>/editar/", "Update", "change", _form_get),
    ("<int:pk>/eliminar/", "Delete", "delete", _detail_get),
)


def _entrada(native, getter):
    return method_decorator(ensure_csrf_cookie, name="dispatch")(
        type(f"{native.__name__}Entry", (native,), {"index_bytes": b"", "get": getter})
    )


def catalogos_preview_patterns(build_directory):
    """Freeze an explicit local ``apps/sisoc`` build for a disposable preview URLconf."""
    original = Path(build_directory)
    root = original.resolve(strict=True)
    index = root / "index.html"
    if original.is_symlink() or not index.is_file() or index.is_symlink():
        raise ValueError("VAT preview requires a regular fixed index.html")
    index_bytes = (
        index.read_text(encoding="utf-8")
        .replace(BUILD_ASSETS, PUBLIC_ASSETS)
        .encode("utf-8")
    )
    patrones = []
    for slug, nuevo, modelo, clase in _CATALOGOS:
        for segmento, vista, accion, getter in _ACCIONES:
            native = getattr(catalogo, f"{clase}{vista}View")
            patrones.append(
                path(
                    f"vat/catalogos/{slug}/{segmento.format(nuevo=nuevo)}",
                    _entry(
                        _entrada(native, getter),
                        f"VAT.{accion}_{modelo}",
                        index_bytes,
                    ),
                )
            )
    patrones.append(
        path(
            "vat/react/<path:asset_path>",
            ReactAssetView.as_view(assets=_frozen_assets(root)),
        )
    )
    return patrones
