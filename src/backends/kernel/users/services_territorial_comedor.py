"""Alcances territoriales almacenados en identidad, sin consultar Espacios."""

from core.models import Provincia
from users.models import TerritorialComedorProvincia
from users.profile_utils import get_profile_or_none


def is_territorial_comedor_user(user):
    return bool(
        getattr(user, "is_authenticated", False)
        and getattr(get_profile_or_none(user), "es_territorial_comedor", False)
    )


def get_territorial_comedor_provincia_ids(user):
    if not is_territorial_comedor_user(user):
        return []
    return list(
        TerritorialComedorProvincia.objects.filter(profile=get_profile_or_none(user))
        .values_list("provincia_id", flat=True)
        .distinct()
    )


def get_territorial_comedor_provincias(user):
    provincia_ids = get_territorial_comedor_provincia_ids(user)
    return [
        {"id": provincia.id, "nombre": provincia.nombre}
        for provincia in Provincia.objects.filter(id__in=provincia_ids).order_by(
            "nombre"
        )
    ]
