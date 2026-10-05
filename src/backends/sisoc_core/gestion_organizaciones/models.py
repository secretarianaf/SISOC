"""Modelos de la gestión de organizaciones del core."""

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from core.soft_delete import SoftDeleteModelMixin


class Firmante(SoftDeleteModelMixin, models.Model):
    organizacion = models.ForeignKey(
        "organizaciones.Organizacion",
        on_delete=models.CASCADE,
        related_name="firmantes",
    )
    nombre = models.CharField(max_length=255)
    rol = models.ForeignKey(
        "organizaciones.RolFirmante",
        on_delete=models.PROTECT,
        related_name="firmantes",
        blank=True,
        null=True,
    )
    cuit = models.BigIntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(99999999999)],
    )
    programa = models.ForeignKey(
        "comedores.Programas",
        on_delete=models.PROTECT,
        related_name="firmantes_organizacion",
        blank=True,
        null=True,
    )

    def __str__(self):
        rol = self.rol.nombre if self.rol else "-"
        return f"{self.nombre} ({rol})"

    class Meta:
        # Tabla original: el modelo vivía en `organizaciones` (kernel) hasta
        # #1931. Va del lado del core porque se relaciona con comedores.
        db_table = "organizaciones_firmante"
