"""Enlaces GET anteriores al traslado de la auditoría de sesión al kernel."""

from django.urls import path
from django.views.generic import RedirectView


def _redirect(action):
    # Los permisos los comprueba el admin canónico. Un formulario abierto antes
    # del cambio no puede repetir una mutación por un redirect de POST a GET.
    return RedirectView.as_view(
        pattern_name=f"admin:audittrail_auditoriasesionpwa_{action}",
        permanent=False,
        query_string=True,
        http_method_names=["get", "head", "options"],
    )


urlpatterns = [
    path("", _redirect("changelist")),
    path("add/", _redirect("add")),
    path("<int:object_id>/change/", _redirect("change")),
    path("<int:object_id>/history/", _redirect("history")),
    path("<int:object_id>/delete/", _redirect("delete")),
]
