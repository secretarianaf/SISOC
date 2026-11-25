"""Settings comunes a todos los backends por vertical (src/backends/config/backends.json).

Cada ``src/backends/<x>/<x>_runtime/settings.py`` hace::

    from config.settings import *
    from config.backend_settings import aplicar
    aplicar(globals(), "<x>")

y agrega después lo propio del vertical, si lo hubiera.
"""

from config.backends import load_backends_registry


def ocultar_debug_toolbar(_request):
    """La toolbar de debug no se muestra en los backends por vertical.

    Sus páginas llegan por el proxy del core y la toolbar no funciona ahí: los
    pedidos a ``/__debug__/`` los atiende el core, que no tiene los datos de
    este proceso. Con ``DEBUG`` activo quedaba inyectada sin estilos al final de
    la página (#2956).
    """
    return False


def aplicar(namespace: dict, nombre: str) -> None:
    """Ajusta el settings del core para que el proceso sea el backend ``nombre``."""
    spec = load_backends_registry()[nombre]
    core_apps = namespace["CORE_APPS"]
    # Las del settings base menos las del core: se conservan las compartidas,
    # el kernel y las que el base suma según el entorno (debug_toolbar, silk).
    namespace["INSTALLED_APPS"] = [
        app for app in namespace["INSTALLED_APPS"] if app not in core_apps
    ] + list(spec["apps"])
    namespace["ROOT_URLCONF"] = spec["urlconf"]
    # WSGI_APPLICATION se hereda: config.wsgi importa config (que arma el
    # sys.path) antes de cargar este settings desde DJANGO_SETTINGS_MODULE.
    namespace["SISOC_BACKEND"] = nombre
    # El backend no es proxy de nadie.
    namespace["SISOC_BACKENDS"] = {}

    # Encuestas vive en el core. Su middleware ya corre en el core antes de que
    # el proxy reenvíe (src/backends/kernel/core/backend_proxy.py): el bloqueo por encuesta
    # obligatoria sigue aplicando sobre las páginas del backend.
    namespace["MIDDLEWARE"] = [
        m for m in namespace["MIDDLEWARE"] if not m.startswith("encuestas.")
    ]
    # Solo existe con DEBUG (src/backends/config/settings.py). App y middleware
    # se conservan para que dev_urlpatterns y los checks de la toolbar sigan
    # funcionando; solo deja de mostrarse.
    if "DEBUG_TOOLBAR_CONFIG" in namespace:
        namespace["DEBUG_TOOLBAR_CONFIG"] = {
            **namespace["DEBUG_TOOLBAR_CONFIG"],
            "SHOW_TOOLBAR_CALLBACK": ocultar_debug_toolbar,
        }
    plantillas = namespace["TEMPLATES"][0]
    namespace["TEMPLATES"] = [
        {
            **plantillas,
            "OPTIONS": {
                **plantillas["OPTIONS"],
                "context_processors": [
                    cp
                    for cp in plantillas["OPTIONS"]["context_processors"]
                    if not cp.startswith("encuestas.")
                ],
            },
        }
    ]
