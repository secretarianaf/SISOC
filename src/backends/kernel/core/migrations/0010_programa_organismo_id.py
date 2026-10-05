"""``Programa.organismo`` (FK a ``organizaciones``) pasa a ``organismo_id`` entero.

Solo estado: la columna ``organismo_id``, su índice y la FK física siguen en
la DB. El kernel deja de declarar una relación con ``organizaciones``, que es
del core. El SET_NULL al borrar la organización lo hace
``organizaciones.programa_signals``.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0009_renaper_consulta_rate_limit"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveField(
                    model_name="programa",
                    name="organismo",
                ),
                migrations.AddField(
                    model_name="programa",
                    name="organismo_id",
                    field=models.IntegerField(
                        blank=True, db_index=True, null=True, verbose_name="Organismo"
                    ),
                ),
            ],
            database_operations=[],
        ),
    ]
