from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("centrodeinfancia", "0051_accesocdi_estado_responsable"),
    ]

    operations = [
        migrations.AddField(
            model_name="nominacentroinfancia",
            name="responsable_legal_1_sin_cuil",
            field=models.BooleanField(default=False, verbose_name="No posee CUIL"),
        ),
        migrations.AddField(
            model_name="nominacentroinfancia",
            name="sin_cuil_nino",
            field=models.BooleanField(default=False, verbose_name="No posee CUIL"),
        ),
        migrations.AddField(
            model_name="trabajador",
            name="sin_cuil",
            field=models.BooleanField(default=False, verbose_name="No posee CUIL"),
        ),
    ]
