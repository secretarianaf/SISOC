"""Accesos PWA: ``users`` deja de declarar los 4 modelos (ahora en ``pwa``).

Solo estado: las tablas ``users_*`` siguen existiendo y las usa ``pwa``.
Ver ``pwa/migrations/0025_accesos_pwa_desde_users.py``.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("pwa", "0025_accesos_pwa_desde_users"),
        ("users", "0056_issue_2444_roles_territoriales_pnud"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveField(
                    model_name="auditaccesocomedorpwa",
                    name="acceso",
                ),
                migrations.RemoveField(
                    model_name="accesoorganizacionpwa",
                    name="creado_por",
                ),
                migrations.RemoveField(
                    model_name="accesoorganizacionpwa",
                    name="organizacion",
                ),
                migrations.RemoveField(
                    model_name="accesoorganizacionpwa",
                    name="user",
                ),
                migrations.RemoveField(
                    model_name="auditaccesocomedorpwa",
                    name="actor",
                ),
                migrations.RemoveField(
                    model_name="auditaccesocomedorpwa",
                    name="comedor",
                ),
                migrations.RemoveField(
                    model_name="auditaccesocomedorpwa",
                    name="organizacion",
                ),
                migrations.RemoveField(
                    model_name="auditaccesocomedorpwa",
                    name="user",
                ),
                migrations.RemoveField(
                    model_name="coordinadorequipotecnicopwa",
                    name="comedores_adicionales",
                ),
                migrations.RemoveField(
                    model_name="coordinadorequipotecnicopwa",
                    name="duplas",
                ),
                migrations.RemoveField(
                    model_name="coordinadorequipotecnicopwa",
                    name="user",
                ),
                migrations.DeleteModel(
                    name="AccesoComedorPWA",
                ),
                migrations.DeleteModel(
                    name="AccesoOrganizacionPWA",
                ),
                migrations.DeleteModel(
                    name="AuditAccesoComedorPWA",
                ),
                migrations.DeleteModel(
                    name="CoordinadorEquipoTecnicoPWA",
                ),
            ],
            database_operations=[],
        ),
    ]
