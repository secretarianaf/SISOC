"""Explicit local React preview of the PAS reports; never mounted by a production URLconf.

Each entry keeps the native URL, its ``permissions_all_required`` rule and the
native lookup (an unknown report is the native 404). Only then a GET returns
the frozen ``apps/sisoc`` ``index.html``, which loads its data from
``/api/web/pas/informes/``. Other methods, the preview POST and the CSV
download stay native.
"""

from django.urls import path
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from core.decorators import permissions_all_required
from pas.ddjj_preview import _index_response
from pas.views import (
    PasInformeDetailView,
    PasInformeGenerateView,
    PasInformeListView,
)
from pas.web_api_informes import GENERATE_CODES, READ_CODES
from pas.web_preview_backoffice import backoffice_preview_patterns


@method_decorator(ensure_csrf_cookie, name="dispatch")
class PasInformeListEntry(PasInformeListView):
    index_bytes = b""

    def get(self, request, *args, **kwargs):
        return _index_response(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class PasInformeGenerateEntry(PasInformeGenerateView):
    """The GET of the request form; the native POST (CSV download) is not replaced."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        return _index_response(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class PasInformeDetailEntry(PasInformeDetailView):
    """Native lookup first: an unknown ``pk`` is the native 404."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return _index_response(request, self.index_bytes)


def informes_preview_patterns(build_directory):
    """Report pages plus the back-office entries and frozen assets of the same build."""
    base = backoffice_preview_patterns(build_directory)
    index_bytes = base[0].callback.view_initkwargs["index_bytes"]

    def entry(vista, codes=tuple(READ_CODES)):
        return permissions_all_required(list(codes))(
            vista.as_view(index_bytes=index_bytes)
        )

    return [
        path("pas/informes", entry(PasInformeListEntry)),
        path("pas/informes/generar", entry(PasInformeGenerateEntry, GENERATE_CODES)),
        path("pas/informes/<int:pk>", entry(PasInformeDetailEntry)),
        *base,
    ]
