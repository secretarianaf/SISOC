from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone
from core.soft_delete import SoftDeleteModelMixin


def validar_rango_anio_fecha(value):
    """Validar que la fecha esté entre los años 2000 y 2100."""
    if value:
        anio = value.year
        if anio < 2000:
            raise ValidationError("El año de la fecha debe ser mayor o igual a 2000.")
        if anio > 2100:
            raise ValidationError("El año de la fecha debe ser menor o igual a 2100.")


class Intervencion(SoftDeleteModelMixin, models.Model):
    """
    Registro de intervenciones realizadas a comedores.
    """

    comedor = models.ForeignKey(
        "comedores.Comedor",
        on_delete=models.SET_NULL,
        null=True,
        related_name="intervenciones",
        verbose_name="Comedor intervenido",
    )
    admision = models.ForeignKey(
        "admisiones.Admision",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_index=True,
        related_name="intervenciones",
        verbose_name="Admisión",
    )
    subintervencion = models.ForeignKey(
        "catalogo_intervenciones.SubIntervencion",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Sub-tipo de intervención",
    )
    tipo_intervencion = models.ForeignKey(
        "catalogo_intervenciones.TipoIntervencion",
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Tipo de intervención",
    )
    fecha = models.DateTimeField(
        default=timezone.now,
        verbose_name="Fecha y hora de intervención",
        validators=[validar_rango_anio_fecha],
    )
    observaciones = models.TextField(
        blank=True, null=True, verbose_name="Observaciones"
    )
    destinatario = models.ForeignKey(
        "catalogo_intervenciones.TipoDestinatario",
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Destinatario",
    )
    forma_contacto = models.ForeignKey(
        "catalogo_intervenciones.TipoContacto",
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Forma de contacto",
    )
    tiene_documentacion = models.BooleanField(
        default=False, verbose_name="Documentación adjunta"
    )
    documentacion = models.FileField(
        upload_to="documentacion/",
        blank=True,
        null=True,
        verbose_name="Documentación Adjunta",
    )

    class Meta:
        verbose_name = "Intervención"
        verbose_name_plural = "Intervenciones"
        ordering = ["-fecha"]
        indexes = [
            models.Index(fields=["comedor"]),
            models.Index(fields=["fecha"]),
            models.Index(fields=["tipo_intervencion"]),
        ]

    def __str__(self):
        return f"Intervención en {self.comedor} - {self.fecha.strftime('%Y-%m-%d')}"
