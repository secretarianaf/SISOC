# Django migration filenames use a numeric prefix.
# pylint: disable=invalid-name
from django.db import migrations, models


def verificar_reversion(apps, schema_editor):
    configuracion = apps.get_model("dashboard", "ConfiguracionTableroInterno")
    if (
        configuracion.objects.using(schema_editor.connection.alias)
        .filter(codigo="celiaquia")
        .exists()
    ):
        raise RuntimeError(
            "No se puede revertir: existen configuraciones de Celiaquía. "
            "Resolverlas antes de restaurar la restricción anterior."
        )


class Migration(migrations.Migration):
    dependencies = [("dashboard", "0008_tablero_visible_menu_alter_tablero_activo")]

    operations = [
        migrations.RemoveConstraint(
            model_name="configuraciontablerointerno",
            name="dashboard_interno_codigo_valido",
        ),
        migrations.AddConstraint(
            model_name="configuraciontablerointerno",
            constraint=models.CheckConstraint(
                condition=models.Q(codigo__in=("progresar_curso", "celiaquia")),
                name="dashboard_interno_codigo_valido",
            ),
        ),
        migrations.RunPython(migrations.RunPython.noop, verificar_reversion),
    ]
