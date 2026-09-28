"""Actas complementarias ya cargadas desde la app -> "Pendiente validación
coordinador".

La 0020 agregó el ciclo de validación con ``estado_validacion`` vacío, y la app
lee vacío como "todavía no enviada". Las actas que la app ya envió (``origen``
app y con contenido) entran a la bandeja del coordinador; el resto (cargadas o
asignadas desde SISOC, o vacías) queda vacío.

Reversible, pero la vuelta NO es exacta: deja vacías todas las actas de la
app en "Pendiente" que el coordinador todavía no revisó (sin coordinador ni
fecha de revisión). Eso incluye las que movió la ida y también las que la app
envió (POST o PATCH) después de la 0020 y siguen sin revisar: no hay columna
que distinga unas de otras. Solo tiene sentido volver atrás junto con la 0020,
que borra el campo de todos modos.
"""

from django.db import migrations
from django.db.models import Q

PENDIENTE = "Pendiente validación coordinador"


def _con_contenido():
    return (
        (Q(observaciones__isnull=False) & ~Q(observaciones=""))
        | (Q(firma__isnull=False) & ~Q(firma=""))
        | Q(fecha_hora__isnull=False)
        | Q(prestaciones__isnull=False)
    )


def marcar_pendientes(apps, schema_editor):
    ActaComplementaria = apps.get_model("relevamientos", "ActaComplementaria")
    ids = (
        ActaComplementaria.objects.filter(origen="app", estado_validacion__isnull=True)
        .filter(_con_contenido())
        .values_list("id", flat=True)
        .distinct()
    )
    ActaComplementaria.objects.filter(id__in=list(ids)).update(
        estado_validacion=PENDIENTE
    )


def desmarcar_pendientes(apps, schema_editor):
    ActaComplementaria = apps.get_model("relevamientos", "ActaComplementaria")
    ActaComplementaria.objects.filter(
        origen="app",
        estado_validacion=PENDIENTE,
        coordinador__isnull=True,
        fecha_revision_coordinador__isnull=True,
    ).update(estado_validacion=None)


class Migration(migrations.Migration):

    dependencies = [
        ("relevamientos", "0020_acta_complementaria_validacion"),
    ]

    operations = [
        migrations.RunPython(marcar_pendientes, desmarcar_pendientes),
    ]
