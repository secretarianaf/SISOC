from django.apps import AppConfig


class CatalogoIntervencionesConfig(AppConfig):
    """Catálogos de intervenciones compartidos por Comedores y Centro de Infancia."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "catalogo_intervenciones"

    def ready(self):
        import catalogo_intervenciones.cache_signals  # noqa: F401  pylint: disable=import-outside-toplevel,unused-import
        from catalogo_intervenciones.fixture_post_load import (  # pylint: disable=import-outside-toplevel
            registrar_fixture_post_load_handler,
        )

        registrar_fixture_post_load_handler()
