# pylint: disable=invalid-name
from django.db import migrations, models
from django.db.models.functions import Coalesce


def registrar_gestiones_existentes(apps, schema_editor):
    rendicion = apps.get_model("rendicioncuentasmensual", "RendicionCuentaMensual")
    rendicion.objects.using(schema_editor.connection.alias).filter(
        etapa_proceso__in=["auditoria", "regularizacion"],
        validada__isnull=False,
        genera_acta_auditoria__isnull=False,
    ).update(
        fecha_gestion_auditoria=Coalesce(
            "fecha_auditada", "fecha_carga_auditoria", "ultima_modificacion"
        )
    )


class Migration(migrations.Migration):
    dependencies = [("rendicioncuentasmensual", "0023_issue_2673_validada")]

    operations = [
        migrations.AddField(
            model_name="rendicioncuentamensual",
            name="fecha_gestion_auditoria",
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name="Fecha de cierre de gestión de auditoría",
            ),
        ),
        migrations.RunPython(registrar_gestiones_existentes, migrations.RunPython.noop),
    ]
