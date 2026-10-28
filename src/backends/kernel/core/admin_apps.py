"""AppConfig del admin de SISOC: reemplaza a ``django.contrib.admin`` en INSTALLED_APPS.

Vive fuera de ``core/apps.py`` para que Django siga eligiendo ``CoreConfig``
como config por defecto de ``core``.
"""

from django.contrib.admin.apps import AdminConfig


class SisocAdminConfig(AdminConfig):
    """Instala ``SisocAdminSite`` (Unfold + solo superusuarios) como ``admin.site``."""

    default_site = "core.admin_site.SisocAdminSite"
