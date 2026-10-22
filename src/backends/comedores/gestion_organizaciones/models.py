"""Modelos de la gestión de organizaciones del core.

Los datos por programa de la organización (#2745) viven acá y no en el kernel
porque dependen de ``comedores.Programas``. Todas sus relaciones usan
``PROTECT``: nada se borra en cascada (plan del #2745, sección 2.1).
"""

from decimal import Decimal

from django.core.exceptions import ValidationError
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


class ProgramaOrganizacion(models.Model):
    """Programa en el que participa una organización (puede tener varios)."""

    organizacion = models.ForeignKey(
        "organizaciones.Organizacion",
        on_delete=models.PROTECT,
        related_name="programas_asignados",
    )
    programa = models.ForeignKey(
        "comedores.Programas",
        on_delete=models.PROTECT,
        related_name="organizaciones_asignadas",
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.programa)

    class Meta:
        ordering = ["programa_id"]
        verbose_name = "Programa de la organización"
        verbose_name_plural = "Programas de la organización"
        constraints = [
            models.UniqueConstraint(
                fields=["organizacion", "programa"],
                name="uq_programa_organizacion",
            )
        ]


class LineaProyecto(models.Model):
    """Línea de Abordaje Comunitario (Secos o Tradicional) de un proyecto."""

    proyecto = models.OneToOneField(
        "organizaciones.ProyectoOrganizacion",
        on_delete=models.PROTECT,
        related_name="linea",
    )
    programa = models.ForeignKey(
        "comedores.Programas",
        on_delete=models.PROTECT,
        related_name="lineas_proyecto",
    )

    def __str__(self):
        return f"{self.proyecto} - {self.programa}"

    def clean(self):
        super().clean()
        # Import diferido: comedores.utils importa modelos de comedores.
        from comedores.utils import (  # pylint: disable=import-outside-toplevel
            es_programa_linea_secos,
            es_programa_linea_tradicional,
        )

        programa = getattr(self, "programa", None)
        if programa is None:
            return
        if not (
            es_programa_linea_secos(programa) or es_programa_linea_tradicional(programa)
        ):
            raise ValidationError(
                {"programa": "La línea debe ser Línea Secos o Línea Tradicional."}
            )
        proyecto = getattr(self, "proyecto", None)
        if proyecto is None:
            return
        programas_org = ProgramaOrganizacion.objects.filter(
            organizacion_id=proyecto.organizacion_id
        )
        # Sin programas cargados no se exige nada (definición 22 del plan).
        if (
            programas_org.exists()
            and not programas_org.filter(programa=programa).exists()
        ):
            raise ValidationError(
                {"programa": "La organización no tiene cargado este programa."}
            )

    class Meta:
        verbose_name = "Línea del proyecto"
        verbose_name_plural = "Líneas de proyecto"


class RegionAbordaje(models.Model):
    """Catálogo de regiones de Abordaje Comunitario."""

    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre

    class Meta:
        ordering = ["nombre"]
        verbose_name = "Región"
        verbose_name_plural = "Regiones"


class SubzonaAbordaje(models.Model):
    """Catálogo de aglomerados/subzonas, cada una dentro de una región."""

    region = models.ForeignKey(
        RegionAbordaje,
        on_delete=models.PROTECT,
        related_name="subzonas",
    )
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre

    class Meta:
        ordering = ["region__nombre", "nombre"]
        verbose_name = "Aglomerado/Subzona"
        verbose_name_plural = "Aglomerados/Subzonas"
        constraints = [
            models.UniqueConstraint(
                fields=["region", "nombre"],
                name="uq_subzona_abordaje_region_nombre",
            )
        ]


class DatosRegionOrganizacion(models.Model):
    """Región y subzona de la organización; común a Línea Secos y Tradicional."""

    organizacion = models.OneToOneField(
        "organizaciones.Organizacion",
        on_delete=models.PROTECT,
        related_name="datos_region",
    )
    region = models.ForeignKey(
        RegionAbordaje,
        on_delete=models.PROTECT,
        related_name="organizaciones",
    )
    subzona = models.ForeignKey(
        SubzonaAbordaje,
        on_delete=models.PROTECT,
        related_name="organizaciones",
    )

    def __str__(self):
        return f"{self.region} - {self.subzona}"

    def clean(self):
        super().clean()
        if (
            self.region_id
            and self.subzona_id
            and self.subzona.region_id != self.region_id
        ):
            raise ValidationError(
                {"subzona": "La subzona elegida no pertenece a la región."}
            )

    class Meta:
        verbose_name = "Datos de región de la organización"
        verbose_name_plural = "Datos de región de organizaciones"


_MONTO = {
    "max_digits": 14,
    "decimal_places": 2,
    "validators": [MinValueValidator(Decimal("0"))],
}


class ConvenioProyecto(models.Model):
    """Convenio de la organización para un proyecto de Abordaje Comunitario.

    Distinto de ``comedores.ComedorDatosConvenioPnud`` (datos de convenio del
    comedor): conviven y no se sincronizan (definición 27 del plan #2745).
    """

    proyecto = models.OneToOneField(
        "organizaciones.ProyectoOrganizacion",
        on_delete=models.PROTECT,
        related_name="convenio",
    )
    numero = models.CharField(max_length=50, verbose_name="Número de convenio")
    fecha = models.DateField(verbose_name="Fecha de convenio")
    meses = models.PositiveSmallIntegerField(
        verbose_name="Meses de convenio",
        validators=[MinValueValidator(1)],
    )
    monto_total = models.DecimalField(verbose_name="Monto total", **_MONTO)
    componente_alimentario = models.DecimalField(
        verbose_name="Componente alimentario", **_MONTO
    )
    componente_gastos_generales = models.DecimalField(
        verbose_name="Componente gastos generales", **_MONTO
    )
    componente_siph = models.DecimalField(verbose_name="Componente SIPH", **_MONTO)
    componente_gasto_bancario = models.DecimalField(
        verbose_name="Componente gasto bancario", **_MONTO
    )
    imprevistos = models.DecimalField(
        verbose_name="Imprevistos",
        blank=True,
        null=True,
        **_MONTO,
    )

    def __str__(self):
        return f"Convenio {self.numero} ({self.proyecto})"

    def clean(self):
        super().clean()
        if self.imprevistos is None or not self.proyecto_id:
            return
        from comedores.utils import (  # pylint: disable=import-outside-toplevel
            es_programa_linea_tradicional,
        )

        linea = LineaProyecto.objects.filter(proyecto_id=self.proyecto_id).first()
        if linea is None or not es_programa_linea_tradicional(linea.programa):
            raise ValidationError(
                {"imprevistos": "Imprevistos solo aplica a Línea Tradicional."}
            )

    class Meta:
        verbose_name = "Convenio de la organización (por proyecto)"
        verbose_name_plural = "Convenios de la organización (por proyecto)"
