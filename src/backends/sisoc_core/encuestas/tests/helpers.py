"""Preparación de encuestas publicadas para pruebas ajenas a la aprobación."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission

from encuestas.services import publicar, solicitar_publicacion


def publicar_para_test(encuesta, *, usuario):
    """Recorre el circuito con un revisor sin elevar permisos del actor del test."""
    revisor, _ = get_user_model().objects.get_or_create(
        username=f"revisor-fixtures-{usuario.pk}"
    )
    revisor.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="encuestas",
            codename__in=["change_encuesta", "aprobar_encuesta"],
        )
    )
    solicitar_publicacion(encuesta, usuario=revisor)
    return publicar(encuesta, usuario=revisor)
