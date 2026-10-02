"""Tags del menú lateral que aportan los dominios.

El layout compartido (``templates/includes/sidebar``) lo renderizan el core y
cada backend. Los ítems que dependen de apps del core se registran desde esas
apps; en un proceso que no las instala, el tag devuelve una lista vacía.
"""

from django import template

from core.services.sidebar_items import obtener_tableros

register = template.Library()


@register.simple_tag(takes_context=True)
def tableros_para_sidebar(context):
    """Tableros visibles para el menú (los aporta ``dashboard``)."""
    return obtener_tableros(context)
