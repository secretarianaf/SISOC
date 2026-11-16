"""Explicit local React preview of the VAT centros list and institution screens (V06.01); never mounted by a production URLconf.

Each entry keeps the native URL and the native guard (the same ``permissions_any_required`` decorator as
``VAT/urls.py``) and the native view's own dispatch (login redirect, queryset 404, invalid ``page`` 404). Only
then the GET returns the frozen React ``index.html``, which loads its data from ``/api/web/vat/``. POSTs go to
the web API.
"""

from pathlib import Path

from django.urls import path
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from VAT.views.institucion import (
    InstitucionContactoCreateView,
    InstitucionContactoDeleteView,
    InstitucionContactoDetailView,
    InstitucionContactoListView,
    InstitucionContactoUpdateView,
    InstitucionUbicacionCreateView,
    InstitucionUbicacionDeleteView,
    InstitucionUbicacionDetailView,
    InstitucionUbicacionListView,
    InstitucionUbicacionUpdateView,
    InstitucionIdentificadorHistUpdateView,
    InstitucionIdentificadorHistListView,
    InstitucionIdentificadorHistDetailView,
    InstitucionIdentificadorHistDeleteView,
    InstitucionIdentificadorHistCreateView,
)
from VAT.views.modalidad_institucional import (
    ModalidadInstitucionalCreateView,
    ModalidadInstitucionalDeleteView,
    ModalidadInstitucionalDetailView,
    ModalidadInstitucionalListView,
    ModalidadInstitucionalUpdateView,
)
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


def _new_get(view, request, *args, **kwargs):
    """The create form has no object: the React index is served as is."""
    view.object = None
    return index_response(request, view.index_bytes)


_GET = {"list": _list_get, "object": _detail_get, "new": _new_get}

# (route, native view, permission, kind of native GET)
ROUTES = (
    (
        "vat/modalidades-institucionales/",
        ModalidadInstitucionalListView,
        "VAT.view_modalidadinstitucional",
        "list",
    ),
    (
        "vat/modalidades-institucionales/nueva/",
        ModalidadInstitucionalCreateView,
        "VAT.add_modalidadinstitucional",
        "new",
    ),
    (
        "vat/modalidades-institucionales/<int:pk>/",
        ModalidadInstitucionalDetailView,
        "VAT.view_modalidadinstitucional",
        "object",
    ),
    (
        "vat/modalidades-institucionales/<int:pk>/editar/",
        ModalidadInstitucionalUpdateView,
        "VAT.change_modalidadinstitucional",
        "object",
    ),
    (
        "vat/modalidades-institucionales/<int:pk>/eliminar/",
        ModalidadInstitucionalDeleteView,
        "VAT.delete_modalidadinstitucional",
        "object",
    ),
    (
        "vat/institucion/contactos/",
        InstitucionContactoListView,
        "VAT.view_institucioncontacto",
        "list",
    ),
    (
        "vat/institucion/contactos/nuevo/",
        InstitucionContactoCreateView,
        "VAT.add_institucioncontacto",
        "new",
    ),
    (
        "vat/institucion/contactos/<int:pk>/",
        InstitucionContactoDetailView,
        "VAT.view_institucioncontacto",
        "object",
    ),
    (
        "vat/institucion/contactos/<int:pk>/editar/",
        InstitucionContactoUpdateView,
        "VAT.change_institucioncontacto",
        "object",
    ),
    (
        "vat/institucion/contactos/<int:pk>/eliminar/",
        InstitucionContactoDeleteView,
        "VAT.delete_institucioncontacto",
        "object",
    ),
    (
        "vat/institucion/identificadores/",
        InstitucionIdentificadorHistListView,
        "VAT.view_institucionidentificadorhist",
        "list",
    ),
    (
        "vat/institucion/identificadores/nuevo/",
        InstitucionIdentificadorHistCreateView,
        "VAT.add_institucionidentificadorhist",
        "new",
    ),
    (
        "vat/institucion/identificadores/<int:pk>/",
        InstitucionIdentificadorHistDetailView,
        "VAT.view_institucionidentificadorhist",
        "object",
    ),
    (
        "vat/institucion/identificadores/<int:pk>/editar/",
        InstitucionIdentificadorHistUpdateView,
        "VAT.change_institucionidentificadorhist",
        "object",
    ),
    (
        "vat/institucion/identificadores/<int:pk>/eliminar/",
        InstitucionIdentificadorHistDeleteView,
        "VAT.delete_institucionidentificadorhist",
        "object",
    ),
    (
        "vat/institucion/ubicaciones/",
        InstitucionUbicacionListView,
        "VAT.view_institucionubicacion",
        "list",
    ),
    (
        "vat/institucion/ubicaciones/nuevo/",
        InstitucionUbicacionCreateView,
        "VAT.add_institucionubicacion",
        "new",
    ),
    (
        "vat/institucion/ubicaciones/<int:pk>/",
        InstitucionUbicacionDetailView,
        "VAT.view_institucionubicacion",
        "object",
    ),
    (
        "vat/institucion/ubicaciones/<int:pk>/editar/",
        InstitucionUbicacionUpdateView,
        "VAT.change_institucionubicacion",
        "object",
    ),
    (
        "vat/institucion/ubicaciones/<int:pk>/eliminar/",
        InstitucionUbicacionDeleteView,
        "VAT.delete_institucionubicacion",
        "object",
    ),
)


def _entry_class(view, kind):
    entry = type(
        f"{view.__name__}Entry",
        (view,),
        {"index_bytes": b"", "get": _GET[kind]},
    )
    return method_decorator(ensure_csrf_cookie, name="dispatch")(entry)


def centros_preview_patterns(build_directory):
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
    return [
        path(route, _entry(_entry_class(view, kind), permission, index_bytes))
        for route, view, permission, kind in ROUTES
    ] + [
        path(
            "vat/react/<path:asset_path>",
            ReactAssetView.as_view(assets=_frozen_assets(root)),
        )
    ]
