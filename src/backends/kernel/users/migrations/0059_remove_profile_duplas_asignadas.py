"""``users`` deja de declarar ``Profile.duplas_asignadas`` (ahora en ``duplas``).

Solo estado: la tabla ``users_profile_duplas_asignadas`` la sigue usando
``duplas.Dupla.coordinadores`` (``duplas/migrations/0004``).
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0058_accesos_pwa_a_pwa"),
        ("duplas", "0004_dupla_coordinadores"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveField(
                    model_name="profile",
                    name="duplas_asignadas",
                ),
            ],
            database_operations=[],
        ),
    ]
