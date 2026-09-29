"""Copia a cada jornada el checklist que antes se compartia por sede.

Antes el checklist vivia en la sede y la fila apuntaba solo a la primera
jornada que lo cargo. Ahora se lee por jornada, asi que las demas jornadas
de la misma sede lo verian vacio. No cambia estados de jornada.
"""

from django.db import migrations

CAMPOS_COPIADOS = (
    "item",
    "descripcion",
    "critico",
    "cumple",
    "observacion",
    "responsable",
)


def copiar_checklist_de_sede_a_jornadas(apps, schema_editor):
    checklist_model = apps.get_model("ver_para_ser_libre", "ChecklistJornadaVPSL")
    jornada_model = apps.get_model("ver_para_ser_libre", "JornadaVPSL")

    checklist_por_sede = {}
    for fila in checklist_model.objects.filter(sede__isnull=False).order_by("pk"):
        checklist_por_sede.setdefault(fila.sede_id, {}).setdefault(fila.item, fila)
    if not checklist_por_sede:
        return

    items_existentes = set(
        checklist_model.objects.filter(jornada__isnull=False).values_list(
            "jornada_id", "item"
        )
    )
    nuevas = []
    jornadas = jornada_model.objects.filter(
        sede_vpsl_id__in=checklist_por_sede
    ).values_list("pk", "sede_vpsl_id")
    for jornada_id, sede_id in jornadas.iterator():
        for item, origen in checklist_por_sede[sede_id].items():
            if (jornada_id, item) in items_existentes:
                continue
            nuevas.append(
                checklist_model(
                    jornada_id=jornada_id,
                    sede_id=sede_id,
                    # Se referencia el mismo archivo; no se duplica en storage.
                    evidencia=origen.evidencia.name or None,
                    **{campo: getattr(origen, campo) for campo in CAMPOS_COPIADOS},
                )
            )
    checklist_model.objects.bulk_create(nuevas, batch_size=500)


def eliminar_copias_de_checklist(apps, schema_editor):
    # El flujo anterior espera una sola fila por (sede, item): se conserva la
    # original (menor pk) y se eliminan las copias.
    checklist_model = apps.get_model("ver_para_ser_libre", "ChecklistJornadaVPSL")
    vistos = set()
    copias = []
    filas = (
        checklist_model.objects.filter(sede__isnull=False)
        .order_by("pk")
        .values_list("pk", "sede_id", "item")
    )
    for pk, sede_id, item in filas.iterator():
        if (sede_id, item) in vistos:
            copias.append(pk)
        else:
            vistos.add((sede_id, item))
    checklist_model.objects.filter(pk__in=copias).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("ver_para_ser_libre", "0015_vpsl_ubicacion_vehiculos_graduaciones"),
    ]

    operations = [
        migrations.RunPython(
            copiar_checklist_de_sede_a_jornadas,
            reverse_code=eliminar_copias_de_checklist,
        ),
    ]
