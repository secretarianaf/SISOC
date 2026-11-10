from django.db import migrations, models

ESTADOS_FINALIZADOS = ("Finalizado", "Finalizado/Excepciones")
LOTE = 500

# Copia congelada de relevamientos/services/datos_comedor_snapshot.py: la
# migración no importa código vivo, que puede cambiar después.
CAMPOS_PERSONA = ("nombre", "apellido", "documento", "mail", "celular", "funcion")
CAMPOS_COMEDOR = (
    "nombre",
    "comienzo",
    "calle",
    "numero",
    "entre_calle_1",
    "entre_calle_2",
    "partido",
    "barrio",
    "codigo_postal",
)


def _nombre_de(objeto):
    return getattr(objeto, "nombre", None) if objeto is not None else None


def _datos_persona(persona):
    return {campo: getattr(persona, campo, None) for campo in CAMPOS_PERSONA}


def armar_snapshot(comedor, responsable=None):
    datos = {campo: getattr(comedor, campo, None) for campo in CAMPOS_COMEDOR}
    datos["provincia"] = _nombre_de(comedor.provincia)
    datos["municipio"] = _nombre_de(comedor.municipio)
    datos["localidad"] = _nombre_de(comedor.localidad)
    datos["programa"] = _nombre_de(comedor.programa)
    datos["referente"] = _datos_persona(comedor.referente)
    datos["responsable"] = _datos_persona(responsable)
    return datos


def completar_snapshot_de_finalizados(apps, schema_editor):
    """#2797: los finalizados existentes quedan con los datos actuales del comedor.

    Es lo mejor que se puede reconstruir: no hay historial de ediciones previas.
    """
    relevamiento_model = apps.get_model("relevamientos", "Relevamiento")
    queryset = (
        relevamiento_model.objects.filter(
            estado__in=ESTADOS_FINALIZADOS, datos_comedor_snapshot__isnull=True
        )
        .select_related(
            "comedor",
            "comedor__provincia",
            "comedor__municipio",
            "comedor__localidad",
            "comedor__programa",
            "comedor__referente",
            "responsable_relevamiento",
        )
        .order_by("pk")
    )
    lote = []
    for relevamiento in queryset.iterator(chunk_size=LOTE):
        relevamiento.datos_comedor_snapshot = armar_snapshot(
            relevamiento.comedor, relevamiento.responsable_relevamiento
        )
        lote.append(relevamiento)
        if len(lote) >= LOTE:
            relevamiento_model.objects.bulk_update(lote, ["datos_comedor_snapshot"])
            lote = []
    if lote:
        relevamiento_model.objects.bulk_update(lote, ["datos_comedor_snapshot"])


class Migration(migrations.Migration):

    dependencies = [
        ("relevamientos", "0023_pdf_oficial_gestionar"),
    ]

    operations = [
        migrations.AddField(
            model_name="relevamiento",
            name="datos_comedor_snapshot",
            field=models.JSONField(
                blank=True,
                help_text=(
                    "Datos generales del comedor al finalizar el relevamiento "
                    "(#2797). Evita que editar el comedor cambie relevamientos "
                    "ya hechos."
                ),
                null=True,
            ),
        ),
        migrations.RunPython(
            completar_snapshot_de_finalizados, migrations.RunPython.noop
        ),
    ]
