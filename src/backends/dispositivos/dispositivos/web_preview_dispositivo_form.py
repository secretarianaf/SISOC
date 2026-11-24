"""Explicit local React preview of the Dispositivos create and edit screens.

Same contract as ``dispositivos.web_preview``: each entry keeps the native URL,
the same ``permissions_any_required`` decorator as ``urls.py`` and the native
view's own dispatch (login, scope 404); only then the GET returns the frozen
React ``index.html``. POST keeps the native behaviour. The frozen assets are
served by ``dispositivos_preview_patterns``; this module only adds the two form
entries, so a preview URLconf lists both.
"""

from pathlib import Path

from django.urls import path
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from core.decorators import permissions_any_required

from .views import DispositivoCreateView, DispositivoUpdateView
from .web_preview import BUILD_ASSETS, PUBLIC_ASSETS, index_response


@method_decorator(ensure_csrf_cookie, name="dispatch")
class DispositivoCrearEntry(DispositivoCreateView):
    """Native guards, then the index; POST stays native."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.object = None
        return index_response(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class DispositivoEditarEntry(DispositivoUpdateView):
    """Native guards and the scoped object (404), then the index; POST stays native."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return index_response(request, self.index_bytes)


def _frozen_index(build_directory):
    original = Path(build_directory)
    root = original.resolve(strict=True)
    index = root / "index.html"
    if original.is_symlink() or not index.is_file() or index.is_symlink():
        raise ValueError("Dispositivos preview requires a regular fixed index.html")
    return (
        index.read_text(encoding="utf-8")
        .replace(BUILD_ASSETS, PUBLIC_ASSETS)
        .encode("utf-8")
    )


def dispositivo_form_preview_patterns(build_directory):
    """Form entries of a disposable preview URLconf (no assets, see the module doc)."""
    index_bytes = _frozen_index(build_directory)
    return [
        path(
            "dispositivos/crear",
            permissions_any_required(["dispositivos.add_dispositivo"])(
                DispositivoCrearEntry.as_view(index_bytes=index_bytes)
            ),
        ),
        path(
            "dispositivos/<int:pk>/editar",
            permissions_any_required(["dispositivos.change_dispositivo"])(
                DispositivoEditarEntry.as_view(index_bytes=index_bytes)
            ),
        ),
    ]
