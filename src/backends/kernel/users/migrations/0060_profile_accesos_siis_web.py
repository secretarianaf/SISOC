from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("users", "0059_remove_profile_duplas_asignadas")]
    operations = [
        migrations.AddField(
            model_name="profile",
            name="acceso_web",
            field=models.BooleanField(default=True, verbose_name="Acceso SISOC web"),
        ),
        migrations.AddField(
            model_name="profile",
            name="acceso_siis",
            field=models.BooleanField(default=False, verbose_name="Acceso SIIS"),
        ),
    ]
