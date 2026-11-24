from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("centrodeinfancia", "0054_formulario_calidad_p101_otro_text"),
    ]

    operations = [
        migrations.AlterField(
            model_name="intervencioncentroinfancia",
            name="documentacion",
            field=models.FileField(
                blank=True,
                null=True,
                upload_to="cdi/documentacion/",
            ),
        ),
    ]
