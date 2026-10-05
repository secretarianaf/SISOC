"""Alcance provincial compartido por las pantallas Django y la API VPSL."""

from django.db.models import Q

from iam.services import user_has_permission_code

VIEW_ALL_ITINERARIOS_PERMISSION = "ver_para_ser_libre.view_all_itinerarios_vpsl"
CREATE_ANY_PROVINCE_PERMISSION = (
    "ver_para_ser_libre.create_itinerarios_any_province_vpsl"
)


def provincia_usuario_provincial(user):
    profile = getattr(user, "profile", None)
    if profile and profile.es_usuario_provincial and profile.provincia_id:
        return profile.provincia
    return None


def puede_ver_todos_los_itinerarios(user):
    return bool(
        getattr(user, "is_superuser", False)
        or user_has_permission_code(user, VIEW_ALL_ITINERARIOS_PERMISSION)
    )


def filtrar_itinerarios_por_usuario(queryset, user):
    if puede_ver_todos_los_itinerarios(user):
        return queryset
    provincia = provincia_usuario_provincial(user)
    if user_has_permission_code(user, CREATE_ANY_PROVINCE_PERMISSION):
        if provincia:
            return queryset.filter(Q(provincia=provincia) | Q(creado_por=user))
        return queryset.filter(creado_por=user)
    if provincia:
        return queryset.filter(provincia=provincia)
    return queryset.none()


def filtrar_jornadas_por_usuario(queryset, user):
    if puede_ver_todos_los_itinerarios(user):
        return queryset
    provincia = provincia_usuario_provincial(user)
    if provincia:
        return queryset.filter(itinerario__provincia=provincia)
    return queryset.none()


def filtrar_casos_laboratorio_por_usuario(queryset, user):
    if puede_ver_todos_los_itinerarios(user):
        return queryset
    provincia = provincia_usuario_provincial(user)
    if provincia:
        return queryset.filter(registro__jornada__itinerario__provincia=provincia)
    return queryset.none()
