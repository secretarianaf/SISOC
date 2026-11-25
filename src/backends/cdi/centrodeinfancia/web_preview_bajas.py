"""React entries of the CDI soft-delete confirmations: centre and nómina.

Same contract as ``centrodeinfancia.web_preview``: each entry keeps the native
URL, the same ``permissions_any_required`` decorator as ``urls.py`` and the
native view's own dispatch (login, scoped lookup, 404); only then the GET
returns the frozen React ``index.html``. POST keeps the native soft delete.
The frozen assets are served by ``cdi_preview_patterns``.
"""

from django.urls import path
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from centrodeinfancia.views import (
    CentroDeInfanciaDeleteView,
    NominaCentroInfanciaDeleteView,
)
from centrodeinfancia.web_preview import index_response
from centrodeinfancia.web_preview_trabajadores import frozen_index
from core.decorators import permissions_any_required


def _scoped_get(view, request, *args, **kwargs):
    """Resolve the scoped object (404) like the native view, then the index."""
    view.object = view.get_object()
    return index_response(request, view.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CentroEliminarEntry(CentroDeInfanciaDeleteView):
    """Centre soft-delete confirmation; POST stays native."""

    index_bytes = b""
    get = _scoped_get


@method_decorator(ensure_csrf_cookie, name="dispatch")
class NominaEliminarEntry(NominaCentroInfanciaDeleteView):
    """Nómina soft-delete confirmation (scoped to the centre); POST stays native."""

    index_bytes = b""
    get = _scoped_get


def _entry(view_class, permission, index_bytes):
    return permissions_any_required([permission])(
        view_class.as_view(index_bytes=index_bytes)
    )


def cdi_bajas_preview_patterns(build_directory):
    """Delete confirmation entries (no assets, see the module doc)."""
    index_bytes = frozen_index(build_directory)
    return [
        path(
            "centrodeinfancia/eliminar/<int:pk>",
            _entry(
                CentroEliminarEntry,
                "centrodeinfancia.delete_centrodeinfancia",
                index_bytes,
            ),
        ),
        path(
            "centrodeinfancia/<int:pk>/nomina/<int:pk2>/eliminar/",
            _entry(
                NominaEliminarEntry,
                "centrodeinfancia.delete_nominacentroinfancia",
                index_bytes,
            ),
        ),
    ]
