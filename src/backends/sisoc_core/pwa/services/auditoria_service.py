"""Compatibilidad: persistencia compartida y snapshots propios del dominio."""

import logging

from audittrail.auth import registrar_evento_auth as persistir_evento_auth
from pwa.services.accesos import get_pwa_context


def registrar_evento_auth(**kwargs):
    """Adjunta contexto de Espacios comunitarios sin acoplar el persistidor."""
    user = kwargs.get("user")
    try:
        kwargs["contexto"] = get_pwa_context(user) if user else {}
    except Exception:  # No perder el evento común por un snapshot de negocio.
        logging.getLogger(__name__).exception(
            "Contexto de Espacios no disponible para auditoría"
        )
        kwargs["contexto"] = {}
    return persistir_evento_auth(**kwargs)
