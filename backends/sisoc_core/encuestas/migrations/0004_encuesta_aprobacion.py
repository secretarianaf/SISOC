from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("encuestas", "0003_encuesta_opcional")]

    operations = [
        migrations.AlterModelOptions(
            name="encuesta",
            options={
                "ordering": ["-fecha_creacion"],
                "verbose_name": "Encuesta",
                "verbose_name_plural": "Encuestas",
                "permissions": [
                    ("ver_resultados", "Puede ver los resultados de las encuestas"),
                    (
                        "aprobar_encuesta",
                        "Puede aprobar o rechazar la publicación de encuestas",
                    ),
                ],
            },
        ),
        migrations.AlterField(
            model_name="encuesta",
            name="estado",
            field=models.CharField(
                max_length=20,
                default="borrador",
                verbose_name="Estado",
                choices=[
                    ("borrador", "Borrador"),
                    ("pendiente_aprobacion", "Pendiente aprobación"),
                    ("publicada", "Publicada"),
                    ("cerrada", "Cerrada"),
                    ("archivada", "Archivada"),
                ],
            ),
        ),
    ]
