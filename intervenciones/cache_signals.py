"""Invalidación de cache de Intervenciones.

Antes vivía en ``core.cache_utils`` (kernel); las claves siguen allá.
"""

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from core.cache_utils import invalidate_intervenciones_cache


@receiver([post_save, post_delete], sender="intervenciones.TipoIntervencion")
def invalidate_tipo_intervencion_cache_on_change(sender, instance, **kwargs):
    """Invalida cache cuando se modifica un tipo de intervención."""
    invalidate_intervenciones_cache()


@receiver([post_save, post_delete], sender="intervenciones.TipoDestinatario")
def invalidate_destinatario_cache_on_change(sender, instance, **kwargs):
    """Invalida cache cuando se modifica un tipo de destinatario."""
    invalidate_intervenciones_cache()
