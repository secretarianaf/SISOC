"""Base compartida de las vistas web de VAT que proyectan una vista nativa a JSON.

Cada endpoint corre la vista nativa (``setup`` + ``get_queryset`` /
``get_context_data``) y solo proyecta su contexto. La regla de acceso es la del
decorador ``permissions_any_required`` de ``VAT.urls`` (no la lleva la vista).
Los valores se renderizan con el motor de plantillas de Django para que el
texto coincida con el HTML nativo (``d/m/Y``, coma decimal, hora local).
"""

from html import unescape

from django.contrib import messages
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from django.template import Context, Template
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from core.decorators import permissions_any_required
from core.pagination import build_compact_page_range
from core.web_gate import WebGatePermission

_NIVELES = {
    messages.ERROR: "error",
    messages.WARNING: "warning",
    messages.SUCCESS: "success",
}
_FILTRO_SIN_PAGINA = Template(
    "{% for key, value in request.GET.items %}{% if key != 'page' and "
    "key != 'busqueda' %}{{ key }}={{ value|urlencode }}&{% endif %}{% endfor %}"
)


class VatSessionAuthentication(SessionAuthentication):
    """Sesión/CSRF de Django con 401 explícito si no hay sesión."""

    def authenticate_header(self, request):
        return "Session"


def regla_nativa(codigos):
    """Permiso DRF que aplica el decorador nativo de la ruta, sin cambios."""
    decorada = permissions_any_required(codigos)(lambda request: True)

    class _Regla(BasePermission):
        def has_permission(self, request, view):
            try:
                return decorada(request._request)  # pylint: disable=protected-access
            except DjangoPermissionDenied:
                return False

    return _Regla


def texto(plantilla, **contexto):
    """Valor tal como lo imprime la plantilla nativa (sin escapado HTML)."""
    return unescape(Template(plantilla).render(Context(contexto)))


def mensajes_pendientes(request):
    """Consume los mensajes en cola como lo haría la página nativa."""
    return [
        {"message": str(m), "level": _NIVELES.get(m.level, "info")}
        for m in messages.get_messages(request)
    ]


def pagina(context, request):
    """``page_obj`` e ``is_paginated`` del contexto de un ``ListView`` nativo."""
    page = context["page_obj"]
    return {
        "is_paginated": bool(context["is_paginated"]),
        "number": page.number,
        "num_pages": page.paginator.num_pages,
        "count": page.paginator.count,
        "previous": page.previous_page_number() if page.has_previous() else None,
        "next": page.next_page_number() if page.has_next() else None,
        "range": [
            "…" if numero in ("...", "…") else numero
            for numero in build_compact_page_range(page)
        ],
        "query_without_page": unescape(
            _FILTRO_SIN_PAGINA.render(Context({"request": request}))
        ),
    }


class VatNativeReadView(APIView):
    """GET que ejecuta una vista nativa de VAT; el alcance es el de su ruta."""

    authentication_classes = [VatSessionAuthentication]
    renderer_classes = [JSONRenderer]
    http_method_names = ["get", "head"]
    schema = None
    native_class = None
    codigos = ()

    permission_classes = [WebGatePermission, IsAuthenticated]

    def get_permissions(self):
        return [*super().get_permissions(), regla_nativa(self.codigos)()]

    def native(self, **kwargs):
        vista = self.native_class()  # pylint: disable=not-callable
        vista.setup(self.request._request, **kwargs)  # pylint: disable=protected-access
        return vista

    def lista(self, extra):
        """Contexto de la lista nativa, con su 404 de página inválida."""
        vista = self.native()
        vista.object_list = vista.get_queryset()
        try:
            context = vista.get_context_data()
        except Http404 as exc:
            raise NotFound("Página no válida.") from exc
        django_request = self.request._request  # pylint: disable=protected-access
        return Response(
            {
                **extra(context, django_request),
                "page": pagina(context, django_request),
                "messages": mensajes_pendientes(django_request),
            }
        )

    def detalle(self, pk):
        """``(vista, contexto)`` del detalle nativo con su 404."""
        vista = self.native(pk=pk)
        try:
            vista.object = vista.get_object()
        except Http404 as exc:
            raise NotFound() from exc
        return vista, vista.get_context_data(object=vista.object)
