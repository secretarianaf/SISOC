# pylint: disable=invalid-name
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("rendicioncuentasmensual", "0023_issue_2673_validada")]

    operations = [
        migrations.AddField(
            model_name="rendicioncuentamensual",
            name="fecha_gestion_auditoria",
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name="Fecha de cierre de gestión de auditoría",
            ),
        ),
    ]
