"""Explicit local React preview of the encuestas management screens; never mounted by a production URLconf.

Each entry keeps the native URL, the same ``permissions_any_required`` decorator as
``encuestas/urls.py`` and the native view's own dispatch (login, 404, the redirect of an
approval-pending survey). Only then a plain GET returns the frozen React ``index.html``, which
loads its data from ``/api/web/encuestas/``. Other methods keep the native behaviour. The assets
are served by the ``ciudadanos.web_preview`` entry under ``/ciudadanos/react/`` and must be listed
with it, as the audittrail preview does.
"""

from pathlib import Path

from django.http import HttpResponseRedirect
from django.urls import path
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from ciudadanos.web_preview import BUILD_ASSETS, PUBLIC_ASSETS, _index
from core.decorators import permissions_any_required
from encuestas.views import (
    EncuestaCreateView,
    EncuestaListView,
    EncuestaResultadosView,
    EncuestaRevisionView,
    EncuestaSegmentacionView,
    EncuestaUpdateView,
)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class SegmentacionEntry(EncuestaSegmentacionView):
    """Native login, 404 and pending-survey redirect first, then the frozen React index."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        if isinstance(response, HttpResponseRedirect):
            return response
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ResultadosEntry(EncuestaResultadosView):
    """Native login and 404 first (the context is built), then the frozen React index."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        super().get(request, *args, **kwargs)
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ListaEntry(EncuestaListView):
    """Native login, legacy-link redirect and page check first, then the frozen React index."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        if isinstance(response, HttpResponseRedirect):
            return response
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class RevisionEntry(EncuestaRevisionView):
    """Native login and 404 first, then the frozen React index; POSTs stay native."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        super().get(request, *args, **kwargs)
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CrearEntry(EncuestaCreateView):
    """Native login first, then the frozen React index; the native POST keeps its HTML flow."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        return _index(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class EditarEntry(EncuestaUpdateView):
    """Native login, 404 and pending-survey redirect first, then the frozen React index."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        if isinstance(response, HttpResponseRedirect):
            return response
        return _index(request, self.index_bytes)


def encuestas_preview_patterns(build_directory):
    """Freeze the index of an explicit local ``apps/sisoc`` build for a disposable URLconf."""
    original = Path(build_directory)
    root = original.resolve(strict=True)
    index = root / "index.html"
    if original.is_symlink() or not index.is_file() or index.is_symlink():
        raise ValueError("Encuestas preview requires a regular fixed index.html")
    index_bytes = (
        index.read_text(encoding="utf-8")
        .replace(BUILD_ASSETS, PUBLIC_ASSETS)
        .encode("utf-8")
    )
    return [
        path(
            "encuestas/",
            permissions_any_required(
                ["encuestas.view_encuesta", "encuestas.ver_resultados"]
            )(ListaEntry.as_view(index_bytes=index_bytes)),
        ),
        path(
            "encuestas/crear/",
            permissions_any_required(["encuestas.add_encuesta"])(
                CrearEntry.as_view(index_bytes=index_bytes)
            ),
        ),
        path(
            "encuestas/<int:pk>/editar/",
            permissions_any_required(["encuestas.change_encuesta"])(
                EditarEntry.as_view(index_bytes=index_bytes)
            ),
        ),
        path(
            "encuestas/<int:pk>/revision/",
            permissions_any_required(
                ["encuestas.aprobar_encuesta", "encuestas.change_encuesta"]
            )(RevisionEntry.as_view(index_bytes=index_bytes)),
        ),
        path(
            "encuestas/<int:pk>/segmentacion/",
            permissions_any_required(["encuestas.change_encuesta"])(
                SegmentacionEntry.as_view(index_bytes=index_bytes)
            ),
        ),
        path(
            "encuestas/<int:pk>/resultados/",
            permissions_any_required(["encuestas.ver_resultados"])(
                ResultadosEntry.as_view(index_bytes=index_bytes)
            ),
        ),
    ]
