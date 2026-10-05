"""``organizaciones`` deja de declarar Firmante (ahora en gestion_organizaciones).

Solo estado: la tabla ``organizaciones_firmante`` la sigue usando el core.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("organizaciones", "0022_issue_2445_territoriales_abordaje_comunitario"),
        ("gestion_organizaciones", "0001_firmante_desde_organizaciones"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(
                    name="Firmante",
                ),
            ],
            database_operations=[],
        ),
    ]
