"""Invalidación de cache de Comedores.

Antes vivía en ``core.cache_utils`` (kernel). Las claves y helpers siguen allá;
acá solo se conectan las señales de los modelos de este dominio.
"""

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from core.cache_utils import (
    invalidate_cache_keys,
    invalidate_comedor_cache,
    invalidate_dashboard_cache,
    invalidate_territoriales_cache,
    invalidate_territoriales_cache_provincia,
)
from core.soft_delete.signals import post_restore, post_soft_delete


@receiver([post_save, post_delete], sender="comedores.Comedor")
def invalidate_comedor_cache_on_change(sender, instance, **kwargs):
    """Invalida cache cuando se modifica un comedor."""
    invalidate_comedor_cache(instance.id)
    invalidate_dashboard_cache()


@receiver([post_soft_delete, post_restore])
def invalidate_comedor_cache_on_soft_delete(sender, instance, **kwargs):
    """Invalida cache del comedor ante baja lógica o restauración."""
    if instance._meta.label_lower == "comedores.comedor":
        invalidate_comedor_cache(instance.id)
        invalidate_dashboard_cache()


@receiver([post_save, post_delete], sender="comedores.ValorComida")
def invalidate_valor_comida_cache_on_change(sender, **kwargs):
    """Invalida cache cuando cambian valores de comida."""
    invalidate_cache_keys("valores_comida_map")


@receiver([post_save, post_delete], sender="comedores.TerritorialCache")
def invalidate_territorial_cache_on_change(sender, instance, **kwargs):
    """Invalida cache cuando cambian datos de territoriales por provincia."""
    invalidate_territoriales_cache()
    if getattr(instance, "provincia_id", None):
        invalidate_territoriales_cache_provincia(instance.provincia_id)
    else:
        invalidate_territoriales_cache_provincia()
