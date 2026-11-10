"""Retira la Región y Subzona propias del #2745: se usan las del #2642.

Decisión del 26/10/2026 (definición 28 del plan
``docs/plans/2026-T4/2026-10-20-2745-legajo-organizacion-por-programa.md``):
la Región y la Subzona de la organización son ``Organizacion.region_abordaje``
y ``subzona_abordaje`` (kernel, #2642). Las tablas de la Etapa 1
(``RegionAbordaje``, ``SubzonaAbordaje``, ``DatosRegionOrganizacion``) quedan
sin uso.

Antes de borrarlas se copia todo al catálogo y a los campos del #2642 (plan,
sección 2.1): las regiones y subzonas que use alguna organización y falten se
agregan al catálogo del kernel, y la región y subzona de cada organización
pasan a sus campos. Si algo
no se puede copiar sin pisar un dato distinto, la migración se frena y lista
los casos para resolverlos a mano. La reversa recrea las tablas vacías.
"""

# pylint: disable=invalid-name,protected-access

from django.db import migrations


class RegionNoCopiable(RuntimeError):
    pass


def _copiar_catalogo(apps, alias, conflictos, usados):
    """Copia al kernel solo las regiones y subzonas que usa alguna organización.

    El resto del catálogo del #2745 es igual al del #2642 (mismo Excel): no se
    toca el del kernel por gusto.
    """
    region_propia = apps.get_model("gestion_organizaciones", "RegionAbordaje")
    subzona_propia = apps.get_model("gestion_organizaciones", "SubzonaAbordaje")
    region_kernel = apps.get_model("organizaciones", "RegionAbordajeComunitario")
    subzona_kernel = apps.get_model("organizaciones", "SubzonaAbordajeComunitario")

    subzonas_usadas = subzona_propia.objects.using(alias).filter(
        pk__in=usados.values("subzona_id")
    )
    regiones = {}
    for region in region_propia.objects.using(alias).filter(
        pk__in=list(usados.values_list("region_id", flat=True))
        + list(subzonas_usadas.values_list("region_id", flat=True))
    ):
        regiones[region.pk], _ = region_kernel.objects.using(alias).get_or_create(
            nombre=region.nombre
        )

    subzonas = {}
    for subzona in subzonas_usadas:
        region = regiones[subzona.region_id]
        existente = (
            subzona_kernel.objects.using(alias).filter(nombre=subzona.nombre).first()
        )
        if existente is None:
            existente = subzona_kernel.objects.using(alias).create(
                nombre=subzona.nombre, region=region
            )
        elif existente.region_id is None:
            existente.region = region
            existente.save(update_fields=["region"])
        elif existente.region_id != region.pk:
            conflictos.append(
                f"La subzona {subzona.nombre} es de {subzona.region} en el "
                f"#2745 y de otra región en el #2642."
            )
        subzonas[subzona.pk] = existente
    return regiones, subzonas


def _conflictos_de(organizacion, valores):
    """Campos que ya tienen un valor distinto: no se pisan."""
    return [
        f"La organización {organizacion.pk} ({organizacion.nombre}) tiene otro "
        f"valor en {campo}: no se pisa con {valor.nombre}."
        for campo, valor in valores.items()
        if getattr(organizacion, f"{campo}_id") not in (None, valor.pk)
    ]


def copiar_region_al_2642(apps, schema_editor):
    alias = schema_editor.connection.alias
    datos_region = apps.get_model("gestion_organizaciones", "DatosRegionOrganizacion")
    organizacion_model = apps.get_model("organizaciones", "Organizacion")

    conflictos = []
    usados = datos_region.objects.using(alias).all()
    regiones, subzonas = _copiar_catalogo(apps, alias, conflictos, usados)

    cambios = []
    for datos in usados:
        # _base_manager: incluye organizaciones dadas de baja.
        organizacion = organizacion_model._base_manager.using(alias).get(
            pk=datos.organizacion_id
        )
        valores = {
            "region_abordaje": regiones[datos.region_id],
            "subzona_abordaje": subzonas[datos.subzona_id],
        }
        conflictos.extend(_conflictos_de(organizacion, valores))
        cambios.append(
            (organizacion.pk, {f"{campo}_id": v.pk for campo, v in valores.items()})
        )

    if conflictos:
        raise RegionNoCopiable(
            "No se puede retirar la región del #2745 sin perder datos:\n"
            + "\n".join(conflictos)
        )

    for organizacion_id, campos in cambios:
        organizacion_model._base_manager.using(alias).filter(pk=organizacion_id).update(
            **campos
        )


class Migration(migrations.Migration):

    dependencies = [
        ("gestion_organizaciones", "0004_carga_inicial_programas_lineas"),
        ("organizaciones", "0026_issue_2642_regiones_zonas_excel"),
    ]

    operations = [
        migrations.RunPython(copiar_region_al_2642, migrations.RunPython.noop),
        migrations.DeleteModel(name="DatosRegionOrganizacion"),
        migrations.DeleteModel(name="SubzonaAbordaje"),
        migrations.DeleteModel(name="RegionAbordaje"),
    ]
