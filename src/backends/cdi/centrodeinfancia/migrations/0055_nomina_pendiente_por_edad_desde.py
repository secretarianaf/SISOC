from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("centrodeinfancia", "0054_formulario_calidad_p101_otro_text"),
    ]

    operations = [
        migrations.AddField(
            model_name="nominacentroinfancia",
            name="pendiente_por_edad_desde",
            field=models.DateField(
                blank=True,
                editable=False,
                null=True,
                verbose_name="Pendiente por edad desde",
            ),
        ),
    ]
