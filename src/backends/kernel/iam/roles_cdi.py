"""Roles de Centro de Infancia que necesita conocer el kernel.

El menú lateral oculta Comunicados a los roles CDI locales sin rol SIMEPI. La
regla depende solo de grupos (datos del kernel), así que vive acá y se aplica
en el core y en cada backend aunque CDI corra aparte.
``centrodeinfancia.access`` y ``centrodeinfancia.sidebar_access`` la reexportan.
"""

from typing import Any

from core.constants import UserGroups

GRUPOS_CDI_LOCALES = frozenset(
    (
        UserGroups.CDI_REFERENTE_CENTRO,
        UserGroups.CDI_TRABAJADOR,
    )
)
GRUPOS_SIMEPI = frozenset(
    (
        UserGroups.SIMEPI_ADMINISTRADOR,
        UserGroups.SIMEPI_ANALISTA_DATOS,
        UserGroups.SIMEPI_EQUIPO_NACIONAL,
        UserGroups.SIMEPI_AUDITORIA,
        UserGroups.SIMEPI_EGP,
    )
)


def es_usuario_solo_cdi_local(user: Any) -> bool:
    """Oculta Comunicados sólo a roles CDI locales sin rol SIMEPI adicional."""
    if not user or not getattr(user, "is_authenticated", False) or user.is_superuser:
        return False
    group_names = set(user.groups.values_list("name", flat=True))
    return bool(group_names & GRUPOS_CDI_LOCALES) and not bool(
        group_names & GRUPOS_SIMEPI
    )
