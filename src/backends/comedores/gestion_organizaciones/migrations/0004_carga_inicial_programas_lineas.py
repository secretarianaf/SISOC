"""Carga inicial de programas por organización y línea por proyecto (#2745).

Definiciones 15, 18 y 25 del plan
``docs/plans/2026-T4/2026-10-20-2745-legajo-organizacion-por-programa.md``:

- Cada organización recibe un ``ProgramaOrganizacion`` por cada programa
  distinto de sus comedores, incluidos los dados de baja y los programas que
  no son los tres del legajo.
- Cada proyecto recibe la línea (Secos o Tradicional) de los comedores que lo
  usan, solo si todos tienen el mismo programa y ese programa es una línea de
  Abordaje. Si no, queda sin línea (no se adivina) y se informa en el log.

Preservación de datos (sección 2.1): solo agrega filas en tablas nuevas, no
modifica ni borra nada existente, es idempotente y su reversa no borra nada.
Usa ``_base_manager`` para no excluir registros dados de baja. No importa
``comedores.utils``: replica la normalización de nombres con los modelos de
la migración.

Las organizaciones con comedores creadas después de esta migración no reciben
programas automáticamente; las reglas nuevas no las bloquean (definición 22).
"""

import logging
import unicodedata

from django.db import migrations

logger = logging.getLogger("django")

BATCH_SIZE = 1000


def _normalizar(nombre):
    sin_acentos = unicodedata.normalize("NFD", nombre or "")
    sin_acentos = "".join(c for c in sin_acentos if not unicodedata.combining(c))
    return " ".join(sin_acentos.lower().split())


def _es_linea_abordaje(nombre):
    normalizado = _normalizar(nombre)
    return "abordaje comunitario" in normalizado and (
        "linea secos" in normalizado or "linea tradicional" in normalizado
    )


def cargar_programas_organizacion(apps):
    comedor_model = apps.get_model("comedores", "Comedor")
    programa_org_model = apps.get_model(
        "gestion_organizaciones", "ProgramaOrganizacion"
    )

    pares = set(
        comedor_model._base_manager.filter(
            organizacion__isnull=False, programa__isnull=False
        ).values_list("organizacion_id", "programa_id")
    )
    existentes = set(
        programa_org_model._base_manager.values_list("organizacion_id", "programa_id")
    )
    nuevos = [
        programa_org_model(organizacion_id=organizacion_id, programa_id=programa_id)
        for organizacion_id, programa_id in sorted(pares - existentes)
    ]
    programa_org_model._base_manager.bulk_create(nuevos, batch_size=BATCH_SIZE)
    return len(nuevos)


def cargar_lineas_proyecto(apps):
    comedor_model = apps.get_model("comedores", "Comedor")
    programas_model = apps.get_model("comedores", "Programas")
    linea_model = apps.get_model("gestion_organizaciones", "LineaProyecto")

    es_linea = {
        programa.id: _es_linea_abordaje(programa.nombre)
        for programa in programas_model._base_manager.all()
    }
    programas_por_proyecto = {}
    for proyecto_id, programa_id in comedor_model._base_manager.filter(
        proyecto__isnull=False
    ).values_list("proyecto_id", "programa_id"):
        programas_por_proyecto.setdefault(proyecto_id, set()).add(programa_id)

    con_linea = set(linea_model._base_manager.values_list("proyecto_id", flat=True))
    nuevas = []
    ambiguos = []
    for proyecto_id, programas in sorted(programas_por_proyecto.items()):
        if proyecto_id in con_linea:
            continue
        if len(programas) == 1:
            (programa_id,) = programas
            if programa_id is not None and es_linea.get(programa_id):
                nuevas.append(
                    linea_model(proyecto_id=proyecto_id, programa_id=programa_id)
                )
                continue
        ambiguos.append(proyecto_id)
    linea_model._base_manager.bulk_create(nuevas, batch_size=BATCH_SIZE)
    return len(nuevas), ambiguos


def carga_inicial(apps, schema_editor):
    del schema_editor
    proyecto_model = apps.get_model("organizaciones", "ProyectoOrganizacion")
    linea_model = apps.get_model("gestion_organizaciones", "LineaProyecto")

    programas_creados = cargar_programas_organizacion(apps)
    lineas_creadas, ambiguos = cargar_lineas_proyecto(apps)
    sin_comedores = list(
        proyecto_model._base_manager.exclude(
            pk__in=linea_model._base_manager.values_list("proyecto_id", flat=True)
        )
        .exclude(pk__in=ambiguos)
        .values_list("pk", flat=True)
    )

    logger.info(
        "[#2745] Carga inicial: %s programas de organización creados; "
        "%s líneas de proyecto asignadas; %s proyectos con comedores de "
        "programas distintos o fuera de Abordaje; %s proyectos sin comedores.",
        programas_creados,
        lineas_creadas,
        len(ambiguos),
        len(sin_comedores),
    )
    if ambiguos:
        logger.warning(
            "[#2745] Proyectos sin línea por ambigüedad (completar a mano): %s",
            ambiguos,
        )
    if sin_comedores:
        logger.warning(
            "[#2745] Proyectos sin línea por no tener comedores (completar a mano): %s",
            sin_comedores,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("gestion_organizaciones", "0003_catalogo_region_subzona"),
        ("comedores", "0063_merge_subido_por_responsable_tarjeta"),
        ("organizaciones", "0023_firmante_a_gestion"),
    ]

    operations = [
        migrations.RunPython(carga_inicial, migrations.RunPython.noop),
    ]
