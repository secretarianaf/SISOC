from django import template

from relevamientos.service import RelevamientoService

register = template.Library()


@register.filter
def estado_unificado(obj):
    """Pendiente / En curso / Pendiente Revisión / Finalizado (#2781)."""
    return RelevamientoService.estado_unificado(obj)


@register.filter
def badge_estado_unificado(obj):
    """Clase CSS del badge del estado unificado de ``obj``."""
    return RelevamientoService.badge_estado_unificado(
        RelevamientoService.estado_unificado(obj)
    )
