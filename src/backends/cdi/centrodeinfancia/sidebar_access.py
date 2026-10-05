"""Reglas de visibilidad de navegación propias de CDI.

La regla vive en el kernel (``iam.roles_cdi``) para que el menú del core y de
cualquier backend la aplique aunque CDI corra aparte; el kernel la registra.
"""

from core.services.sidebar_access import registrar_predicado_sidebar

# Reexportados para los consumidores de CDI.
from iam.roles_cdi import (  # noqa: F401  pylint: disable=unused-import
    GRUPOS_SIMEPI,
    es_usuario_solo_cdi_local,
)


def registrar_acceso_sidebar() -> None:
    registrar_predicado_sidebar("cdi_local", es_usuario_solo_cdi_local)
