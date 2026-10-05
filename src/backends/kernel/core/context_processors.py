from django.core.cache import cache


def _build_footer_version_label(current_version: str) -> str:
    if not current_version:
        return "Versiones"

    parts = str(current_version).split(".")
    if len(parts) != 3:
        return "Versiones"

    day, month, year = parts
    try:
        return f"v{int(day):02d}.{int(month):02d}.{int(year[-2:]):02d}"
    except ValueError:
        return "Versiones"


def footer_version(request):
    del request

    cache_key = "footer_version_label"
    cached_label = cache.get(cache_key)
    if cached_label is not None:
        return {"footer_version_label": cached_label}

    from core.views import (
        get_current_version,
    )  # pylint: disable=import-outside-toplevel

    label = _build_footer_version_label(get_current_version())
    cache.set(cache_key, label, 300)
    return {"footer_version_label": label}


def _es_pantalla_transitoria(request) -> bool:
    """Indica si la pantalla es un paso de un flujo y no un destino.

    Altas, ediciones y confirmaciones de borrado no se apilan en el historial
    del boton "Volver": despues de un POST-redirect-GET quedarian como "pantalla
    anterior" y el boton llevaria al formulario vacio, o al confirm_delete de un
    objeto que ya no existe (404). Ver src/backends/kernel/static/custom/js/volver.js.

    Se deduce de la clase de la vista en lugar de pedirle a cada template que se
    marque: son ~200 formularios y uno sin marcar es un bug silencioso.
    """

    resolver_match = getattr(request, "resolver_match", None)
    if resolver_match is None:
        return False

    # `resolver_match` puede ser un doble de test sin `func`: el boton nunca
    # deberia hacer fallar un render.
    vista = getattr(getattr(resolver_match, "func", None), "view_class", None)
    if vista is None:
        # Vista basada en funcion: no hay forma de deducirlo, se asume destino.
        return False

    # Import local: este modulo lo carga settings y no conviene arrastrar las
    # vistas genericas de Django al arranque.
    from django.views.generic.edit import DeletionMixin, FormMixin

    return issubclass(vista, (FormMixin, DeletionMixin))


def boton_volver(request):
    """Defaults del boton "Volver" unificado (issue #2460).

    El componente se renderiza desde ``includes/main.html`` en todas las
    pantallas, asi que sus variables tienen que existir siempre: sin esto cada
    render loguea "Exception while resolving variable". Las vistas que quieran
    otro comportamiento pisan estos valores desde su propio contexto.
    """

    return {
        "ocultar_volver": False,
        "volver_url": "",
        "volver_texto": "Volver",
        "volver_transitoria": _es_pantalla_transitoria(request),
    }
