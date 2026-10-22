"""``Profile.duplas_asignadas`` pasa a declararse como ``Dupla.coordinadores``.

Solo estado: la tabla intermedia ``users_profile_duplas_asignadas`` y sus
columnas (``profile_id``, ``dupla_id``) no cambian. El kernel (``users``) deja
de depender de ``duplas``. Ver
docs/registro/decisiones/2026-09-30-monorepo-kernel-backends.md.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("duplas", "0001_squashed_0003"),
        ("users", "0058_accesos_pwa_a_pwa"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name="dupla",
                    name="coordinadores",
                    field=models.ManyToManyField(
                        blank=True,
                        db_table="users_profile_duplas_asignadas",
                        help_text="Perfiles de coordinador que tienen asignada esta dupla",
                        related_name="duplas_asignadas",
                        to="users.profile",
                        verbose_name="Coordinadores",
                    ),
                ),
            ],
            database_operations=[],
        ),
    ]
