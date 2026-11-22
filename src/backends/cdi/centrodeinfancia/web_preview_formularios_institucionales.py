"""Explicit local React preview of the CDI institutional form screens (CDI03).

Same contract as ``centrodeinfancia.web_preview_trabajadores``: each entry keeps
the native URL, the same ``permissions_any_required`` decorator as ``urls.py``
and the native view's own dispatch (login, scope); only then the GET returns the
frozen React ``index.html``. Other methods keep the native behaviour. The frozen
assets are served by ``cdi_preview_patterns``.
"""

from django.urls import path
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from centrodeinfancia.views_formulario_cdi import (
    FormularioCDICreateView,
    FormularioCDIDetailView,
    FormularioCDIListView,
    FormularioCDIUpdateView,
)
from centrodeinfancia.web_preview import index_response
from centrodeinfancia.web_preview_trabajadores import _entry, frozen_index


@method_decorator(ensure_csrf_cookie, name="dispatch")
class FormularioListaEntry(FormularioCDIListView):
    """Native guards, scoped centre and page check (both 404), then the index."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        self.get_context_data()
        return index_response(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class FormularioDetalleEntry(FormularioCDIDetailView):
    """Native guards and the scoped form (404), then the index."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return index_response(request, self.index_bytes)


class _FormEntryMixin:
    """Scope checks of the native ``get`` without building the form or its formsets."""

    index_bytes = b""

    def get(self, request, *args, **kwargs):
        self.get_centro()
        self.get_form_instance()
        return index_response(request, self.index_bytes)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class FormularioCrearEntry(_FormEntryMixin, FormularioCDICreateView):
    """Native guards and the scoped centre (404), then the index; POST stays native."""


@method_decorator(ensure_csrf_cookie, name="dispatch")
class FormularioEditarEntry(_FormEntryMixin, FormularioCDIUpdateView):
    """Native guards and the scoped form (404), then the index: the fixed rows are not created."""


def cdi_formularios_preview_patterns(build_directory):
    """Form entries of a disposable preview URLconf (no assets, see the module doc)."""
    index_bytes = frozen_index(build_directory)
    return [
        path(
            "centrodeinfancia/<int:pk>/formularios/",
            _entry(
                FormularioListaEntry,
                "centrodeinfancia.view_formulariocdi",
                index_bytes,
            ),
        ),
        path(
            "centrodeinfancia/<int:pk>/formularios/<int:form_pk>/",
            _entry(
                FormularioDetalleEntry,
                "centrodeinfancia.view_formulariocdi",
                index_bytes,
            ),
        ),
        path(
            "centrodeinfancia/<int:pk>/formularios/crear/",
            _entry(
                FormularioCrearEntry, "centrodeinfancia.add_formulariocdi", index_bytes
            ),
        ),
        path(
            "centrodeinfancia/<int:pk>/formularios/<int:form_pk>/editar/",
            _entry(
                FormularioEditarEntry,
                "centrodeinfancia.change_formulariocdi",
                index_bytes,
            ),
        ),
    ]
