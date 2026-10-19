from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("comedores", "0059_comedorpwacreateoperation"),
    ]

    operations = [
        migrations.AddField(
            model_name="imagencomedor",
            name="subido_por",
            field=models.ForeignKey(
                blank=True,
                help_text=(
                    "Usuario que subió la foto desde la app. Solo él puede borrarla "
                    "por la API territorial. Null en las fotos de SISOC web y en las "
                    "anteriores a este campo."
                ),
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
