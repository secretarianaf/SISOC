from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpResponse, JsonResponse
from django.views import View

from .services import leer_resultado


def health_check(request):
    return HttpResponse("OK", status=200)


class HealthUrlsView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Último resultado de ``python manage.py chequear_urls``, solo superusuarios."""

    def test_func(self):
        return self.request.user.is_superuser

    def get(self, request):
        resultado = leer_resultado()
        if resultado is None:
            return JsonResponse(
                {
                    "error": (
                        "Todavía no hay resultados: correr "
                        "python manage.py chequear_urls."
                    )
                },
                status=404,
            )
        return JsonResponse(resultado, json_dumps_params={"ensure_ascii": False})
