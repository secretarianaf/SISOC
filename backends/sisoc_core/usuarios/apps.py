from django.apps import AppConfig


class UsuariosConfig(AppConfig):
    """Gestión de usuarios del SISOC core.

    Pantallas, formularios, importación masiva y la API de login de las PWAs.
    La identidad y los permisos que comparten todos los servicios viven en
    ``kernel/users``; esta app es del core y puede depender de sus dominios
    (comedores, organizaciones, duplas, pwa).
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "usuarios"
