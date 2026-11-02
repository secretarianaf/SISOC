"""Reglas del Formulario de Calidad de los CDI: borrador, envío y completitud."""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from centrodeinfancia.formulario_calidad_schema import (
    CHECKBOX,
    PREGUNTAS,
    especificar_requerido,
    pregunta_visible,
)
from centrodeinfancia.models import FormularioCalidadCDI

MENSAJE_INCOMPLETA = "Esta pregunta es obligatoria."
MENSAJE_FILAS_INCOMPLETAS = "Complete todas las filas."
MENSAJE_CHECKBOX = "Seleccione al menos una opción."
MENSAJE_ESPECIFICAR = "Especifique la opción elegida."


class FormularioIncompletoError(Exception):
    """El envío no se completó porque quedan preguntas obligatorias sin responder."""

    def __init__(self, errores: dict[int, str]):
        super().__init__("Formulario incompleto")
        self.errores = errores


def obtener_borrador(centro):
    return (
        FormularioCalidadCDI.objects.filter(
            centro=centro, estado=FormularioCalidadCDI.Estado.BORRADOR
        )
        .order_by("-modificado", "-id")
        .first()
    )


def _vaciar_campos(formulario, pregunta):
    for nombre in pregunta.campos:
        setattr(formulario, nombre, False if pregunta.tipo == CHECKBOX else None)
    if pregunta.campo_especificar:
        setattr(formulario, pregunta.campo_especificar, None)


def limpiar_respuestas_ocultas(formulario):
    """Vacía lo que el pase condicional oculta y los 'especificar' no aplicables."""
    for pregunta in PREGUNTAS:
        if not pregunta_visible(pregunta, formulario):
            _vaciar_campos(formulario, pregunta)
            continue
        if pregunta.campo_especificar and not especificar_requerido(
            pregunta, formulario
        ):
            setattr(formulario, pregunta.campo_especificar, None)


def errores_de_completitud(formulario) -> dict[int, str]:
    """Preguntas visibles sin responder, por número de pregunta."""
    errores = {}
    for pregunta in PREGUNTAS:
        if not pregunta_visible(pregunta, formulario):
            continue
        valores = [getattr(formulario, nombre) for nombre in pregunta.campos]
        if pregunta.tipo == CHECKBOX:
            if not any(valores):
                errores[pregunta.numero] = MENSAJE_CHECKBOX
        elif all(valor is None for valor in valores):
            errores[pregunta.numero] = MENSAJE_INCOMPLETA
        elif any(valor is None for valor in valores):
            errores[pregunta.numero] = MENSAJE_FILAS_INCOMPLETAS
        if pregunta.numero in errores:
            continue
        if (
            especificar_requerido(pregunta, formulario)
            and not (getattr(formulario, pregunta.campo_especificar) or "").strip()
        ):
            errores[pregunta.numero] = MENSAJE_ESPECIFICAR
    return errores


def guardar_borrador(formulario, centro, user):
    formulario.centro = centro
    formulario.estado = FormularioCalidadCDI.Estado.BORRADOR
    if not formulario.pk:
        formulario.creado_por = user
    limpiar_respuestas_ocultas(formulario)
    formulario.save()
    return formulario


def enviar_formulario(formulario, centro, user):
    """Cierra el formulario como envío inmutable o informa lo que falta.

    Si falta completar algo, el avance queda guardado como borrador para no
    perder lo cargado y se levanta `FormularioIncompletoError`.
    """
    guardar_borrador(formulario, centro, user)
    errores = errores_de_completitud(formulario)
    if errores:
        raise FormularioIncompletoError(errores)

    with transaction.atomic():
        formulario.estado = FormularioCalidadCDI.Estado.ENVIADO
        formulario.fecha_envio = timezone.now()
        formulario.enviado_por = user
        formulario.jurisdiccion_id = centro.provincia_id
        formulario.departamento_id = centro.departamento_id
        formulario.save()
    return formulario
