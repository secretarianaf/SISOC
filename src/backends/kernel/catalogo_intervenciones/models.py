"""Catálogos de intervenciones: datos maestros compartidos (kernel).

Los usan Comedores (``intervenciones.Intervencion``) y Centro de Infancia, que
corre en su propio backend. Antes vivían en ``intervenciones``.
"""

from django.db import models
from django.db.models import Q


class TipoIntervencion(models.Model):
    """
    Guardado de los tipos de intervenciones realizadas.
    """

    nombre = models.CharField(max_length=255)
    programa = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="Programa",
        help_text="Texto libre para segmentar tipos por módulo (ej: comedores, cdi).",
        db_index=True,
    )

    @classmethod
    def para_programas(cls, *aliases, include_ids=None):
        queryset = cls.objects.order_by("id")
        include_ids = [pk for pk in (include_ids or []) if pk]
        aliases = [alias for alias in aliases if alias]

        if not aliases and not include_ids:
            return queryset

        condiciones = Q(programa__isnull=True) | Q(programa="")
        for alias in aliases:
            condiciones |= Q(programa__iexact=alias)

        if include_ids:
            condiciones |= Q(pk__in=include_ids)

        return queryset.filter(condiciones).distinct()

    def __str__(self):
        return f"{self.nombre}"

    class Meta:
        # Tabla original: el modelo vivía en `intervenciones` hasta #1931.
        db_table = "intervenciones_tipointervencion"
        verbose_name = "Tipo de Intervención"
        verbose_name_plural = "Tipos de Intervención"
        ordering = ["id"]


class SubIntervencion(models.Model):
    """
    Guardado de las sub-intervenciones realizadas.
    """

    nombre = models.CharField(max_length=255)
    tipo_intervencion = models.ForeignKey(
        TipoIntervencion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subintervenciones",
        verbose_name="Tipo de Intervención asociada",
    )

    @classmethod
    def para_tipo(cls, tipo_intervencion_id=None, include_ids=None):
        include_ids = [pk for pk in (include_ids or []) if pk]
        queryset = cls.objects.order_by("nombre")

        if tipo_intervencion_id:
            queryset = queryset.filter(tipo_intervencion_id=tipo_intervencion_id)
        else:
            queryset = queryset.none()

        queryset = queryset.exclude(nombre="")
        if include_ids:
            queryset = cls.objects.filter(
                Q(pk__in=include_ids)
                | (Q(tipo_intervencion_id=tipo_intervencion_id) & ~Q(nombre=""))
            ).order_by("nombre")

        return queryset.distinct()

    def __str__(self):
        return f"{self.nombre}"

    class Meta:
        # Tabla original: el modelo vivía en `intervenciones` hasta #1931.
        db_table = "intervenciones_subintervencion"
        verbose_name = "Sub-Intervención"
        verbose_name_plural = "Sub-Intervenciones"
        ordering = ["tipo_intervencion", "nombre"]


class TipoDestinatario(models.Model):
    """
    Guardado de los destinatarios de las intervenciones realizadas.
    """

    nombre = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.nombre}"

    class Meta:
        # Tabla original: el modelo vivía en `intervenciones` hasta #1931.
        db_table = "intervenciones_tipodestinatario"
        verbose_name = "Destinatario"
        verbose_name_plural = "Destinatarios"
        ordering = ["id"]


class TipoContacto(models.Model):
    """
    Guardado de los tipos de contacto de las intervenciones realizadas.
    """

    nombre = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.nombre}"

    class Meta:
        # Tabla original: el modelo vivía en `intervenciones` hasta #1931.
        db_table = "intervenciones_tipocontacto"
        verbose_name = "Tipo de Contacto"
        verbose_name_plural = "Tipos de Contacto"
        ordering = ["id"]
