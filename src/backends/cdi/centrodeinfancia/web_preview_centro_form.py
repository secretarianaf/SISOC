"""Explicit local React preview of the CDI centre create and edit screens.

Same contract as ``centrodeinfancia.web_preview``: each entry keeps the native
URL, the same ``permissions_any_required`` decorator as ``urls.py`` and the
native view's own dispatch (login, scope, the CDI-A3 veto on writes); only then
the GET returns the frozen React ``index.html``. Other methods keep the native
behaviour. The frozen assets are served by ``cdi_preview_patterns``; this module
only adds the two centre form entries, so a preview URLconf lists both.
"""

from pathlib import Path

from django.urls import path
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from centrodeinfancia.views import (
    CentroDeInfanciaCreateView,
    CentroDeInfanciaUpdateView,
)
from centrodeinfancia.web_preview import BUILD_ASSETS, PUBLIC_ASSETS, index_response
from core.decorators import permissions_any_required


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CentroCrearEntry(CentroDeInfanciaCreateView):
    """Native guards, then the index; POST stays native."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.object = None
        self.get_context_data()
        return index_response(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CentroEditarEntry(CentroDeInfanciaUpdateView):
    """Native guards and the scoped centre (404), then the index; POST stays native."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return index_response(request, self.index_bytes)


def _frozen_index(build_directory):
    """The fixed ``index.html`` of an isolated local build, assets under the backend prefix."""
    original = Path(build_directory)
    root = original.resolve(strict=True)
    index = root / "index.html"
    if original.is_symlink() or not index.is_file() or index.is_symlink():
        raise ValueError("CDI preview requires a regular fixed index.html")
    return (
        index.read_text(encoding="utf-8")
        .replace(BUILD_ASSETS, PUBLIC_ASSETS)
        .encode("utf-8")
    )


def _entry(view_class, permission, index_bytes):
    return permissions_any_required([permission])(
        view_class.as_view(index_bytes=index_bytes)
    )


def centro_form_preview_patterns(build_directory):
    """Centre form entries of a disposable preview URLconf (no assets, see the module doc)."""
    index_bytes = _frozen_index(build_directory)
    return [
        path(
            "centrodeinfancia/crear",
            _entry(
                CentroCrearEntry, "centrodeinfancia.add_centrodeinfancia", index_bytes
            ),
        ),
        path(
            "centrodeinfancia/editar/<int:pk>",
            _entry(
                CentroEditarEntry,
                "centrodeinfancia.change_centrodeinfancia",
                index_bytes,
            ),
        ),
    ]
