from django import template

from dashboard.models import Tablero
from dashboard.services.politicas import (
    configuracion_celiaquia,
    configuracion_progresar,
    ids_embeds_nacionales,
)

register = template.Library()


def _colapsar_grupos_individuales(items):
    return [
        (
            item["hijos"][0]
            if item["tipo"] == "grupo" and len(item["hijos"]) == 1
            else item
        )
        for item in items
    ]


@register.simple_tag(takes_context=True)
def tableros_para_sidebar(context):
    """Devuelve los tableros visibles agrupados para el menú lateral.

    Cada elemento de la lista es un dict con ``tipo``:

    - ``single``: enlace directo (``nombre``, ``url``, ``activo``).
    - ``grupo``: submenú colapsable (``nombre``, ``activo`` y ``hijos``,
      lista de dicts ``single``).

    Los tableros sin ``grupo_menu`` (o cuyo grupo tiene un único tablero
    visible) se muestran como enlaces directos, sin el "Ver" intermedio.

    La posición de un grupo queda anclada al primer tablero encontrado de ese
    grupo (menor ``orden`` según el queryset). Los tableros posteriores del
    mismo grupo se agregan a sus ``hijos`` y no mueven la posición del grupo,
    aunque su propio ``orden`` los ubicaría después de otros elementos.
    """
    request = context.get("request")
    if not request:
        return []
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return []

    tableros = list(
        Tablero.objects.filter(activo=True, visible_menu=True).order_by(
            "orden", "nombre"
        )
    )
    configuracion = configuracion_progresar()
    celiaquia = configuracion_celiaquia()
    tableros_nacionales = ids_embeds_nacionales(user, tableros)
    tableros = [
        tablero
        for tablero in tableros
        if tablero.usuario_puede_ver(
            user,
            configuracion=configuracion,
            configuracion_celiaquia_actual=celiaquia,
            tableros_nacionales=tableros_nacionales,
        )
    ]

    current_path = request.get_full_path()

    items = []
    grupos_por_nombre = {}
    for tablero in tableros:
        url = tablero.get_absolute_url()
        hijo = {
            "tipo": "single",
            "nombre": tablero.nombre,
            "url": url,
            "activo": current_path == url,
        }

        grupo_menu = (tablero.grupo_menu or "").strip()
        if not grupo_menu:
            items.append(hijo)
            continue

        grupo = grupos_por_nombre.get(grupo_menu)
        if grupo is None:
            grupo = {
                "tipo": "grupo",
                "nombre": grupo_menu,
                "activo": False,
                "hijos": [],
            }
            grupos_por_nombre[grupo_menu] = grupo
            items.append(grupo)
        grupo["hijos"].append(hijo)
        if hijo["activo"]:
            grupo["activo"] = True

    # Un grupo con un solo tablero visible se colapsa a enlace directo.
    return _colapsar_grupos_individuales(items)
