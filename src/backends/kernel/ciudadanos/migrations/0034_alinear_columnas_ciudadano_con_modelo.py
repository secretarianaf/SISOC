# Las AlterField de ``altura``, ``codigo_postal`` y ``observaciones`` quedaron
# solo en ``state_operations`` de 0009_squashed_0028: Django cree que son
# varchar/longtext, pero en MySQL siguen como int y varchar(500) (#2750).
# Se corrige solo lo que difiere y en un único ALTER por tabla, porque
# ``ciudadanos_ciudadano`` es grande y cada ALTER de tipo copia la tabla.

from django.db import migrations

COLUMNAS_A_ALINEAR = {
    "Ciudadano": ("altura", "codigo_postal", "observaciones"),
    "GrupoFamiliar": ("observaciones",),
}


def _tipos_actuales(cursor, tabla):
    cursor.execute(
        "SELECT column_name, column_type FROM information_schema.columns "
        "WHERE table_schema = DATABASE() AND table_name = %s",
        [tabla],
    )
    return {nombre.lower(): tipo.lower() for nombre, tipo in cursor.fetchall()}


def alinear_columnas(apps, schema_editor):
    connection = schema_editor.connection
    if connection.vendor != "mysql":
        return
    quote = schema_editor.quote_name
    for model_name, field_names in COLUMNAS_A_ALINEAR.items():
        model = apps.get_model("ciudadanos", model_name)
        tabla = model._meta.db_table
        with connection.cursor() as cursor:
            actuales = _tipos_actuales(cursor, tabla)
        cambios = []
        for field_name in field_names:
            field = model._meta.get_field(field_name)
            esperado = field.db_type(connection).lower()
            actual = actuales.get(field.column.lower())
            if actual is None or actual == esperado:
                continue
            nulo = "NULL" if field.null else "NOT NULL"
            cambios.append(f"MODIFY {quote(field.column)} {esperado} {nulo}")
        if cambios:
            schema_editor.execute(f"ALTER TABLE {quote(tabla)} {', '.join(cambios)}")


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ("ciudadanos", "0033_ciudadanosimportjob_lease_token"),
    ]

    operations = [
        migrations.RunPython(alinear_columnas, migrations.RunPython.noop),
    ]
