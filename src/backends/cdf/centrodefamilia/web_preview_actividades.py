"""Explicit local React preview of the CDF activity screens (CDF-C); never mounted by a production URLconf.

Same contract as ``centrodefamilia.web_preview``: each entry keeps the native URL
and guard (``permissions_any_required`` with ``view_centro``, then the native
view's own dispatch and object rule) and only then answers its GET with the
frozen React ``index.html``. Other methods keep the native behaviour.
"""

from pathlib import Path

from django.shortcuts import get_object_or_404
from django.urls import path
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from centrodefamilia.models import ParticipanteActividad
from centrodefamilia.views.actividad import (
    ActividadCentroCreateView,
    ActividadCentroDetailView,
    ActividadCentroListView,
    ActividadCentroUpdateView,
    ActividadCreateView,
)
from centrodefamilia.views.asistencia import AsistenciaActividadView
from centrodefamilia.views.participante import (
    ParticipanteActividadCreateView,
    ParticipanteActividadDeleteView,
)
from centrodefamilia.web_preview import (
    BUILD_ASSETS,
    PUBLIC_ASSETS,
    ReactAssetView,
    _entry,
    _frozen_assets,
    index_response,
)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ActividadDetailEntry(ActividadCentroDetailView):
    """The native object rule (missing answers 404), then the index."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return index_response(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ParticipanteCreateEntry(ParticipanteActividadCreateView):
    """Search and create entry; the native view only requires login besides the guard."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        return index_response(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ParticipanteDeleteEntry(ParticipanteActividadDeleteView):
    """Baja confirmation entry; a missing participant answers 404 like the native view."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        get_object_or_404(ParticipanteActividad, pk=kwargs["pk"])
        return index_response(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class AsistenciaEntry(AsistenciaActividadView):
    """The native dispatch (missing 404, attendance permission 403), then the index."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        return index_response(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ActividadListEntry(ActividadCentroListView):
    """The native queryset (a malformed ``centro`` filter fails as today), then the index."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.get_queryset()
        return index_response(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ActividadCatalogoEntry(ActividadCreateView):
    """Catalog form entry; POST stays the native form."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        return index_response(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ActividadCentroCreateEntry(ActividadCentroCreateView):
    """The native centre lookup (missing answers 404), then the index."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        return index_response(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ActividadCentroUpdateEntry(ActividadCentroUpdateView):
    """The native object lookup (missing answers 404), then the index."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return index_response(request, self.index_bytes)


def cdf_actividades_preview_patterns(build_directory):
    """Freeze an explicit local ``apps/sisoc`` build for a disposable preview URLconf."""
    original = Path(build_directory)
    root = original.resolve(strict=True)
    index = root / "index.html"
    if original.is_symlink() or not index.is_file() or index.is_symlink():
        raise ValueError("CDF preview requires a regular fixed index.html")
    index_bytes = (
        index.read_text(encoding="utf-8")
        .replace(BUILD_ASSETS, PUBLIC_ASSETS)
        .encode("utf-8")
    )
    actividad = (
        "centrodefamilia/centros/<int:centro_id>/actividades/<int:actividad_id>/"
    )
    return [
        path(
            "centrodefamilia/centros/actividades/<int:pk>/detalle/",
            _entry(ActividadDetailEntry, index_bytes),
        ),
        path(
            "centrodefamilia/centros/<int:centro_id>/actividades/nueva/",
            _entry(ActividadCentroCreateEntry, index_bytes),
        ),
        path(
            "centrodefamilia/centros/actividades/<int:pk>/editar/",
            _entry(ActividadCentroUpdateEntry, index_bytes),
        ),
        path(
            "centrodefamilia/actividades/",
            _entry(ActividadListEntry, index_bytes),
        ),
        path(
            "centrodefamilia/actividades/nueva/",
            _entry(ActividadCatalogoEntry, index_bytes),
        ),
        path(
            "centrodefamilia/centros/actividades/<int:pk>/asistencia/",
            _entry(AsistenciaEntry, index_bytes),
        ),
        path(
            actividad + "participantes/crear/",
            _entry(ParticipanteCreateEntry, index_bytes),
        ),
        path(
            actividad + "participantes/<int:pk>/eliminar/",
            _entry(ParticipanteDeleteEntry, index_bytes),
        ),
        path(
            "centrodefamilia/react/<path:asset_path>",
            ReactAssetView.as_view(assets=_frozen_assets(root)),
        ),
    ]
