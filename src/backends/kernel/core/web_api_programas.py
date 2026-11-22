"""Programas para React (T05, G1 v1): ``/api/web/core/programas/``.

Corre las vistas nativas ``Programa*View`` con su regla de acceso actual: solo sesión
autenticada (decisión ``docs/registro/decisiones/2026-11-10-2785-t05-programas-acceso-actual.md``).
El ``GET`` proyecta el contexto de la plantilla; el ``POST`` corre ``form_valid`` /
``form_invalid`` / ``post`` nativos: el mensaje en cola, el redirect y la persistencia son
los de la vista, y un formulario rechazado responde ``400`` sin escribir.
"""

from django.urls import reverse
from rest_framework.response import Response

from core.pagination import build_compact_page_range
from core.views import (
    ProgramaCreateView,
    ProgramaDeleteView,
    ProgramaDetailView,
    ProgramaListView,
    ProgramaUpdateView,
)
from core.web_api_core_base import (
    CoreWebView,
    native_object,
    native_view,
    pending_messages,
    project_form,
)


def _urls(programa):
    return {
        "detail": reverse("programa_detalle", kwargs={"pk": programa.pk}),
        "edit": reverse("programa_editar", kwargs={"pk": programa.pk}),
        "delete": reverse("programa_eliminar", kwargs={"pk": programa.pk}),
    }


def _organismo(programa):
    organismo = programa.organismo
    return str(organismo) if organismo else None


class ProgramaListWebView(CoreWebView):
    """``ProgramaListView``: 25 por página, ordenado por nombre."""

    def get(self, request):
        vista = native_view(ProgramaListView, request)
        vista.object_list = vista.get_queryset()
        # ``get_context_data`` pagina y levanta el 404 nativo de una página inexistente.
        contexto = vista.get_context_data()
        page = contexto["page_obj"]
        return Response(
            {
                "items": [
                    {
                        "id": programa.pk,
                        "nombre": programa.nombre,
                        "organismo": _organismo(programa),
                        "estado": bool(programa.estado),
                        "urls": _urls(programa),
                    }
                    for programa in contexto["programas"]
                ],
                "urls": {"create": reverse("programa_crear")},
                "pagination": {
                    "paginated": bool(contexto["is_paginated"]),
                    "number": page.number,
                    "previous": (
                        page.previous_page_number() if page.has_previous() else None
                    ),
                    "next": page.next_page_number() if page.has_next() else None,
                    "range": list(build_compact_page_range(page)),
                    "count": page.paginator.count,
                },
                "messages": pending_messages(request),
            }
        )


class ProgramaDetailWebView(CoreWebView):
    """``ProgramaDetailView``."""

    def get(self, request, pk):
        vista = native_view(ProgramaDetailView, request, pk=pk)
        programa = native_object(vista)
        return Response(
            {
                "id": programa.pk,
                "nombre": programa.nombre,
                "estado": bool(programa.estado),
                "organismo": _organismo(programa),
                "observaciones": programa.observaciones,
                "descripcion": programa.descripcion,
                "urls": {"list": reverse("programa_listar"), **_urls(programa)},
                "messages": pending_messages(request),
            }
        )


def _formulario(vista, form, request, status=200):
    programa = vista.object
    existe = programa is not None and programa.pk is not None
    return Response(
        {
            "mode": "edit" if existe else "create",
            "fields": project_form(form),
            "urls": {"list": reverse("programa_listar")},
            "messages": pending_messages(request),
        },
        status=status,
    )


def _guardar(vista, request):
    form = vista.get_form()
    if not form.is_valid():
        return _formulario(vista, form, request, status=400)
    respuesta = vista.form_valid(form)
    return Response({"ok": True, "redirect": respuesta["Location"]})


class ProgramaCreateWebView(CoreWebView):
    """``ProgramaCreateView``."""

    def get(self, request):
        vista = native_view(ProgramaCreateView, request)
        vista.object = None
        return _formulario(vista, vista.get_form(), request)

    def post(self, request):
        vista = native_view(ProgramaCreateView, request)
        vista.object = None
        return _guardar(vista, request)


class ProgramaUpdateWebView(CoreWebView):
    """``ProgramaUpdateView``."""

    def get(self, request, pk):
        vista = native_view(ProgramaUpdateView, request, pk=pk)
        vista.object = native_object(vista)
        return _formulario(vista, vista.get_form(), request)

    def post(self, request, pk):
        vista = native_view(ProgramaUpdateView, request, pk=pk)
        vista.object = native_object(vista)
        return _guardar(vista, request)


class ProgramaDeleteWebView(CoreWebView):
    """``ProgramaDeleteView``: confirmación y baja."""

    def get(self, request, pk):
        vista = native_view(ProgramaDeleteView, request, pk=pk)
        programa = native_object(vista)
        return Response(
            {
                "id": programa.pk,
                "nombre": programa.nombre,
                "urls": {"detail": reverse("programa_detalle", kwargs={"pk": pk})},
                "messages": pending_messages(request),
            }
        )

    def post(self, request, pk):
        vista = native_view(ProgramaDeleteView, request, pk=pk)
        native_object(vista)
        # pylint: disable-next=protected-access
        respuesta = vista.post(request._request, pk=pk)
        return Response({"ok": True, "redirect": respuesta["Location"]})
