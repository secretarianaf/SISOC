from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("admisiones", "0082_caratula_borrador"),
    ]

    operations = [
        migrations.AddField(
            model_name="admision",
            name="datos_organizacion_snapshot",
            field=models.JSONField(
                blank=True,
                help_text=(
                    "Datos de la organizacion que precargan el informe tecnico"
                    " ('informe') y ultimo estado del legajo aceptado ('legajo')."
                ),
                null=True,
                verbose_name="Snapshot de datos de la organizacion",
            ),
        ),
    ]
