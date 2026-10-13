from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("dispositivos", "0005_remove_dispositivo_domicilio_institucion_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="dispositivo",
            name="ubicacion_georef",
            field=models.JSONField(blank=True, default=dict, editable=False),
        ),
    ]
