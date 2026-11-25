"""Explicit local React preview of the Organizaciones screens (O05); never mounted by a production URLconf.

Each entry keeps the native URL, its route decorator and the native view's
lookup: anonymous users and users without one of the route codes get the
native 403, and the list keeps its ``NoCountPaginator`` (no 404). Only then a
GET returns the frozen React ``index.html``, which loads its data from
``/api/web/comedores/organizaciones/``. Assets are served under the backend's
own prefix ``/organizaciones/react/``. The CSV stays the native
``/organizaciones/exportar``.
"""

from pathlib import Path

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.urls import path
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import ensure_csrf_cookie

from core.decorators import permissions_any_required
from comedores.web_preview_catalogos import (
    BUILD_ASSETS,
    ReactAssetView,
    _frozen_assets,
    _index,
)
from gestion_organizaciones.urls import ORGANIZACION_DOCUMENTACION_PERMS
from gestion_organizaciones.views import (
    AvalCreateView,
    AvalDeleteView,
    AvalUpdateView,
    ConvenioProyectoView,
    FirmanteCreateView,
    FirmanteDeleteView,
    FirmanteUpdateView,
    OrganizacionCreateView,
    OrganizacionDeleteView,
    OrganizacionDetailView,
    OrganizacionListView,
    OrganizacionRendicionDetailView,
    OrganizacionUpdateView,
    _filtrar_organizaciones_por_dupla,
)
from organizaciones.models import DocumentacionOrganizacion, Organizacion

PUBLIC_ASSETS = "/organizaciones/react/assets/"


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ListadoEntry(OrganizacionListView):
    index_bytes = b""

    def get(self, request, *args, **kwargs):
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class LegajoEntry(OrganizacionDetailView):
    index_bytes = b""

    def get(self, request, *args, **kwargs):
        # The native lookup: an organization outside the dupla scope is a 404.
        self.get_object()
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CrearEntry(OrganizacionCreateView):
    index_bytes = b""
    # React saves through ``/api/web/comedores/organizaciones/``; no native POST here.
    http_method_names = ["get", "head"]

    def get(self, request, *args, **kwargs):
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class EditarEntry(OrganizacionUpdateView):
    index_bytes = b""
    http_method_names = ["get", "head"]

    def get(self, request, *args, **kwargs):
        self.get_object()
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class EliminarEntry(OrganizacionDeleteView):
    index_bytes = b""
    http_method_names = ["get", "head"]

    def get(self, request, *args, **kwargs):
        self.get_object()
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ConvenioEntry(ConvenioProyectoView):
    """O01: the native lookup and its "sin línea" redirect (with message) come first."""

    index_bytes = b""
    http_method_names = ["get", "head"]

    def get(self, request, *args, **kwargs):
        self.get_proyecto()
        return self._sin_linea() or _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class HistorialEntry(LoginRequiredMixin, View):
    """O02: the native lookups of ``historial_documento_organizacion`` (404 outside the dupla)."""

    index_bytes = b""

    def get(self, request, organizacion_id, documentacion_id):
        get_object_or_404(
            _filtrar_organizaciones_por_dupla(Organizacion.objects.all(), request.user),
            pk=organizacion_id,
        )
        get_object_or_404(DocumentacionOrganizacion, pk=documentacion_id)
        return _index(request, self.index_bytes)


def _entrada_firmante(vista, *, crea):
    """O03: a form/confirmation entry; React saves through the web API (no native POST)."""

    @method_decorator(ensure_csrf_cookie, name="dispatch")
    class Entry(vista):
        index_bytes = b""
        http_method_names = ["get", "head"]

        def get(self, request, *args, **kwargs):
            if not crea:
                self.get_object()
            return _index(request, self.index_bytes)

    Entry.__name__ = f"{vista.__name__}Entry"
    return Entry


@method_decorator(ensure_csrf_cookie, name="dispatch")
class RendicionEntry(OrganizacionRendicionDetailView):
    """O04: the native queryset (visible organization, 404 otherwise)."""

    index_bytes = b""
    http_method_names = ["get", "head"]

    def get(self, request, *args, **kwargs):
        self.get_object()
        return _index(request, self.index_bytes)


def organizaciones_preview_patterns(build_directory):
    """Freeze an explicit local ``apps/sisoc`` build for a disposable preview URLconf.

    The caller supplies its own isolated build directory, never a request path.
    """
    original = Path(build_directory)
    root = original.resolve(strict=True)
    index = root / "index.html"
    if original.is_symlink() or not index.is_file() or index.is_symlink():
        raise ValueError("Organizaciones preview requires a regular fixed index.html")
    index_bytes = (
        index.read_text(encoding="utf-8")
        .replace(BUILD_ASSETS, PUBLIC_ASSETS)
        .encode("utf-8")
    )
    listado = permissions_any_required(ORGANIZACION_DOCUMENTACION_PERMS)(
        ListadoEntry.as_view(index_bytes=index_bytes)
    )
    legajo = permissions_any_required(ORGANIZACION_DOCUMENTACION_PERMS)(
        LegajoEntry.as_view(index_bytes=index_bytes)
    )
    abm = permissions_any_required(["organizaciones.view_organizacion"])
    documentos = permissions_any_required(ORGANIZACION_DOCUMENTACION_PERMS)
    firmantes = [
        ("firmante/crear/<int:organizacion_pk>", FirmanteCreateView, True),
        ("firmante/editar/<int:pk>", FirmanteUpdateView, False),
        ("firmante/eliminar/<int:pk>", FirmanteDeleteView, False),
        ("aval/crear/<int:organizacion_pk>", AvalCreateView, True),
        ("aval/editar/<int:pk>", AvalUpdateView, False),
        ("aval/eliminar/<int:pk>", AvalDeleteView, False),
    ]
    return [
        path(
            "organizaciones/proyectos/<int:proyecto_id>/convenio/",
            abm(ConvenioEntry.as_view(index_bytes=index_bytes)),
        ),
        path(
            "organizaciones/<int:organizacion_id>/documentacion/<int:documentacion_id>/historial/",
            documentos(HistorialEntry.as_view(index_bytes=index_bytes)),
        ),
        path(
            "organizaciones/<int:organizacion_id>/rendiciones/<int:pk>/detalle/",
            documentos(RendicionEntry.as_view(index_bytes=index_bytes)),
        ),
        *[
            path(
                f"organizaciones/{ruta}",
                abm(
                    _entrada_firmante(vista, crea=crea).as_view(index_bytes=index_bytes)
                ),
            )
            for ruta, vista, crea in firmantes
        ],
        path("organizaciones/crear", abm(CrearEntry.as_view(index_bytes=index_bytes))),
        path(
            "organizaciones/editar/<int:pk>",
            abm(EditarEntry.as_view(index_bytes=index_bytes)),
        ),
        path(
            "organizaciones/eliminar/<int:pk>",
            abm(EliminarEntry.as_view(index_bytes=index_bytes)),
        ),
        path("organizaciones/listar", listado),
        path("organizaciones/detalle/<int:pk>", legajo),
        path(
            "organizaciones/react/<path:asset_path>",
            ReactAssetView.as_view(assets=_frozen_assets(root)),
        ),
    ]
