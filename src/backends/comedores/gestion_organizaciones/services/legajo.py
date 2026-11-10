"""Datos del legajo de la organización por programa (#2745, Etapa 5).

Arma lo que muestra ``organizacion_detail.html`` según el programa y la
sección elegidos. Nada queda oculto: lo que no tiene lugar en un programa
aparece en los bloques "Sin programa asignado", "Proyectos sin línea" o
"Rendiciones de otras líneas" (plan, sección 2.1).
"""

from django.db.models import Q

from comedores.models import Comedor
from comedores.utils import (
    es_programa_alimentar_comunidad,
    es_programa_linea_tradicional,
)
from gestion_organizaciones.models import Firmante
from gestion_organizaciones.services.programas import (
    comedores_por_programa,
    es_programa_abordaje,
    firmantes_por_programa,
    linea_programatica_de,
    programas_de_organizacion,
    proyectos_por_linea,
    rendiciones_por_programa,
    resumen_convenio,
)
from organizaciones.models import ArchivoOrganizacion, ProyectoOrganizacion
from rendicioncuentasmensual.services import RendicionesOrganizacionService

SECCION_INFO = "info"
SECCION_RENDICIONES = "rendiciones"

_COMEDOR_RELACIONES = (
    "tipocomedor",
    "provincia",
    "municipio",
    "localidad",
    "referente",
    "programa",
    "proyecto",
)


def color_programa(programa):
    """Clave de color de la franja y del selector (B v3)."""
    if programa is None:
        return "otro"
    if es_programa_alimentar_comunidad(programa):
        return "alco"
    if es_programa_abordaje(programa):
        return "trad" if es_programa_linea_tradicional(programa) else "secos"
    return "otro"


def _entero(valor):
    valor = str(valor or "").strip()
    return int(valor) if valor.isdigit() else None


def elegir_programa(programas, solicitado, linea_del_proyecto=None):
    """El programa pedido si es de la organización; si no, el primero.

    Sin programa pedido, ``linea_del_proyecto`` (la del ``?proyecto=`` del
    legajo anterior) elige la línea donde están sus rendiciones.
    """
    programa_id = _entero(solicitado)
    if programa_id is None:
        programa_id = linea_del_proyecto
    for programa in programas:
        if programa.pk == programa_id:
            return programa
    return programas[0] if programas else None


def _linea_de_proyecto(organizacion, codigo):
    if not codigo:
        return None
    return (
        ProyectoOrganizacion.objects.filter(
            organizacion=organizacion, codigo=codigo, activo=True
        )
        .values_list("linea__programa_id", flat=True)
        .first()
    )


def sin_programa_asignado(organizacion, programas):
    """Firmantes y comedores sin programa o con uno que la organización no tiene."""
    ids = [programa.pk for programa in programas]
    fuera = Q(programa__isnull=True) | ~Q(programa_id__in=ids)
    return {
        "firmantes": list(
            Firmante.objects.filter(organizacion=organizacion)
            .filter(fuera)
            .select_related("rol", "programa")
        ),
        "comedores": list(
            Comedor.objects.filter(organizacion=organizacion)
            .filter(fuera)
            .select_related(*_COMEDOR_RELACIONES)
        ),
    }


def proyectos_sin_lugar(organizacion, programas):
    """Proyectos activos sin línea o con una línea que la organización no tiene."""
    lineas = [programa.pk for programa in programas if es_programa_abordaje(programa)]
    return list(
        ProyectoOrganizacion.objects.filter(organizacion=organizacion, activo=True)
        .filter(Q(linea__isnull=True) | ~Q(linea__programa_id__in=lineas))
        .order_by("codigo")
    )


def rendiciones_de_otras_lineas(organizacion, programas):
    """Rendiciones cuya línea no es un programa de Abordaje de la organización."""
    lineas = {
        linea_programatica_de(programa)
        for programa in programas
        if es_programa_abordaje(programa)
    }
    return list(
        RendicionesOrganizacionService.obtener_rendiciones(organizacion).exclude(
            linea_programatica__in=lineas
        )
    )


def _territoriales_sin_proyecto(organizacion):
    return list(
        organizacion.territoriales_abordaje_comunitario.order_by(
            "last_name", "first_name", "username"
        )
    )


def _abordaje_sin_programa(organizacion, codigo_proyecto):
    """Datos de Abordaje de una organización sin programa de Abordaje.

    Se muestran debajo de Datos de la Organización, como en el legajo
    anterior, para que proyectos, región y rendiciones no queden ocultos.
    """
    proyectos = list(
        organizacion.proyectos.filter(activo=True)
        .order_by("codigo")
        .prefetch_related("territoriales")
    )
    territoriales = _territoriales_sin_proyecto(organizacion)
    tiene_region = bool(
        organizacion.region_abordaje_id or organizacion.subzona_abordaje_id
    )
    codigos = RendicionesOrganizacionService.obtener_proyectos(organizacion)
    codigo = codigo_proyecto if codigo_proyecto in codigos else ""
    return {
        "abordaje_sin_programa": (
            {"proyectos": proyectos, "territoriales_sin_proyecto": territoriales}
            if proyectos or territoriales or tiene_region
            else None
        ),
        "rendiciones_generales": list(
            RendicionesOrganizacionService.obtener_rendiciones(organizacion, codigo)
        ),
        "codigos_rendiciones": codigos,
        "proyecto_rendiciones": codigo,
    }


def _convenios(proyectos):
    filas = []
    for proyecto in proyectos:
        convenio = getattr(proyecto, "convenio", None)
        filas.append(
            {
                "proyecto": proyecto,
                "convenio": convenio,
                "resumen": resumen_convenio(convenio) if convenio else None,
            }
        )
    return filas


def _datos_abordaje(organizacion, programa, programas, seccion, codigo_proyecto):
    proyectos = list(
        proyectos_por_linea(organizacion, programa)
        .select_related("convenio")
        .prefetch_related("territoriales")
    )
    # Las mismas opciones que el legajo anterior (incluye códigos de comedor).
    codigos = RendicionesOrganizacionService.obtener_proyectos(organizacion)
    codigo = codigo_proyecto if codigo_proyecto in codigos else ""
    rendiciones = rendiciones_por_programa(organizacion, programa)
    return {
        "proyectos": proyectos,
        "convenios": _convenios(proyectos),
        "es_linea_tradicional": es_programa_linea_tradicional(programa),
        "proyectos_sin_linea": proyectos_sin_lugar(organizacion, programas),
        "territoriales_sin_proyecto": _territoriales_sin_proyecto(organizacion),
        "codigos_rendiciones": codigos,
        "proyecto_rendiciones": codigo,
        "rendiciones_total": rendiciones.count(),
        "rendiciones": (
            rendiciones_por_programa(organizacion, programa, codigo)
            if seccion == SECCION_RENDICIONES
            else []
        ),
    }


def datos_legajo(organizacion, parametros):
    """Contexto del legajo para el programa y la sección de ``parametros``.

    ``parametros``: ``programa`` (id), ``seccion`` (info | rendiciones) y
    ``proyecto`` (código, filtro de rendiciones). ``?proyecto=`` sin
    ``seccion`` abre Rendiciones, como el legajo anterior.
    """
    programas = programas_de_organizacion(organizacion)
    codigo_proyecto = (parametros.get("proyecto") or "").strip()
    programa = elegir_programa(
        programas,
        parametros.get("programa"),
        _linea_de_proyecto(organizacion, codigo_proyecto),
    )
    seccion = parametros.get("seccion")
    if seccion not in (SECCION_INFO, SECCION_RENDICIONES):
        seccion = SECCION_RENDICIONES if "proyecto" in parametros else SECCION_INFO
    tiene_abordaje = any(es_programa_abordaje(item) for item in programas)

    datos = {
        "programas": [
            {"programa": item, "color": color_programa(item)} for item in programas
        ],
        "programa": programa,
        "color": color_programa(programa),
        "es_alimentar": bool(programa and es_programa_alimentar_comunidad(programa)),
        "es_abordaje": bool(programa and es_programa_abordaje(programa)),
        "seccion": seccion,
        "sin_programa": sin_programa_asignado(organizacion, programas),
        "tiene_abordaje": tiene_abordaje,
        "rendiciones_otras_lineas": [],
        "abordaje_sin_programa": None,
        "rendiciones_generales": [],
        "firmantes": [],
        "comedores": [],
        "comedores_count": Comedor.objects.filter(organizacion=organizacion).count(),
    }
    if tiene_abordaje:
        datos["rendiciones_otras_lineas"] = rendiciones_de_otras_lineas(
            organizacion, programas
        )
    else:
        datos.update(_abordaje_sin_programa(organizacion, codigo_proyecto))
    if programa is not None:
        datos["firmantes"] = list(firmantes_por_programa(organizacion, programa))
        datos["comedores"] = list(
            comedores_por_programa(organizacion, programa).select_related(
                *_COMEDOR_RELACIONES
            )
        )
    if datos["es_abordaje"]:
        datos.update(
            _datos_abordaje(organizacion, programa, programas, seccion, codigo_proyecto)
        )
    # La documentación es de Alimentar Comunidad; sin programas cargados se
    # sigue viendo como hoy (definición 22). Si la organización no tiene
    # Alimentar pero sí documentos cargados, se ve en todos sus programas:
    # nada cargado queda sin acceso.
    tiene_alimentar = any(es_programa_alimentar_comunidad(p) for p in programas)
    datos["muestra_documentacion"] = (
        datos["es_alimentar"]
        or not programas
        or (
            not tiene_alimentar
            and ArchivoOrganizacion.objects.filter(organizacion=organizacion).exists()
        )
    )
    return datos
