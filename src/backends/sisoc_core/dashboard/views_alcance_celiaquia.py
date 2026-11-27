"""Consulta de alcance para la sesión propia, no autentica el servicio llamante."""

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.vary import vary_on_cookie
from django.views.generic import View

from dashboard.services.alcance_celiaquia import alcance_celiaquia


@method_decorator(never_cache, name="dispatch")
@method_decorator(vary_on_cookie, name="dispatch")
class AlcanceCeliaquiaView(View):
    http_method_names = ["get", "head"]

    def get(self, request):
        if not request.user.is_authenticated or not request.user.is_active:
            return JsonResponse({"estado": "denegado"}, status=403)
        alcance = alcance_celiaquia(request.user)
        if alcance is None:
            return JsonResponse({"estado": "no_disponible"}, status=503)
        return JsonResponse(alcance)
