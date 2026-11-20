from django.db import migrations

VARIABLES_DOCUMENTALES = (
    (
        "informe.if_ultimo_informe_tecnico",
        "IF del último Informe Técnico",
        "Renovaciones - antecedentes",
        14,
    ),
    (
        "informe.if_referencia_prestaciones",
        "IF de referencia de prestaciones (IT Complementario o último IT)",
        "Renovaciones - Informe Complementario",
        15,
    ),
)


def registrar_variables(apps, schema_editor):
    variable_model = apps.get_model("admisiones", "VariableTemplateInformeTecnico")
    for codigo, nombre, categoria, orden in VARIABLES_DOCUMENTALES:
        variable_model.objects.update_or_create(
            codigo=codigo,
            defaults={
                "nombre": nombre,
                "categoria": categoria,
                "orden": orden,
                "activo": True,
            },
        )


def eliminar_variables(apps, schema_editor):
    variable_model = apps.get_model("admisiones", "VariableTemplateInformeTecnico")
    variable_model.objects.filter(
        codigo__in=[codigo for codigo, *_ in VARIABLES_DOCUMENTALES]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [("admisiones", "0083_admision_datos_organizacion_snapshot")]

    operations = [
        migrations.RunPython(registrar_variables, eliminar_variables),
    ]
