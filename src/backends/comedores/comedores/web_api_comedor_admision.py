"""Web API (G1 v1) of «Comenzar Admisión» from the comedor ficha (CO07.01).

``POST /api/web/comedores/comedores/<pk>/admision/`` runs the native
``ComedorService.crear_admision_desde_comedor`` for the comedor the user's scope
resolves (a comedor outside it is a 404), with the access of the native ficha
route (any of ``view_comedor``, ``view_admision`` or
``view_informacionrelevante``; the service adds no ``add_admision`` check, and
this API does not add one either, see the CO07.01 contract). Only the type is
read: the other POST actions of the native ficha view (``descartar_expediente``,
the legacy territorial redirect) are not reachable here.

The service always answers with a redirect to the ficha and a Django message:
success or the reason it refused (nómina directa, no type, renovación without
incorporación, incorporación already active, four active renovaciones). The API
returns that outcome (201 when an admission was created, 200 otherwise) and keeps
the message queued for the ficha the redirect lands on.
"""

from django.contrib import messages
from django.http import Http404
from django.urls import reverse
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from admisiones.models.admisiones import Admision
from comedores.services.comedor_service import ComedorService
from comedores.views.comedor import ComedorDetailView
from comedores.web_api_comedor_ficha import _native
from comedores.web_api_comedores import MESSAGE_LEVELS, VerComedores
from core.web_gate import WebGatePermission


class ComedorAdmisionWebView(APIView):
    """``POST /api/web/comedores/comedores/<pk>/admision/``."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, VerComedores]
    renderer_classes = [JSONRenderer]
    http_method_names = ["post"]

    def post(self, request, pk):
        django_request = request._request  # pylint: disable=protected-access
        vista = _native(ComedorDetailView, request, pk=pk)
        try:
            comedor = vista.get_object()
        except Http404 as exc:
            raise NotFound() from exc
        antes = Admision.objects.filter(comedor=comedor).count()

        ComedorService.crear_admision_desde_comedor(django_request, comedor)

        # The service answers with a message; read it and leave it queued for the ficha.
        queued = list(messages.get_messages(django_request))
        for item in queued:
            messages.add_message(django_request, item.level, item.message)
        ultimo = queued[-1] if queued else None
        creada = Admision.objects.filter(comedor=comedor).count() > antes
        return Response(
            {
                "created": creada,
                "redirect": reverse("comedor_detalle", kwargs={"pk": comedor.pk}),
                "message": (
                    {
                        "level": MESSAGE_LEVELS.get(ultimo.level, "info"),
                        "text": str(ultimo.message),
                    }
                    if ultimo
                    else None
                ),
            },
            status=status.HTTP_201_CREATED if creada else status.HTTP_200_OK,
        )
