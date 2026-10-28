"""Datos de la organización por programa (#2745).

Plan: docs/plans/2026-T4/2026-10-20-2745-legajo-organizacion-por-programa.md.
Si la organización no tiene programas cargados, las reglas nuevas no se
aplican (definición 22): las funciones devuelven lo mismo que hoy.
"""

from decimal import Decimal

from django.db.models import Q

from comedores.models import Comedor, Programas
from comedores.utils import (
    es_programa_alimentar_comunidad,
    es_programa_linea_secos,
    es_programa_linea_tradicional,
)
from gestion_organizaciones.models import (
    Firmante,
    LineaProyecto,
    ProgramaOrganizacion,
)
from organizaciones.models import ProyectoOrganizacion
from rendicioncuentasmensual.models import RendicionCuentaMensual
from rendicioncuentasmensual.services import RendicionesOrganizacionService


def es_programa_abordaje(programa) -> bool:
    return es_programa_linea_secos(programa) or es_programa_linea_tradicional(programa)


def es_programa_del_legajo(programa) -> bool:
    """Alimentar Comunidad, Línea Secos o Línea Tradicional."""
    return es_programa_alimentar_comunidad(programa) or es_programa_abordaje(programa)


def _orden_programa(programa):
    if es_programa_alimentar_comunidad(programa):
        return (0, programa.pk)
    if es_programa_linea_secos(programa):
        return (1, programa.pk)
    if es_programa_linea_tradicional(programa):
        return (2, programa.pk)
    return (3, programa.pk)


def ordenar_programas(programas):
    """Orden del legajo: Alimentar, Secos, Tradicional y después el resto."""
    return sorted(programas, key=_orden_programa)


def programas_del_legajo():
    """Los tres programas que se eligen en la organización."""
    return ordenar_programas(
        programa
        for programa in Programas.objects.all()
        if es_programa_del_legajo(programa)
    )


def programas_de_organizacion(organizacion):
    """Programas cargados en la organización, en el orden del legajo."""
    if not getattr(organizacion, "pk", None):
        return []
    return ordenar_programas(
        Programas.objects.filter(organizaciones_asignadas__organizacion=organizacion)
    )


def aplica_reglas_de_programa(organizacion) -> bool:
    """Verdadero si la organización tiene al menos un programa cargado."""
    if not getattr(organizacion, "pk", None):
        return False
    return ProgramaOrganizacion.objects.filter(organizacion=organizacion).exists()


def tiene_programa_abordaje(organizacion) -> bool:
    return any(
        es_programa_abordaje(programa)
        for programa in programas_de_organizacion(organizacion)
    )


def linea_programatica_de(programa):
    """Valor de ``RendicionCuentaMensual.linea_programatica`` del programa."""
    if es_programa_linea_secos(programa):
        return RendicionCuentaMensual.LINEA_SECOS
    if es_programa_linea_tradicional(programa):
        return RendicionCuentaMensual.LINEA_TRADICIONAL
    return None


def proyectos_por_linea(organizacion, programa):
    """Proyectos activos de la organización con la línea del programa."""
    return ProyectoOrganizacion.objects.filter(
        organizacion=organizacion,
        activo=True,
        linea__programa=programa,
    ).order_by("codigo")


def proyectos_sin_linea(organizacion):
    return ProyectoOrganizacion.objects.filter(
        organizacion=organizacion,
        activo=True,
        linea__isnull=True,
    ).order_by("codigo")


def firmantes_por_programa(organizacion, programa):
    return Firmante.objects.filter(
        organizacion=organizacion, programa=programa
    ).select_related("rol", "programa")


def comedores_por_programa(organizacion, programa):
    return Comedor.objects.filter(organizacion=organizacion, programa=programa)


def rendiciones_por_programa(organizacion, programa, codigo_proyecto=None):
    """Rendiciones de la línea del programa (definición 23).

    Para programas que no son de Abordaje no hay rendiciones por línea.
    """
    linea = linea_programatica_de(programa)
    if linea is None:
        return RendicionCuentaMensual.objects.none()
    return RendicionesOrganizacionService.obtener_rendiciones(
        organizacion, codigo_proyecto, linea_programatica=linea
    )


def asociaciones_de_programa(organizacion, programa):
    """Datos de la organización que usan el programa (impiden quitarlo).

    Cuenta también registros dados de baja: quitar el programa no debe dejar
    datos sin su programa (sección 2.1 del plan).
    """
    asociaciones = {
        "proyectos": LineaProyecto.objects.filter(
            proyecto__organizacion=organizacion, programa=programa
        ).count(),
        "firmantes": Firmante.all_objects.filter(
            organizacion=organizacion, programa=programa
        ).count(),
        "comedores": Comedor.all_objects.filter(
            organizacion=organizacion, programa=programa
        ).count(),
        "rendiciones": 0,
    }
    linea = linea_programatica_de(programa)
    if linea is not None:
        asociaciones["rendiciones"] = (
            RendicionCuentaMensual.objects.filter(linea_programatica=linea)
            .filter(
                Q(proyecto__organizacion=organizacion)
                | Q(comedor__organizacion=organizacion)
            )
            .distinct()
            .count()
        )
    return {clave: total for clave, total in asociaciones.items() if total}


def motivo_que_impide_baja(organizacion):
    """Mensaje si la organización tiene proyectos; si no, ``None``.

    La baja lógica de la organización borraría físicamente sus proyectos
    (no tienen baja lógica), y con ellos su línea y su convenio.
    """
    proyectos = ProyectoOrganizacion.objects.filter(organizacion=organizacion)
    total = proyectos.count()
    if not total:
        return None
    detalle = []
    usados = (
        Comedor.all_objects.filter(proyecto__in=proyectos)
        .values("proyecto")
        .distinct()
        .count()
    )
    if usados:
        detalle.append(f"{usados} usados por comedores")
    con_linea = proyectos.filter(linea__isnull=False).count()
    if con_linea:
        detalle.append(f"{con_linea} con línea")
    con_convenio = proyectos.filter(convenio__isnull=False).count()
    if con_convenio:
        detalle.append(f"{con_convenio} con convenio")
    con_rendiciones = (
        proyectos.filter(rendiciones_cuentas_mensuales__isnull=False).distinct().count()
    )
    if con_rendiciones:
        detalle.append(f"{con_rendiciones} con rendiciones")
    sufijo = f" ({', '.join(detalle)})" if detalle else ""
    return (
        f"No se puede dar de baja la organización: tiene {total} "
        f"proyecto{'s' if total != 1 else ''}{sufijo}. Darla de baja borraría "
        "esos proyectos y sus datos."
    )


COMPONENTES_CONVENIO = (
    "componente_alimentario",
    "componente_gastos_generales",
    "componente_siph",
    "componente_gasto_bancario",
    "imprevistos",
)


def resumen_convenio(convenio):
    """Suma de componentes frente al monto total (solo informa, no bloquea)."""
    suma = sum(
        (getattr(convenio, campo, None) or Decimal("0"))
        for campo in COMPONENTES_CONVENIO
    )
    total = convenio.monto_total or Decimal("0")
    return {
        "suma": suma,
        "total": total,
        "diferencia": total - suma,
        "coincide": suma == total,
    }
