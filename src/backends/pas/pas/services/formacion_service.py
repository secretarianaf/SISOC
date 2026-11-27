"""Reglas de presentación de formación para titulares PAS.

La fuente externa todavía no tiene un contrato público confirmado. Hasta que
ese contrato exista, PAS no consulta modelos ni tablas de otro dominio.
"""

import json
import logging
import os
from datetime import date, timedelta

from django.conf import settings
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from pas.models import PasPeriodoFormacion, PasPersona

logger = logging.getLogger("django")

# La fuente FCH/PAV todavía no está integrada. Mientras sea False la formación
# no bloquea el pago ni se cierran ciclos: todos los titulares figurarían en
# rojo sin que exista un dato real que lo respalde.
FORMACION_INTEGRADA = False

PUNTOS_CURSO_COMPLETO = 100
# Un curso FCH solo puede estar Inscripto o Aprobado.
ESTADO_INSCRIPTO = "inscripto"
ESTADO_APROBADO = "aprobado"
ESTADOS_CURSO = {ESTADO_INSCRIPTO: "Inscripto", ESTADO_APROBADO: "Aprobado"}
# Códigos que la fuente pueda informar como curso terminado.
_CODIGOS_APROBADO = {"aprobado", "aprobada", "completada", "completado", "completed"}
INICIO_PERIODOS_FORMACION = date(2026, 1, 1)
DURACION_PERIODO_DIAS = 90
PERSONAS_POR_PAGINA = 30


def calcular_periodo_formacion(fecha_actual=None):
    """Calcula el ciclo consecutivo de 90 días correspondiente a una fecha."""

    fecha_actual = fecha_actual or timezone.localdate()
    dias_desde_inicio = max((fecha_actual - INICIO_PERIODOS_FORMACION).days, 0)
    ciclos_completos, indice_dia = divmod(
        dias_desde_inicio,
        DURACION_PERIODO_DIAS,
    )
    inicio_periodo_actual = INICIO_PERIODOS_FORMACION + timedelta(
        days=ciclos_completos * DURACION_PERIODO_DIAS
    )
    fin_periodo_actual = inicio_periodo_actual + timedelta(
        days=DURACION_PERIODO_DIAS - 1
    )
    return {
        "inicio_base": INICIO_PERIODOS_FORMACION,
        "inicio_actual": inicio_periodo_actual,
        "fin_actual": fin_periodo_actual,
        "duracion_dias": DURACION_PERIODO_DIAS,
        "dia_actual": indice_dia + 1,
    }


def _formacion_demo():
    """Puntajes de prueba ``{dni: puntos}`` del entorno local, si existen.

    Solo se leen con ``DEBUG`` activo desde la variable ``PAS_FORMACION_DEMO``
    del ``.env`` local (JSON). Sirven para ver el semáforo sin la fuente FCH;
    en un despliegue sin esa variable no hay datos de prueba.
    """

    if not settings.DEBUG:
        return {}
    texto = os.getenv("PAS_FORMACION_DEMO", "").strip()
    if not texto:
        return {}
    try:
        datos = json.loads(texto)
        return {int(dni): int(puntos) for dni, puntos in datos.items()}
    except (ValueError, TypeError, AttributeError):
        logger.warning("pas.formacion.demo_invalida")
        return {}


def estado_curso(formacion):
    """Código del curso: ``aprobado`` si la fuente lo da por terminado, si no ``inscripto``."""

    codigo = str(formacion.get("estado_codigo") or formacion.get("estado") or "")
    if codigo.strip().casefold() in _CODIGOS_APROBADO:
        return ESTADO_APROBADO
    return ESTADO_INSCRIPTO


def normalizar_cursos(formaciones):
    """Cursos con ``estado_codigo`` y ``estado`` limitados a Inscripto o Aprobado."""

    return [
        {
            **formacion,
            "estado_codigo": estado_curso(formacion),
            "estado": ESTADOS_CURSO[estado_curso(formacion)],
        }
        for formacion in formaciones
    ]


def obtener_formacion_persona(persona):
    """Devuelve formación vacía hasta disponer de una fachada confirmada."""

    dni = getattr(persona, "dni", None)
    puntos = _formacion_demo().get(dni) if dni else None
    if puntos is None:
        return []
    inicio = calcular_periodo_formacion()["inicio_actual"]
    return [
        {
            "curso": "Curso de prueba (dato local)",
            "fuente": "Entorno local",
            "inicio": inicio,
            "fin": inicio + timedelta(days=10),
            "progreso": "100%",
            "puntos": puntos,
            "estado": ESTADOS_CURSO[ESTADO_APROBADO],
            "estado_codigo": ESTADO_APROBADO,
            "certificado_url": "",
        }
    ]


def puntos_formacion_por_persona(personas, fecha_actual=None):
    """Puntos del ciclo actual (crédito arrastrado incluido) por id de titular."""

    personas = list(personas)
    inicio = calcular_periodo_formacion(fecha_actual)["inicio_actual"]
    creditos = dict(
        PasPeriodoFormacion.objects.filter(
            persona__in=personas, fin=inicio - timedelta(days=1)
        ).values_list("persona_id", "excedente")
    )
    return {
        persona.pk: creditos.get(persona.pk, 0)
        + _sumar_puntos(obtener_formacion_persona(persona))
        for persona in personas
    }


def credito_inicial(persona, inicio_periodo):
    """Excedente arrastrado del ciclo inmediato anterior ya cerrado."""

    if persona is None or not getattr(persona, "pk", None):
        return 0
    anterior = (
        PasPeriodoFormacion.objects.filter(
            persona=persona, fin=inicio_periodo - timedelta(days=1)
        )
        .values_list("excedente", flat=True)
        .first()
    )
    return anterior or 0


def _clasificar(puntos_totales, formaciones):
    """Semáforo de validación de pago: verde, amarillo (parcial) o rojo."""

    if puntos_totales >= PUNTOS_CURSO_COMPLETO:
        return PasPeriodoFormacion.Estado.CUMPLIDO
    if formaciones or puntos_totales > 0:
        return PasPeriodoFormacion.Estado.PARCIAL
    return PasPeriodoFormacion.Estado.INCUMPLIDO


SEMAFORO = {
    PasPeriodoFormacion.Estado.CUMPLIDO: "verde",
    PasPeriodoFormacion.Estado.PARCIAL: "amarillo",
    PasPeriodoFormacion.Estado.INCUMPLIDO: "rojo",
}


def _sumar_puntos(formaciones):
    return sum(int(formacion["puntos"] or 0) for formacion in formaciones)


def resumir_formacion(formaciones, persona=None, fecha_actual=None):
    """Resume datos normalizados sin inferir progreso no provisto por la fuente.

    Suma al puntaje del ciclo el crédito excedente arrastrado del ciclo
    anterior (Eje 2) e indica si el resultado bloquea el pago.
    """

    periodo = calcular_periodo_formacion(fecha_actual)
    credito = credito_inicial(persona, periodo["inicio_actual"])
    puntos_periodo = _sumar_puntos(formaciones)
    puntos = credito + puntos_periodo
    clasificacion = _clasificar(puntos, formaciones)
    cursos_completados = sum(
        estado_curso(formacion) == ESTADO_APROBADO for formacion in formaciones
    )
    if puntos >= PUNTOS_CURSO_COMPLETO:
        estado = "cumplido"
        titulo = "Cumplido"
        detalle = "Condicionalidad de formación alcanzada para el período."
    elif formaciones:
        estado = "en-curso"
        titulo = "En curso"
        detalle = (
            "Hay cursos inscriptos sin aprobar. Solo los cursos aprobados suman puntos."
        )
    else:
        estado = "sin-formacion"
        titulo = "Sin formación"
        detalle = "La fuente de formación todavía no se encuentra integrada."

    resumen = {
        "puntos": puntos,
        "puntos_periodo": puntos_periodo,
        "credito_inicial": credito,
        "objetivo": PUNTOS_CURSO_COMPLETO,
        "excedente": max(puntos - PUNTOS_CURSO_COMPLETO, 0),
        "cursos_completados": cursos_completados,
        "total_cursos": len(formaciones),
        "estado": estado,
        "titulo": titulo,
        "detalle": detalle,
        "semaforo": SEMAFORO[clasificacion],
        "bloquea_pago": FORMACION_INTEGRADA
        and clasificacion != PasPeriodoFormacion.Estado.CUMPLIDO,
        "integrada": FORMACION_INTEGRADA,
    }
    resumen.update(periodo)
    return resumen


@transaction.atomic
def cerrar_periodo_formacion(persona, inicio, fin, formaciones):
    """Persiste el resultado del ciclo y el excedente que pasa al siguiente.

    Ej.: con 120 puntos el ciclo siguiente arranca con 20 de crédito.
    Idempotente por titular e inicio de ciclo.
    """

    credito = credito_inicial(persona, inicio)
    total = credito + _sumar_puntos(formaciones)
    periodo, _ = PasPeriodoFormacion.objects.update_or_create(
        persona=persona,
        inicio=inicio,
        defaults={
            "fin": fin,
            "credito_inicial": credito,
            "puntos_periodo": total - credito,
            "excedente": max(total - PUNTOS_CURSO_COMPLETO, 0),
            "estado": _clasificar(total, formaciones),
        },
    )
    return periodo


def cerrar_periodos_formacion(fecha_actual=None):
    """Cierra, para todo el padrón, el último ciclo de 90 días ya vencido.

    No hace nada mientras la fuente FCH no esté integrada.
    """

    if not FORMACION_INTEGRADA:
        return {"cerrados": 0, "integrada": False}
    actual = calcular_periodo_formacion(fecha_actual)
    if actual["inicio_actual"] <= INICIO_PERIODOS_FORMACION:
        return {"cerrados": 0, "integrada": True}
    fin = actual["inicio_actual"] - timedelta(days=1)
    inicio = fin - timedelta(days=DURACION_PERIODO_DIAS - 1)
    cerrados = 0
    pendientes = PasPersona.objects.exclude(periodos_formacion__inicio=inicio)
    for persona in pendientes.order_by("pk").iterator(chunk_size=500):
        cerrar_periodo_formacion(
            persona, inicio, fin, obtener_formacion_persona(persona)
        )
        cerrados += 1
    logger.info(
        "pas.formacion.ciclo_cerrado",
        extra={"data": {"inicio": inicio.isoformat(), "cerrados": cerrados}},
    )
    return {"cerrados": cerrados, "integrada": True}


def obtener_puntos_por_dni(personas, fecha_actual=None):
    """Puntos del ciclo (con crédito arrastrado) y cursos de cada titular."""

    personas = [persona for persona in personas if persona.dni]
    puntos = puntos_formacion_por_persona(personas, fecha_actual)
    return {
        persona.dni: {
            "puntos": puntos[persona.pk],
            "total_cursos": len(obtener_formacion_persona(persona)),
        }
        for persona in personas
    }


def buscar_personas_formacion(query="", estado_formacion="todos", excluir_id=None):
    """Filtra el padrón completo antes de aplicar la paginación de Formación."""

    personas = PasPersona.objects.select_related("estado").order_by(
        "apellidos", "nombres", "id"
    )
    query = str(query or "").strip()
    if query:
        filtro = (
            Q(apellidos__icontains=query)
            | Q(nombres__icontains=query)
            | Q(cuit__icontains=query)
        )
        if query.isdigit():
            filtro |= Q(dni=int(query)) | Q(id_persona=int(query))
        personas = personas.filter(filtro)

    # Sin una fuente integrada, todos los titulares tienen estado neutral.
    if estado_formacion not in ("todos", "sin-formacion"):
        personas = personas.none()
    if excluir_id:
        personas = personas.exclude(pk=excluir_id)
    return personas


def paginar_personas_formacion(
    query="", estado_formacion="todos", pagina=1, excluir_id=None
):
    """Entrega una página estable para el scroll incremental de Formación."""

    personas = buscar_personas_formacion(query, estado_formacion, excluir_id)
    return Paginator(personas, PERSONAS_POR_PAGINA).get_page(pagina)


def preparar_personas_formacion(personas):
    """Agrega a cada persona los indicadores disponibles para presentación."""

    personas = list(personas)
    puntos_por_dni = obtener_puntos_por_dni(personas)
    for persona in personas:
        datos = puntos_por_dni.get(persona.dni, {"puntos": 0, "total_cursos": 0})
        if datos["puntos"] >= PUNTOS_CURSO_COMPLETO:
            estado = "cumplido"
        elif datos["total_cursos"]:
            estado = "en-curso"
        else:
            estado = "sin-formacion"
        persona.puntos_formacion = datos["puntos"]
        persona.estado_formacion = estado
    return personas


def estado_formacion_pago(persona, fecha_actual=None):
    """Resumen de formación del titular para la liquidación.

    Devuelve ``None`` mientras la fuente no esté integrada: no hay validación.
    """

    if not FORMACION_INTEGRADA:
        return None
    return resumir_formacion(
        obtener_formacion_persona(persona), persona=persona, fecha_actual=fecha_actual
    )
