from django.apps import AppConfig
from django.db.models.signals import post_migrate


class PwaConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "pwa"
    verbose_name = "Espacios comunitarios"

    def ready(self):
        from pwa.signals import (
            seed_catalogo_actividades,
        )  # pylint: disable=import-outside-toplevel

        post_migrate.connect(
            seed_catalogo_actividades,
            sender=self,
            dispatch_uid="pwa.bootstrap_catalogo",
        )
        from pwa.ciudadano_detail import (  # pylint: disable=import-outside-toplevel
            registrar_contribucion_ciudadano,
        )

        registrar_contribucion_ciudadano()
        from pwa.identity_services import (  # pylint: disable=import-outside-toplevel
            registrar_servicios_identidad,
        )

        registrar_servicios_identidad()
        from pwa.user_admin_views import (  # pylint: disable=import-outside-toplevel
            registrar_operacion_usuario,
        )

        registrar_operacion_usuario()
