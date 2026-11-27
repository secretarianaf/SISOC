"""La toolbar de debug no se muestra en los backends por vertical (#2956).

Detrás del proxy del core la toolbar no funciona y quedaba inyectada sin
estilos al final de la página (Inspecciones escolares).
"""

from config.backend_settings import aplicar


def _namespace_core(**extra):
    return {
        "CORE_APPS": [],
        "INSTALLED_APPS": ["django.contrib.auth", "debug_toolbar"],
        "MIDDLEWARE": ["debug_toolbar.middleware.DebugToolbarMiddleware"],
        "TEMPLATES": [{"OPTIONS": {"context_processors": []}}],
        **extra,
    }


def test_backend_con_debug_no_muestra_la_toolbar():
    namespace = _namespace_core(
        DEBUG_TOOLBAR_CONFIG={
            "SHOW_TOOLBAR_CALLBACK": lambda request: True,
            "OTRA_OPCION": 1,
        }
    )

    aplicar(namespace, "inspecciones")

    config = namespace["DEBUG_TOOLBAR_CONFIG"]
    assert config["SHOW_TOOLBAR_CALLBACK"](object()) is False
    assert config["OTRA_OPCION"] == 1
    # App y middleware siguen, para dev_urlpatterns y los checks de la toolbar.
    assert "debug_toolbar" in namespace["INSTALLED_APPS"]
    assert "debug_toolbar.middleware.DebugToolbarMiddleware" in namespace["MIDDLEWARE"]


def test_backend_sin_debug_no_agrega_config_de_toolbar():
    namespace = _namespace_core()

    aplicar(namespace, "inspecciones")

    assert "DEBUG_TOOLBAR_CONFIG" not in namespace
