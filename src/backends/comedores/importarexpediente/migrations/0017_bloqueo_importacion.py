from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("importarexpediente", "0016_cambio_estado_importacion")]

    operations = [
        migrations.CreateModel(
            name="BloqueoImportacion",
            fields=[
                (
                    "id",
                    models.PositiveSmallIntegerField(primary_key=True, serialize=False),
                )
            ],
        ),
    ]
