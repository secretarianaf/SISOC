"""Modelo del Formulario de Calidad de los CDI (200_CalidadCDI).

Los campos de respuesta se generan desde `formulario_calidad_schema`: una
columna por variable SQL de la especificación, con el mismo nombre de columna.
Los metadatos de captura automática llevan el prefijo `0_` en la base.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from centrodeinfancia.formulario_calidad_schema import (
    CHECKBOX,
    GRILLA,
    MATRIZ_NUMERICA,
    NUMERO,
    PREGUNTAS,
    RADIO,
)


class FormularioCalidadCDI(models.Model):
    class Estado(models.TextChoices):
        BORRADOR = "borrador", "Borrador"
        ENVIADO = "enviado", "Enviado"

    centro = models.ForeignKey(
        "centrodeinfancia.CentroDeInfancia",
        on_delete=models.PROTECT,
        related_name="formularios_calidad",
        db_column="0_CDI_ID",
    )
    jurisdiccion = models.ForeignKey(
        "core.Provincia",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
        db_column="0_Jurisdiccion_ID",
    )
    departamento = models.ForeignKey(
        "centrodeinfancia.DepartamentoIpi",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
        db_column="0_Departamento_ID",
    )
    enviado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
        db_column="0_User_ID",
    )
    fecha_envio = models.DateTimeField(
        null=True,
        blank=True,
        db_column="0_Timestamp",
    )

    estado = models.CharField(
        max_length=16,
        choices=Estado.choices,
        default=Estado.BORRADOR,
        db_index=True,
    )
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    creado = models.DateTimeField(auto_now_add=True)
    modificado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_envio", "-modificado", "-id"]
        verbose_name = "Formulario de Calidad CDI"
        verbose_name_plural = "Formularios de Calidad CDI"
        constraints = [
            models.UniqueConstraint(
                fields=["centro", "fecha_envio"],
                name="uniq_formulario_calidad_cdi_version",
            )
        ]

    def __str__(self):
        return f"Formulario de Calidad #{self.pk} - {self.centro_id} ({self.estado})"

    @property
    def es_enviado(self):
        return self.estado == self.Estado.ENVIADO

    def save(self, *args, **kwargs):
        # Inmutabilidad (1.3 de la especificación): un envío no se edita; las
        # correcciones se cargan como un formulario nuevo.
        if self.pk:
            estado_guardado = (
                type(self)
                .objects.filter(pk=self.pk)
                .values_list("estado", flat=True)
                .first()
            )
            if estado_guardado == self.Estado.ENVIADO:
                raise ValidationError(
                    "El formulario ya fue enviado y no puede modificarse."
                )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.es_enviado:
            raise ValidationError("El formulario ya fue enviado y no puede borrarse.")
        return super().delete(*args, **kwargs)


def _campo_opcion(pregunta, db_column):
    # Sin `choices` en el modelo: la base guarda sólo el número de opción y los
    # textos viven en el schema, así un ajuste de redacción no genera migración.
    # El form valida las opciones (TypedChoiceField).
    return models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(len(pregunta.opciones))],
        db_column=db_column,
    )


def _campos_de_pregunta(pregunta):
    if pregunta.tipo == RADIO:
        yield pregunta.nombre_campo(), _campo_opcion(pregunta, pregunta.db_column())
    elif pregunta.tipo == NUMERO:
        yield pregunta.nombre_campo(), models.PositiveIntegerField(
            null=True, blank=True, db_column=pregunta.db_column()
        )
    elif pregunta.tipo == MATRIZ_NUMERICA:
        for fila, _ in pregunta.filas:
            yield pregunta.nombre_campo(fila), models.DecimalField(
                max_digits=5,
                decimal_places=2,
                null=True,
                blank=True,
                validators=[MinValueValidator(0)],
                db_column=pregunta.db_column(fila),
            )
    elif pregunta.tipo == GRILLA:
        for fila, _ in pregunta.filas:
            yield pregunta.nombre_campo(fila), _campo_opcion(
                pregunta, pregunta.db_column(fila)
            )
    elif pregunta.tipo == CHECKBOX:
        for fila, _ in pregunta.filas:
            yield pregunta.nombre_campo(fila), models.BooleanField(
                default=False, db_column=pregunta.db_column(fila)
            )
    else:  # pragma: no cover - el schema sólo usa los tipos de arriba
        raise ValueError(f"Tipo de pregunta desconocido: {pregunta.tipo}")

    if pregunta.campo_especificar:
        yield pregunta.campo_especificar, models.CharField(
            max_length=255,
            null=True,
            blank=True,
            db_column=pregunta.db_column_especificar,
        )


for _pregunta in PREGUNTAS:
    for _nombre, _campo in _campos_de_pregunta(_pregunta):
        FormularioCalidadCDI.add_to_class(_nombre, _campo)
