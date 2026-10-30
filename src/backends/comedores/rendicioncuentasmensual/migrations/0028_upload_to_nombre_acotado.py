# Cambia solo ``upload_to`` (estado de Django); no altera columnas ni archivos.

from django.db import migrations, models

import rendicioncuentasmensual.models


class Migration(migrations.Migration):

    dependencies = [
        ("rendicioncuentasmensual", "0027_issue_2642_abordaje_comunitario"),
    ]

    operations = [
        migrations.AlterField(
            model_name="documentacionadjunta",
            name="archivo",
            field=models.FileField(
                upload_to=rendicioncuentasmensual.models.documentacion_adjunta_upload_to,
                verbose_name="Archivo",
            ),
        ),
        migrations.AlterField(
            model_name="rendicioncuentamensual",
            name="acta_auditoria",
            field=models.FileField(
                blank=True,
                null=True,
                upload_to=rendicioncuentasmensual.models.acta_auditoria_upload_to,
                verbose_name="PDF Acta de Auditoría",
            ),
        ),
        migrations.AlterField(
            model_name="rendicioncuentamensual",
            name="documento_regularizacion",
            field=models.FileField(
                blank=True,
                null=True,
                upload_to=rendicioncuentasmensual.models.documento_regularizacion_upload_to,
                verbose_name="PDF Regularización",
            ),
        ),
    ]
