from django.apps import AppConfig


class CentrodeinfanciaConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "centrodeinfancia"
    verbose_name = "Centro de Desarrollo Infantil"

    def ready(self):
        import centrodeinfancia.signals  # pylint: disable=unused-import,import-outside-toplevel
        from centrodeinfancia.access import (  # pylint: disable=import-outside-toplevel
            aplicar_scope_usuarios_cdi,
        )
        from centrodeinfancia.sidebar_access import (  # pylint: disable=import-outside-toplevel
            registrar_acceso_sidebar,
        )
        from iam.services import (  # pylint: disable=import-outside-toplevel
            register_user_queryset_scope,
        )
        from core.internal_services import (
            registrar_servicio_interno,
        )  # pylint: disable=import-outside-toplevel
        from centrodeinfancia.selector_tableros import (
            RUTA_SELECTOR,
            consultar_centros,
        )  # pylint: disable=import-outside-toplevel

        register_user_queryset_scope(
            "centrodeinfancia",
            aplicar_scope_usuarios_cdi,
        )
        registrar_acceso_sidebar()
        registrar_servicio_interno(RUTA_SELECTOR, consultar_centros)
