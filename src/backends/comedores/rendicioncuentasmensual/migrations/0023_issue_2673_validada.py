# pylint: disable=invalid-name
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("rendicioncuentasmensual", "0022_issue_2377_acta_auditoria")]

    operations = [
        migrations.AddField(
            model_name="rendicioncuentamensual",
            name="validada",
            field=models.BooleanField(blank=True, null=True, verbose_name="¿Validada?"),
        ),
    ]
