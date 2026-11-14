"""Corrección del código de un proyecto de organización ya cargado."""

import logging

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q

from comedores.models import Comedor
from organizaciones.models import ProyectoOrganizacion

logger = logging.getLogger("django")

LARGO_MAXIMO_CODIGO = ProyectoOrganizacion._meta.get_field("codigo").max_length

NOMBRES_LINEA = {"secos": "Línea Secos", "tradicional": "Línea Tradicional"}


def normalizar_codigo(codigo):
    return str(codigo or "").strip()


def cambio_de_linea_por_codigo(proyecto, codigo_nuevo):
    """Línea de rendición deducida antes y después de cambiar el código.

    Las rendiciones nuevas de un proyecto toman su línea del código o nombre
    (prefijo AMBA => Secos; ver ``inferir_linea_programatica``, #2642). Devuelve
    ``(antes, despues)`` con nombres legibles si el cambio la altera, o ``None``.
    Las rendiciones ya creadas guardan su línea y no se recalculan.
    """
    # pylint: disable=import-outside-toplevel
    from rendicioncuentasmensual.services import inferir_linea_programatica

    antes = inferir_linea_programatica(None, proyecto)
    simulado = ProyectoOrganizacion(codigo=codigo_nuevo, nombre=proyecto.nombre)
    despues = inferir_linea_programatica(None, simulado)
    if antes == despues:
        return None
    return NOMBRES_LINEA.get(antes, antes), NOMBRES_LINEA.get(despues, despues)


def validar_codigo_proyecto(proyecto, codigo):
    """Mismas reglas que el alta en el formulario de la organización."""
    if not codigo:
        raise ValidationError("Ingresá un código de proyecto.")
    if "," in codigo:
        raise ValidationError("El código no puede tener comas.")
    if len(codigo) > LARGO_MAXIMO_CODIGO:
        raise ValidationError(
            f"El código no puede superar los {LARGO_MAXIMO_CODIGO} caracteres."
        )
    # La unicidad (organización, código) incluye los proyectos quitados; se
    # compara sin mayúsculas como el alta, para no crear códigos casi iguales.
    repetido = (
        ProyectoOrganizacion.objects.filter(
            organizacion_id=proyecto.organizacion_id, codigo__iexact=codigo
        )
        .exclude(pk=proyecto.pk)
        .first()
    )
    if repetido is not None:
        estado = "" if repetido.activo else " (quitado)"
        raise ValidationError(
            f"La organización ya tiene el proyecto {repetido.codigo}{estado}."
        )


@transaction.atomic
def cambiar_codigo_proyecto(*, proyecto, codigo_nuevo, actor=None):
    """Cambia el código del proyecto y el que guardan sus comedores.

    Los comedores se vinculan al proyecto por FK o, en datos anteriores, por
    organización + ``codigo_de_proyecto`` (texto). Se actualizan ambos casos,
    incluidos los comedores dados de baja, para que la vinculación (territoriales
    PNUD, rendiciones, datos de convenio) no se pierda. Devuelve la cantidad de
    comedores actualizados.
    """
    codigo_nuevo = normalizar_codigo(codigo_nuevo)
    proyecto = ProyectoOrganizacion.objects.select_for_update().get(pk=proyecto.pk)
    codigo_anterior = proyecto.codigo
    if codigo_nuevo == codigo_anterior:
        return 0
    validar_codigo_proyecto(proyecto, codigo_nuevo)

    comedores = Comedor.all_objects.filter(
        Q(proyecto=proyecto)
        | Q(
            proyecto__isnull=True,
            organizacion_id=proyecto.organizacion_id,
            codigo_de_proyecto=codigo_anterior,
        )
    )
    comedores_ids = list(comedores.values_list("pk", flat=True))
    actualizados = Comedor.all_objects.filter(pk__in=comedores_ids).update(
        codigo_de_proyecto=codigo_nuevo
    )

    proyecto.codigo = codigo_nuevo
    proyecto.save(update_fields=["codigo"])
    logger.info(
        "Código de proyecto %s cambiado de %r a %r por %s; comedores actualizados: %s",
        proyecto.pk,
        codigo_anterior,
        codigo_nuevo,
        getattr(actor, "pk", None),
        comedores_ids,
    )
    return actualizados
