from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        """Importa las señales de cache cuando la app está lista."""
        import core.cache_utils  # noqa: F401, pylint: disable=import-outside-toplevel,unused-import
        from core.services.sidebar_access import (  # pylint: disable=import-outside-toplevel
            registrar_predicado_sidebar,
        )
        from iam.roles_vat import (  # pylint: disable=import-outside-toplevel
            es_usuario_solo_vat,
        )

        # Menú "solo VAT": regla de kernel, vale en el core y en cada backend.
        registrar_predicado_sidebar("vat", es_usuario_solo_vat)
