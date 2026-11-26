"""Botón "Estado" del legajo del CDI (#2945)."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.http import require_POST

from centrodeinfancia.access import (
    get_object_scoped_cdi_or_404,
    puede_cambiar_estado_cdi,
)
from centrodeinfancia.models import CentroDeInfancia
from centrodeinfancia.services_estado_centro import cambiar_estado_centro


@login_required
@require_POST
def cambiar_estado_centro_cdi(request, pk):
    """Guarda el estado elegido en el modal y vuelve al legajo.

    Sin permiso responde 403; un CDI fuera del alcance territorial, 404.
    """
    if not puede_cambiar_estado_cdi(request.user):
        raise PermissionDenied("No tenés permiso para cambiar el estado del CDI.")
    centro = get_object_scoped_cdi_or_404(
        CentroDeInfancia.objects.all(), request.user, pk=pk
    )
    try:
        cambiado = cambiar_estado_centro(
            actor=request.user, centro=centro, estado=request.POST.get("estado", "")
        )
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
    else:
        if cambiado:
            messages.success(
                request,
                f"Estado del CDI actualizado a «{centro.get_estado_display()}».",
            )
    return redirect(reverse("centrodeinfancia_detalle", kwargs={"pk": centro.pk}))
