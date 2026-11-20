"""Explicit local React preview of the template manager queries (AD01.01).

Never mounted by a production URLconf. Each entry keeps the native URL, the
native route decorator (``permissions_any_required``) and the native view's
dispatch (``GestorTemplatesPermissionMixin``): users they reject get the native
403, a missing object or an invalid page the native 404. Only then a GET returns
the frozen React ``index.html``, which loads its data from
``/api/web/comedores/admisiones/plantillas-informe/``. Other methods (the
incident management POST) reach the native view unchanged, and the routes this
module does not list (DOCX preview and every
action) stay the native Django pages. Assets are served like the other Comedores
previews, under ``/comedores/react/``.
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
from admisiones.views.templates_informe_tecnico import (
    TEMPLATE_MANAGE_PERMISSION,
    IncidenciaTemplateInformeTecnicoDetailView,
    IncidenciaTemplateInformeTecnicoListView,
    PlantillaInformeTecnicoCreateView,
    PlantillaInformeTecnicoDetailView,
    PlantillaInformeTecnicoListView,
    PlantillaInformeTecnicoVersionUpdateView,
    VariableTemplateInformeTecnicoListView,
)


def _list_get(self, request, *args, **kwargs):
    self.object_list = self.get_queryset()
    # Same Http404 as the native list for a page that does not exist.
    self.paginate_queryset(self.object_list, self.get_paginate_by(self.object_list))
    return _index(request, self.index_bytes)


def _detail_get(self, request, *args, **kwargs):
    self.object = self.get_object()
    return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class PlantillasListEntry(PlantillaInformeTecnicoListView):
    index_bytes = b""
    get = _list_get


@method_decorator(ensure_csrf_cookie, name="dispatch")
class PlantillaCrearEntry(PlantillaInformeTecnicoCreateView):
    """GET serves the index after the native ``dispatch``; the native POST stays."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class VersionEditarEntry(PlantillaInformeTecnicoVersionUpdateView):
    """GET serves the index for a draft of that template (else the native 404)."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class PlantillaDetailEntry(PlantillaInformeTecnicoDetailView):
    index_bytes = b""
    get = _detail_get


@method_decorator(ensure_csrf_cookie, name="dispatch")
class VariablesListEntry(VariableTemplateInformeTecnicoListView):
    index_bytes = b""
    get = _list_get


@method_decorator(ensure_csrf_cookie, name="dispatch")
class IncidenciasListEntry(IncidenciaTemplateInformeTecnicoListView):
    index_bytes = b""
    get = _list_get


@method_decorator(ensure_csrf_cookie, name="dispatch")
class IncidenciaDetailEntry(IncidenciaTemplateInformeTecnicoDetailView):
    """GET serves the index; the native ``post()`` still manages the incident."""

    index_bytes = b""
    get = _detail_get


def templates_preview_patterns(build_directory):
    """Freeze an explicit local ``apps/sisoc`` build for a disposable preview URLconf.

    The caller supplies its own isolated build directory, never a request path.
    """
    original = Path(build_directory)
    root = original.resolve(strict=True)
    index = root / "index.html"
    if original.is_symlink() or not index.is_file() or index.is_symlink():
        raise ValueError("Template manager preview requires a regular fixed index.html")
    index_bytes = (
        index.read_text(encoding="utf-8")
        .replace(BUILD_ASSETS, PUBLIC_ASSETS)
        .encode("utf-8")
    )

    def entry(vista):
        return permissions_any_required([TEMPLATE_MANAGE_PERMISSION])(
            vista.as_view(index_bytes=index_bytes)
        )

    base = "comedores/configuracion/templates/"
    return [
        path(base, entry(PlantillasListEntry)),
        path(f"{base}crear/", entry(PlantillaCrearEntry)),
        path(f"{base}incidencias/", entry(IncidenciasListEntry)),
        path(f"{base}incidencias/<int:pk>/", entry(IncidenciaDetailEntry)),
        path(f"{base}variables/", entry(VariablesListEntry)),
        path(f"{base}<int:pk>/", entry(PlantillaDetailEntry)),
        path(
            f"{base}<int:plantilla_pk>/versiones/<int:version_pk>/editar/",
            entry(VersionEditarEntry),
        ),
        path(
            "comedores/react/<path:asset_path>",
            ReactAssetView.as_view(assets=_frozen_assets(root)),
        ),
    ]
