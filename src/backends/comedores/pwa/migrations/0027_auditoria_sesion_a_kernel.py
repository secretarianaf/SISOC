"""Elimina solo el estado antiguo; la tabla pertenece ahora a audittrail."""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("pwa", "0026_inicializar_acceso_web"),
        ("audittrail", "0002_auditoria_sesion_desde_pwa"),
    ]
    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[migrations.DeleteModel(name="AuditoriaSesionPWA")],
        ),
    ]
