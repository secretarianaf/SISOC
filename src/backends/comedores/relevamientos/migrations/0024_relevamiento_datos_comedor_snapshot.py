from django.db import migrations, models

from relevamientos.services.datos_comedor_snapshot import armar_snapshot

ESTADOS_FINALIZADOS = ("Finalizado", "Finalizado/Excepciones")
LOTE = 500


def completar_snapshot_de_finalizados(apps, schema_editor):
    """#2797: los finalizados existentes quedan con los datos actuales del comedor.

    Es lo mejor que se puede reconstruir: no hay historial de ediciones previas.
    ``armar_snapshot`` es pura (solo acceso por atributo), sirve con modelos
    históricos.
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
