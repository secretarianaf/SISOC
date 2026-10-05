"""Regla de navegacion exclusiva del dominio VAT.

La regla vive en el kernel (``iam.roles_vat``) para que el menú del core y de
cualquier backend la aplique aunque VAT corra aparte; el kernel la registra.
"""

from core.services.sidebar_access import registrar_predicado_sidebar
from iam.roles_vat import es_usuario_solo_vat


def registrar_acceso_sidebar() -> None:
    registrar_predicado_sidebar("vat", es_usuario_solo_vat)
