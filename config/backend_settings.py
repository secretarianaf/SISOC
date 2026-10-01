"""Settings comunes a todos los backends por vertical (config/backends.json).

Cada ``backends/<x>/<x>_runtime/settings.py`` hace::

    from config.settings import *
    from config.backend_settings import aplicar
    aplicar(globals(), "<x>")

y agrega después lo propio del vertical, si lo hubiera.
"""

from config.backends import load_backends_registry


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
    # el proxy reenvíe (kernel/core/backend_proxy.py): el bloqueo por encuesta
    # obligatoria sigue aplicando sobre las páginas del backend.
    namespace["MIDDLEWARE"] = [
        m for m in namespace["MIDDLEWARE"] if not m.startswith("encuestas.")
    ]
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
