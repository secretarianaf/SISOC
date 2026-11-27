"""Rol explícito compartido por los servicios de Datos."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db.models import Q


def puede_administrar_tableros(usuario):
    """Autoriza a superusuarios activos y al rol explícito del equipo de Datos."""
    if not getattr(usuario, "is_authenticated", False) or not usuario.pk:
        return False
    if (
        get_user_model()
        .objects.filter(pk=usuario.pk, is_active=True, is_superuser=True)
        .exists()
    ):
        return True
    roles = Permission.objects.filter(
        Q(user__pk=usuario.pk, user__is_active=True)
        | Q(group__user__pk=usuario.pk, group__user__is_active=True),
        content_type__app_label="auth",
        content_type__model="group",
        name="Equipo de Datos",
        codename="role_equipo_de_datos",
    )
    identifiers = roles.values_list(
        "content_type__app_label", "content_type__model", "name", "codename"
    )
    expected = ("auth", "group", "Equipo de Datos", "role_equipo_de_datos")
    return any(item == expected for item in identifiers)
