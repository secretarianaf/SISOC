"""Explicit local React preview of the PAS crossings; never mounted by a production URLconf.

``pas/cruces`` keeps its native URL and ``permissions_any_required`` rule: users
the decorator rejects (anonymous included) get the native 403 and only then a
GET returns the frozen ``apps/sisoc`` ``index.html``, which loads its data from
``/api/web/pas/cruces/``. The three native POST routes (export, import and
RENAPER update) stay reachable and unchanged.
"""

from django.urls import path
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from core.decorators import permissions_any_required
from pas.ddjj_preview import _index_response
from pas.views import PasCrucesView
from pas.web_preview_backoffice import backoffice_preview_patterns


@method_decorator(ensure_csrf_cookie, name="dispatch")
class PasCrucesEntry(PasCrucesView):
    index_bytes = b""

    def get(self, request, *args, **kwargs):
        return _index_response(request, self.index_bytes)


def cruces_preview_patterns(build_directory):
    """Crossings page plus the back-office entries and frozen assets of the same build."""
    base = backoffice_preview_patterns(build_directory)
    index_bytes = base[0].callback.view_initkwargs["index_bytes"]
    return [
        path(
            "pas/cruces",
            permissions_any_required(["pas.view_paspersona"])(
                PasCrucesEntry.as_view(index_bytes=index_bytes)
            ),
        ),
        *base,
    ]
