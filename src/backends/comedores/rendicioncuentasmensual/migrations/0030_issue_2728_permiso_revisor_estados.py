from django.db import migrations


class Migration(migrations.Migration):
    """Permiso del usuario revisor de estados (issue #2728).

    Solo declara el permiso: Django lo crea al migrar y no se asigna a ningún
    grupo, para que se otorgue a demanda desde Usuarios > Grupos.
    """

    dependencies = [
        ("rendicioncuentasmensual", "0029_merge_pdf_descarga_upload_to"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="rendicioncuentamensual",
            options={
                "permissions": [
                    ("manage_mobile_rendicion", "Puede gestionar rendiciones mobile"),
                    ("edit_rendicion_data", "Puede editar datos de rendición"),
                    (
                        "manage_territorial_stage",
                        "Puede gestionar la etapa Revisión Territorial",
                    ),
                    (
                        "manage_auditoria_review_stage",
                        "Puede gestionar la etapa Revisión de Auditoría",
                    ),
                    (
                        "manage_auditoria_stage",
                        "Puede gestionar la etapa Auditoría",
                    ),
                    (
                        "manage_regularizacion_stage",
                        "Puede gestionar la etapa Regularización",
                    ),
                    (
                        "change_review_stage_state",
                        "Puede modificar el estado de rendiciones en revisión",
                    ),
                ],
                "verbose_name": "Rendición de Cuenta Mensual",
                "verbose_name_plural": "Rendiciones de Cuenta Mensuales",
            },
        ),
    ]
